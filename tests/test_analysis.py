import csv
import io
import json
import math
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from pydantic import ValidationError
from ru_transcript.data_constants import ALPHABET, KNOWN_PHONEMES

from phonscope import ExpectedUnits, analyze_dataset
from phonscope.cli import main
from phonscope.models import MARKERS, GroupName


def _transcript(phonemes: list[str], allophones: list[str] | None = None) -> Mock:
    """
    Create a transcriber response with known sound sequences.

    :param phonemes: Phonemes for one utterance.
    :param allophones: Allophones, or None to reuse the phoneme sequence.
    :return: Mock transcriber without pronunciation computation.
    """
    transcript = Mock()
    transcript.get_phonemes.return_value = phonemes
    transcript.get_allophones.return_value = phonemes if allophones is None else allophones
    return transcript


class AnalysisTests(unittest.TestCase):
    """Check metric properties and CLI input boundaries."""

    def setUp(self) -> None:
        """Create an isolated text dataset for each test."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.path = self.root / 'data.txt'

    def test_counts_boundaries_and_evenness(self) -> None:
        """Check all groups, cross-word units and separate utterances."""
        self.path.write_text('первая строка\nвторая строка\n', encoding='utf-8')
        with patch('phonscope.analysis.RuTranscript') as backend:
            backend.side_effect = [_transcript(['a', '_', 'b', 'a']), _transcript(['b'])]
            report = analyze_dataset(self.path)
        assert report.score == 10
        assert report.files == 1 and report.lines == 2
        group_names: tuple[tuple[GroupName, GroupName, GroupName], ...] = (
            (GroupName.PHONEMES, GroupName.PHONEME_BIGRAMS, GroupName.PHONEME_TRIGRAMS),
            (GroupName.ALLOPHONES, GroupName.ALLOPHONE_BIGRAMS, GroupName.ALLOPHONE_TRIGRAMS),
        )
        for single_name, bigram_name, trigram_name in group_names:
            single = report.groups[single_name]
            assert single.total == 4 and single.unique == 2
            assert single.evenness == 1.0
            bigrams = report.groups[bigram_name]
            assert bigrams.total == 2 and bigrams.unique == 2
            assert {item.unit for item in bigrams.frequencies} == {('a', 'b'), ('b', 'a')}
            assert ('a', 'a') not in {item.unit for item in bigrams.frequencies}
            trigrams = report.groups[trigram_name]
            assert trigrams.total == 1 and trigrams.evenness is None
            assert trigrams.frequencies[0].unit == ('a', 'b', 'a')
            assert trigrams.missing is None

    def test_repetition_preserves_score_and_evenness(self) -> None:
        """Repetition changes size and absolute counts but preserves the metrics."""
        self.path.write_text('реплика\n', encoding='utf-8')
        with patch('phonscope.analysis.RuTranscript', return_value=_transcript(['a', 'a', 'b'])):
            original = analyze_dataset(self.path)
            self.path.write_text('реплика\n' * 10, encoding='utf-8')
            repeated = analyze_dataset(self.path)
        assert original.score == repeated.score
        assert repeated.lines == original.lines * 10
        for name, group in original.groups.items():
            other = repeated.groups[name]
            assert other.unique == group.unique
            assert other.total == group.total * 10
            assert other.evenness == group.evenness
            assert [item.relative_frequency for item in other.frequencies] == [
                item.relative_frequency for item in group.frequencies
            ]
        expected_evenness = -(2 / 3 * math.log(2 / 3) + 1 / 3 * math.log(1 / 3)) / math.log(2)
        evenness = original.groups[GroupName.PHONEMES].evenness
        assert evenness is not None
        assert math.isclose(evenness, expected_evenness)

    def test_independent_representations_and_empty_groups(self) -> None:
        """Count representations independently and leave empty group evenness undefined."""
        self.path.write_text('звук\n', encoding='utf-8')
        with patch('phonscope.analysis.RuTranscript', return_value=_transcript(['a'], ['ɑ'])):
            report = analyze_dataset(self.path)
        assert report.score == 2
        assert report.groups[GroupName.PHONEMES].frequencies[0].unit == ('a',)
        assert report.groups[GroupName.ALLOPHONES].frequencies[0].unit == ('ɑ',)
        assert all(group.evenness is None for group in report.groups.values())
        assert report.groups[GroupName.PHONEME_BIGRAMS].total == 0
        assert report.groups[GroupName.PHONEME_BIGRAMS].frequencies == []

    def test_expected_overrides_do_not_change_metrics(self) -> None:
        """Expected inventories change diagnostics only for the specified groups."""
        self.path.write_text('реплика\n', encoding='utf-8')
        expected = ExpectedUnits(phonemes=['a', 'o'], phoneme_bigrams=[('o', 'a')], allophone_trigrams=[])
        with patch('phonscope.analysis.RuTranscript', return_value=_transcript(['a', 'b'])):
            default = analyze_dataset(self.path)
            custom = analyze_dataset(self.path, expected)
        assert custom.score == default.score
        assert default.groups[GroupName.PHONEMES].missing == sorted(
            (symbol,) for symbol in KNOWN_PHONEMES - MARKERS - {'a', 'b'}
        )
        assert custom.groups[GroupName.PHONEMES].missing == [('o',)]
        assert custom.groups[GroupName.PHONEME_BIGRAMS].missing == [('o', 'a')]
        assert custom.groups[GroupName.ALLOPHONE_TRIGRAMS].missing == []
        assert custom.groups[GroupName.ALLOPHONES].missing == sorted((symbol,) for symbol in set(ALPHABET) - {'a', 'b'})
        for name, group in default.groups.items():
            assert group.model_dump(exclude={'missing'}) == custom.groups[name].model_dump(exclude={'missing'})

    def test_directory_filters_and_file_boundaries(self) -> None:
        """Read sorted files without binary files, recursion or joined utterances."""
        (self.root / 'b.txt').write_text('б\n', encoding='utf-8')
        (self.root / 'a.TXT').write_text('а\n', encoding='utf-8')
        (self.root / 'binary.bin').write_bytes(b'\xff')
        (self.root / 'nested').mkdir()
        (self.root / 'nested/hidden.txt').write_text('скрытая строка', encoding='utf-8')
        with patch('phonscope.analysis.RuTranscript') as backend:
            backend.side_effect = [_transcript(['a']), _transcript(['b'])]
            report = analyze_dataset(self.root)
        assert [call.args[0].strip() for call in backend.call_args_list] == ['а', 'б']
        assert report.files == 2 and report.lines == 2
        assert report.groups[GroupName.PHONEME_BIGRAMS].total == 0

    def test_csv_column_records_and_stress_marks(self) -> None:
        """Read the CSV text column while preserving stress, quotes and records."""
        path = self.root / 'data.csv'
        with path.open('w', encoding='utf-8-sig', newline='') as destination:
            writer = csv.writer(destination)
            writer.writerow(['', 'filename', 'text'])
            writer.writerow(['0', 'a.wav', "м+ама 'название',\nвторая часть"])
            writer.writerow(['1', 'b.wav', 'звук'])
        with patch('phonscope.analysis.RuTranscript') as backend:
            backend.side_effect = [_transcript(['a']), _transcript(['b'])]
            report = analyze_dataset(self.root)
        assert report.files == 1 and report.lines == 2
        assert report.groups[GroupName.PHONEME_BIGRAMS].total == 0
        call = backend.call_args_list[0]
        assert call.args == ('мама "название", вторая часть',)
        assert call.kwargs == {'stressed_text': 'м+ама "название", вторая часть', 'stress_place': 'before'}

    def test_invalid_csv_produces_visible_cli_error(self) -> None:
        """Reject invalid CSV without emitting partial JSON."""
        path = self.root / 'data.csv'
        for content in (
            'filename,utterance\na.wav,текст\n',
            'text,text\nодин,два\n',
            'filename,text\na.wav\n',
            'filename,text\na.wav,текст,лишнее\n',
            'filename,text\na.wav,"незакрытое поле\n',
        ):
            with self.subTest(content=content):
                path.write_text(content, encoding='utf-8')
                output = io.StringIO()
                with redirect_stdout(output), self.assertLogs('phonscope.cli', level='ERROR') as logs:
                    assert main([str(path)]) == 1
                assert output.getvalue() == ''
                assert any('Analysis failed' in line for line in logs.output)

    def test_invalid_expected_and_transcription_failures(self) -> None:
        """Reject invalid inventories and transcription failures without partial reports."""
        for value in (
            {'unknown': []},
            {GroupName.PHONEME_BIGRAMS: [['a']]},
            {GroupName.PHONEMES: ['_']},
            {GroupName.PHONEMES: ['']},
            {GroupName.PHONEMES: ['a b']},
            {GroupName.PHONEMES: [1]},
        ):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                ExpectedUnits.model_validate(value)
        with self.assertRaises(ValueError):
            analyze_dataset(self.path)
        self.path.write_text('\n  \n', encoding='utf-8')
        with self.assertRaises(ValueError):
            analyze_dataset(self.path)
        self.path.write_text('первая\nвторая\n', encoding='utf-8')
        with patch('phonscope.analysis.RuTranscript') as backend:
            backend.side_effect = [_transcript(['a']), RuntimeError('transcription failure')]
            with self.assertRaisesRegex(RuntimeError, 'transcription failure'):
                analyze_dataset(self.path)
        with (
            patch('phonscope.analysis.RuTranscript', return_value=_transcript(['a'], [])),
            self.assertRaises(ValueError),
        ):
            analyze_dataset(self.path)

    def test_cli_matches_api_and_reports_errors(self) -> None:
        """Return the API JSON from CLI and report failures without partial output."""
        self.path.write_text('реплика\n', encoding='utf-8')
        expected_path = self.root / 'expected.json'
        expected_path.write_text('{"phonemes": ["a", "o"]}', encoding='utf-8')
        with patch('phonscope.analysis.RuTranscript', return_value=_transcript(['a', 'b'])):
            report = analyze_dataset(self.path, ExpectedUnits(phonemes=['a', 'o']))
            output = io.StringIO()
            with redirect_stdout(output):
                status = main(
                    [
                        str(self.path),
                        '--expected',
                        str(expected_path),
                        '--format',
                        'json',
                        '--output',
                        str(self.root / 'json-report'),
                    ]
                )
        assert status == 0
        assert json.loads(output.getvalue()) == report.model_dump(mode='json')
        expected_path.write_text('{"phonemes": ["_"]}', encoding='utf-8')
        with redirect_stdout(io.StringIO()) as output, self.assertLogs('phonscope.cli', level='ERROR'):
            assert main([str(self.path), '--expected', str(expected_path)]) == 1
        assert output.getvalue() == ''
