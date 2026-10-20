import io
import json
import logging
import re
import tempfile
import unittest
import warnings
from collections.abc import Callable
from contextlib import chdir, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from phonscope import DatasetReport, ExpectedUnits, analyze_dataset
from phonscope.cli import main
from phonscope.locales import Language
from phonscope.models import GroupName
from phonscope.report import render_report, terminal_summary


class ReportTests(unittest.TestCase):
    """Check readable reports, progress and JSON compatibility."""

    def setUp(self) -> None:
        """Create a small dataset with a predictable transcription."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / 'data.txt'
        self.source.write_text('одна\n\nдве\n', encoding='utf-8')
        transcript = Mock()
        transcript.get_phonemes.return_value = ['a', 'b']
        transcript.get_allophones.return_value = ['a', 'b']
        backend = patch('phonscope.analysis.RuTranscript', return_value=transcript)
        backend.start()
        self.addCleanup(backend.stop)

    def test_html_is_self_contained_and_escapes_user_data(self) -> None:
        """Keep user symbols and source names from executing as HTML."""
        expected = ExpectedUnits(phonemes=['</script><script>alert(1)</script>'])
        report = analyze_dataset(self.source, expected)
        html = render_report(report, Path('<img src=x onerror=alert(1)>'), expected, ['warning'] * 7, Language.RU)
        assert '<img src=x onerror=alert(1)>' not in html
        assert '</script><script>alert(1)</script>' not in html
        assert '&lt;img' in html
        data = html.split('<script id="report-data" type="application/json">')[1].split('</script>')[0]
        payload = json.loads(data)
        assert payload['groups'][GroupName.PHONEMES] == report.model_dump(mode='json')['groups'][GroupName.PHONEMES]
        assert payload['expectations'][GroupName.PHONEMES] == 'Пользовательский список'
        assert payload['expectations'][GroupName.ALLOPHONES] == 'Инвентарь RuTranscript (литературная норма)'
        assert 'Предупреждения при анализе: 7' in html
        assert '<script src=' not in html
        assert '/*REPORT_DATA*/' not in html
        assert 'Балл разнообразия: 6' in terminal_summary(report, Language.RU)
        assert 'Не определена' in terminal_summary(report, Language.RU)

    def test_cli_html_progress_warnings_and_browser(self) -> None:
        """Save reports, display progress and open the browser when requested."""
        output = self.root / 'reports/result'
        with (
            patch('phonscope.cli.webbrowser.open', return_value=True) as browser,
            redirect_stdout(io.StringIO()) as stdout,
            redirect_stderr(io.StringIO()) as stderr,
        ):
            status = main([str(self.source), '--output', str(output), '--open'])
        assert status == 0
        output = next(output.glob('data_*'))
        assert {path.name for path in output.iterdir()} == {'report.html', 'report.json', 'report.md'}
        assert json.loads((output / 'report.json').read_text()) == analyze_dataset(self.source).model_dump(mode='json')
        assert '| Phonemes |' in (output / 'report.md').read_text()
        assert 'Diversity score: 6' in stdout.getvalue()
        assert str(output) in stdout.getvalue()
        assert 'Processed utterances: 1' in stderr.getvalue()
        browser.assert_called_once_with((output / 'report.html').resolve().as_uri())

    def test_json_progress_and_write_failure(self) -> None:
        """Preserve machine-readable JSON and expose output errors."""
        progress: list[int] = []
        report = analyze_dataset(self.source, progress=progress.append)
        assert progress == [1, 2]
        with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
            assert main([str(self.source), '--format', 'json', '--output', str(self.root / 'json')]) == 0
        assert json.loads(stdout.getvalue()) == report.model_dump(mode='json')
        assert 'Report directory:' in stderr.getvalue()
        assert 'Processed utterances:' not in stderr.getvalue()
        blocker = self.root / 'blocked'
        blocker.write_text('file', encoding='utf-8')
        with redirect_stdout(io.StringIO()) as stdout, self.assertLogs('phonscope.cli', level='ERROR'):
            assert main([str(self.source), '--output', str(blocker / 'reports')]) == 1
        assert stdout.getvalue() == ''

    def test_full_warnings_and_input_protection(self) -> None:
        """Display complete diagnostics and protect input files from overwriting."""
        output = self.root / 'reports'
        with patch('phonscope.execution.analyze_dataset', wraps=analyze_dataset) as analyze:
            analyze.side_effect = self._warn_and_analyze
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as stderr:
                assert main([str(self.source), '--output', str(output)]) == 0
        output = next(output.glob('data_*'))
        assert 'UserWarning: Unresolved stress' in stderr.getvalue()
        assert stderr.getvalue().count('Unresolved stress') >= 2
        assert 'Unresolved stress' in (output / 'report.html').read_text(encoding='utf-8')
        assert 'Unresolved stress' in (output / 'report.md').read_text(encoding='utf-8')
        original = self.source.read_text(encoding='utf-8')
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main([str(self.source), '--output', str(self.source)])
        assert error.exception.code == 2
        assert self.source.read_text(encoding='utf-8') == original

    def test_report_languages_and_identical_json(self) -> None:
        """Localize readable reports while preserving identical JSON data."""
        expected_json = analyze_dataset(self.source).model_dump(mode='json')
        for language, title, label in (
            (Language.EN, 'Dataset report', 'Phonemes'),
            (Language.RU, 'Отчет о датасете', 'Фонемы'),
        ):
            with self.subTest(language=language):
                output = self.root / language
                with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()):
                    assert main([str(self.source), '--output', str(output), '--language', language]) == 0
                output = next(output.glob('data_*'))
                html = (output / 'report.html').read_text(encoding='utf-8')
                markdown = (output / 'report.md').read_text(encoding='utf-8')
                assert f'lang="{language}"' in html
                assert re.search(r'\{\{[a-z_]+\}\}', html) is None
                assert title in html and title in markdown
                assert f'| {label} |' in markdown
                assert '[report' not in markdown
                assert '(report.html)' in markdown and '(report.json)' in markdown
                assert json.loads((output / 'report.json').read_text()) == expected_json
                assert label in stdout.getvalue()
        original = self.source.read_text(encoding='utf-8')
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main([str(self.source), '--language', 'de'])
        assert error.exception.code == 2
        assert self.source.read_text(encoding='utf-8') == original

    def test_default_directory_and_generated_file_protection(self) -> None:
        """Create three report files and preserve earlier runs."""
        with chdir(self.root), redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()):
            assert main([str(self.source)]) == 0
        output = next((self.root / 'reports').glob('data_*'))
        assert {path.name for path in output.iterdir()} == {'report.json', 'report.html', 'report.md'}
        assert str(output.resolve()) in stdout.getvalue()
        assert 'Diversity score: 6' in stdout.getvalue()
        original = (output / 'report.json').read_bytes()
        with chdir(self.root), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            assert main([str(self.source)]) == 0
        assert len(list((self.root / 'reports').glob('data_*'))) == 2
        assert (output / 'report.json').read_bytes() == original

    def _warn_and_analyze(
        self,
        data_path: Path,
        expected: ExpectedUnits | None,
        progress: Callable[[int], None] | None,
        min_relative_frequency: float = 0,
    ) -> DatasetReport:
        """
        Add warnings to normal analysis for CLI checks.

        :param data_path: Path to the test dataset.
        :param expected: Expected units.
        :param progress: Progress callback.
        :param min_relative_frequency: Minimum relative unit frequency.
        :return: Analysis result for the test dataset.
        """
        logging.getLogger('ru_transcript').warning('Unresolved stress')
        warnings.warn('Unresolved stress', stacklevel=2)
        return analyze_dataset(data_path, expected, progress=progress, min_relative_frequency=min_relative_frequency)
