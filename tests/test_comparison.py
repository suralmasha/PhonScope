import io
import json
import math
import re
import tempfile
import unittest
from collections import Counter
from concurrent.futures import Future
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

from phonscope import analyze_dataset, compare_reports
from phonscope.comparison_report import save_comparison
from phonscope.execution import AnalysisJob, analyze_and_compare
from phonscope.locales import Language
from phonscope.metrics import group_report
from phonscope.models import FORMULA_VERSION, DatasetReport, GroupName, Presence, Winner

if TYPE_CHECKING:
    from phonscope.models import Unit


class MetricTests(unittest.TestCase):
    """Check effective diversity, filtering and original frequency preservation."""

    def test_shannon_example_and_repetition(self) -> None:
        """Ten equally frequent units are more diverse than twenty dominated by one."""
        uniform = group_report(Counter({(str(index),): 100 for index in range(10)}), None)
        counts: Counter[Unit] = Counter({('dominant',): 17100} | {(str(index),): 100 for index in range(19)})
        skewed = group_report(counts, None)
        repeated = group_report(Counter({unit: count * 10 for unit, count in counts.items()}), None)
        assert uniform.effective_diversity is not None and skewed.effective_diversity is not None
        assert math.isclose(uniform.effective_diversity, 10)
        assert math.isclose(skewed.effective_diversity, 1.8580496157031485, rel_tol=1e-6)
        assert uniform.effective_diversity > skewed.effective_diversity
        assert skewed.unique == 20
        assert repeated.effective_diversity == skewed.effective_diversity
        assert repeated.evenness == skewed.evenness
        filtered = group_report(counts, None, 0.01)
        assert filtered.frequencies == skewed.frequencies
        assert filtered.unique == 20 and filtered.retained_unique == 1
        assert filtered.effective_diversity == 1 and filtered.evenness is None
        assert math.isclose(filtered.excluded_frequency or 0, 0.1)

    def test_threshold_boundary_empty_group_and_validation(self) -> None:
        """Include the threshold boundary, handle empty groups and reject invalid settings."""
        counts: Counter[Unit] = Counter({('a',): 9, ('b',): 1})
        assert group_report(counts, None, 0.1).retained_unique == 2
        assert group_report(counts, None, 0.10001).retained_unique == 1
        for empty in (group_report(counts, None, 0.95), group_report(Counter(), None)):
            assert empty.effective_diversity == 0 and empty.retained_unique == 0 and empty.evenness is None
        for value in (-0.1, 1.1, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                analyze_dataset('unused.txt', min_relative_frequency=value)


class ComparisonTests(unittest.TestCase):
    """Check compatibility, frequency differences, reports and worker failures."""

    def setUp(self) -> None:
        """Create two report directories with known frequencies."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.a = self.root / 'a'
        self.b = self.root / 'b'
        self.a.mkdir()
        self.b.mkdir()
        self.report_a = self._report(['a', 'a', 'b'])
        self.report_b = self._report(['b', 'c'])
        (self.a / 'report.json').write_text(self.report_a.model_dump_json(), encoding='utf-8')
        (self.b / 'report.json').write_text(self.report_b.model_dump_json(), encoding='utf-8')

    def _report(self, sequence: list[str], threshold: float = 0) -> DatasetReport:
        """
        Analyze one utterance with a predictable transcription.

        :param sequence: Phoneme and allophone sequence.
        :param threshold: Relative metric threshold.
        :return: A complete report using the same formula as the client.
        """
        source = self.root / 'dataset.txt'
        source.write_text('текст', encoding='utf-8')
        transcript = Mock()
        transcript.get_phonemes.return_value = sequence
        transcript.get_allophones.return_value = sequence
        with patch('phonscope.analysis.RuTranscript', return_value=transcript):
            return analyze_dataset(source, min_relative_frequency=threshold)

    def test_complete_unit_comparison_and_tie(self) -> None:
        """Compare shared and exclusive units using complete original frequencies."""
        report = compare_reports(self.a, self.b)
        assert report.compatible and not report.forced and report.winner is Winner.A
        assert report.score_difference == self.report_a.score - self.report_b.score
        group = report.groups[GroupName.PHONEMES]
        assert (group.common, group.only_a, group.only_b) == (1, 1, 1)
        units = {item.unit: item for item in group.units}
        assert units['a',].presence is Presence.ONLY_A and units['a',].count_b == 0
        assert units['c',].presence == 'only_b' and units['c',].count_a == 0
        assert math.isclose(units['b',].frequency_difference, 1 / 3 - 1 / 2)
        assert compare_reports(self.a, self.a).winner == 'tie'

    def test_incompatibility_override_and_legacy_reports(self) -> None:
        """Require explicit incompatibility overrides and preserve legacy scores."""
        filtered = self._report(['b', 'c'], 0.6)
        (self.b / 'report.json').write_text(filtered.model_dump_json(), encoding='utf-8')
        with self.assertRaises(ValueError):
            compare_reports(self.a, self.b)
        forced = compare_reports(self.a, self.b, allow_incompatible=True)
        assert not forced.compatible and forced.forced
        assert forced.dataset_b.score == filtered.score == 2
        assert all(not item.included_b for item in forced.groups[GroupName.PHONEMES].units)
        legacy = self.report_b.model_dump(mode='json')
        legacy.pop('metric')
        legacy['score'] = 1000
        (self.b / 'report.json').write_text(json.dumps(legacy), encoding='utf-8')
        with self.assertRaises(ValueError):
            compare_reports(self.a, self.b)
        forced = compare_reports(self.a, self.b, allow_incompatible=True)
        assert forced.winner == 'b' and forced.dataset_b.score == 1000
        assert all(item.included_b is None for item in forced.groups[GroupName.PHONEMES].units)
        legacy['groups'].pop(GroupName.PHONEMES)
        (self.b / 'report.json').write_text(json.dumps(legacy), encoding='utf-8')
        with self.assertRaises(ValueError):
            compare_reports(self.a, self.b, allow_incompatible=True)

    def test_invalid_saved_reports(self) -> None:
        """Reject inconsistent saved statistics even when incompatibility is allowed."""
        frequency = {'unit': ['a'], 'count': 2, 'relative_frequency': 2 / 3}
        invalid_groups = {
            'total': 0,
            'unique': 999,
            'frequencies': [frequency, frequency],
            'missing': [('a',)],
            'retained_total': 0,
            'retained_unique': 0,
            'excluded_frequency': 1,
            'evenness': None,
            'effective_diversity': 1.0,
        }
        for field, value in invalid_groups.items():
            with self.subTest(group_field=field):
                data = self.report_a.model_dump(mode='json')
                data['groups']['phonemes'][field] = value
                if field == 'effective_diversity':
                    data['score'] = sum(group['effective_diversity'] for group in data['groups'].values())
                (self.a / 'report.json').write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    compare_reports(self.a, self.b, allow_incompatible=True)
        invalid_frequencies = [
            [{'unit': [], 'count': 3, 'relative_frequency': 1}],
            [{'unit': ['a', 'b'], 'count': 3, 'relative_frequency': 1}],
            [{'unit': ['_'], 'count': 3, 'relative_frequency': 1}],
            [{'unit': ['a'], 'count': 3, 'relative_frequency': 0.5}],
        ]
        for frequencies in invalid_frequencies:
            with self.subTest(frequencies=frequencies):
                data = self.report_a.model_dump(mode='json')
                data['groups']['phonemes'].update(frequencies=frequencies, unique=len(frequencies))
                (self.a / 'report.json').write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    compare_reports(self.a, self.b, allow_incompatible=True)
        invalid_reports = {
            'score': 999,
            'files': 0,
            'lines': 0,
            'groups': {},
            'metric': {'formula': FORMULA_VERSION, 'min_relative_frequency': 1},
        }
        for field, value in invalid_reports.items():
            with self.subTest(dataset_field=field):
                data = self.report_a.model_dump(mode='json')
                data[field] = value
                (self.a / 'report.json').write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    compare_reports(self.a, self.b, allow_incompatible=True)

    def test_localized_comparison_reports_and_escaping(self) -> None:
        """Include original units and incompatibility warnings in all report formats."""
        legacy = self.report_b.model_copy(update={'metric': None})
        (self.b / 'report.json').write_text(legacy.model_dump_json(), encoding='utf-8')
        report = compare_reports(self.a, self.b, allow_incompatible=True)
        report.source_a = '<script>alert(1)</script>'
        languages: tuple[Language, ...] = (Language.EN, Language.RU)
        for language in languages:
            output = self.root / language
            save_comparison(report, output, language)
            html = (output / 'report.html').read_text(encoding='utf-8')
            markdown = (output / 'report.md').read_text(encoding='utf-8')
            assert f'lang="{language}"' in html
            assert '<script>alert(1)</script>' not in html
            assert '&lt;script&gt;' in html
            assert re.search(r'\{\{[a-z_]+\}\}', html) is None
            assert 'only_a' in html and 'only_b' in html
            assert 'a' in markdown and 'b' in markdown
            assert ('WARNING' if language == Language.EN else 'ВНИМАНИЕ') in html
            assert ('WARNING' if language == Language.EN else 'ВНИМАНИЕ') in markdown
            assert json.loads((output / 'report.json').read_text()) == report.model_dump(mode='json')

    def test_parallel_failure_preserves_success_and_skips_comparison(self) -> None:
        """Preserve successful reports and skip comparison after a worker failure."""
        failed: Future[Path] = Future()
        failed.set_exception(ValueError('invalid dataset'))
        successful: Future[Path] = Future()
        successful.set_result(self.b)
        executor = Mock()
        executor.__enter__ = Mock(return_value=executor)
        executor.__exit__ = Mock(return_value=False)
        executor.submit.side_effect = [failed, successful]
        job = AnalysisJob(data_path=self.root / 'dataset.txt', output_root=self.root)
        with (
            patch('phonscope.execution.ProcessPoolExecutor', return_value=executor),
            patch('phonscope.execution.compare_to_reports') as comparison,
            redirect_stdout(io.StringIO()) as stdout,
            redirect_stderr(io.StringIO()),
            self.assertRaises(RuntimeError),
        ):
            analyze_and_compare(job, job, output_root=self.root)
        assert str(self.b) in stdout.getvalue()
        assert (self.b / 'report.json').is_file()
        assert executor.submit.call_count == 2
        comparison.assert_not_called()
