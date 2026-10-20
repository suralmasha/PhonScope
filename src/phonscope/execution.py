import logging
import sys
import tempfile
import warnings
from collections.abc import Generator
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .analysis import analyze_dataset
from .comparison import compare_reports
from .comparison_report import comparison_conclusion, save_comparison
from .locales import TEXT, Language
from .models import DatasetReport, ExpectedUnits
from .report import save_reports

logger = logging.getLogger(__name__)


class AnalysisJob(BaseModel):
    """Shared settings for sequential and parallel analysis clients."""

    model_config = ConfigDict(allow_inf_nan=False)

    data_path: Path
    output_root: Path = Path('reports')
    language: Language = Language.EN
    min_relative_frequency: float = Field(default=0, ge=0, le=1)
    expected_path: Path | None = None


class _Diagnostics(logging.Handler):
    """Collect warnings without replacing application logging handlers."""

    def __init__(self) -> None:
        """Create a warning collector for one analysis run."""
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        """
        Record a warning while existing handlers control terminal output.

        :param record: Logging event.
        """
        if record.levelno == logging.WARNING:
            self.messages.append(record.getMessage())


@contextmanager
def _capture_warnings(diagnostics: _Diagnostics) -> Generator[None]:
    """
    Collect logging and Python warnings and restore the original handlers.

    :param diagnostics: Warning collector for the report.
    :return: Analysis context that preserves diagnostics even on failure.
    """
    root_logger = logging.getLogger()
    root_logger.addHandler(diagnostics)
    with warnings.catch_warnings(record=True) as captured:
        try:
            yield
        finally:
            root_logger.removeHandler(diagnostics)
            diagnostics.close()
            for item in captured:
                diagnostics.messages.append(str(item.message))
                sys.stderr.write(
                    warnings.formatwarning(item.message, item.category, item.filename, item.lineno, item.line)
                )


def _progress(lines: int, *, language: Language = Language.EN, label: str = '') -> None:
    """
    Display the processed utterance count alongside diagnostics.

    :param lines: Number of utterances with nonempty transcriptions.
    :param language: Language of progress messages.
    :param label: Dataset name for parallel runs.
    """
    if lines == 1 or lines % 100 == 0:
        sys.stderr.write(f'{label} | {TEXT[language]["processed"]}: {lines}\n')


def new_report_directory(output_root: Path, name: str) -> Path:
    """
    Create a unique report directory with local time and UTC offset.

    :param output_root: Parent directory for independent results.
    :param name: Dataset name or comparison label.
    :return: Absolute path to a new directory without overwriting prior runs.
    """
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime('%Y%m%d_%H%M%S_%f%z')
    prefix = f'{Path(name).name[:80] or "dataset"}_{stamp}_'
    return Path(tempfile.mkdtemp(prefix=prefix, dir=output_root)).resolve()


def analyze_to_reports(job: AnalysisJob, *, show_progress: bool = True) -> tuple[DatasetReport, Path]:
    """
    Run the same analysis for sequential and parallel clients.

    :param job: Dataset, metric settings and output directory.
    :param show_progress: Display progress without suppressing diagnostics.
    :return: The report and its new directory containing JSON, HTML and Markdown.
    """
    diagnostics = _Diagnostics()
    expected = (
        ExpectedUnits.model_validate_json(job.expected_path.read_text(encoding='utf-8'))
        if job.expected_path is not None
        else None
    )
    if job.output_root.is_file():
        message = 'Output root must be a directory'
        raise ValueError(message)
    if show_progress:
        sys.stderr.write(f'{TEXT[job.language]["analyzing"]} {job.data_path}\n')
    with _capture_warnings(diagnostics):
        report = analyze_dataset(
            job.data_path,
            expected=expected,
            min_relative_frequency=job.min_relative_frequency,
            progress=partial(_progress, language=job.language, label=job.data_path.name) if show_progress else None,
        )
    output = new_report_directory(job.output_root, job.data_path.resolve().stem)
    save_reports(
        report, job.data_path, output, expected=expected, warning_messages=diagnostics.messages, language=job.language
    )
    return report, output


def compare_to_reports(
    folder_a: Path,
    folder_b: Path,
    *,
    output_root: Path = Path('reports'),
    language: Language = Language.EN,
    allow_incompatible: bool = False,
) -> Path:
    """
    Compare two saved report directories using the shared workflow.

    :param folder_a: First report directory.
    :param folder_b: Second report directory.
    :param output_root: Parent directory for the new comparison.
    :param language: Language of readable reports.
    :param allow_incompatible: Explicitly allow incompatible settings with a warning.
    :return: The new comparison directory.
    """
    report = compare_reports(folder_a, folder_b, allow_incompatible=allow_incompatible)
    output = new_report_directory(output_root, 'comparison')
    save_comparison(report, output, language)
    sys.stdout.write(comparison_conclusion(report, language) + f'\n{TEXT[language]["directory"]}: {output}\n')
    return output


def _analyze_worker(job: AnalysisJob) -> Path:
    """
    Save reports in a worker and return only their directory.

    :param job: The same analysis settings used by the sequential client.
    :return: Directory containing the completed reports.
    """
    logging.basicConfig(level=logging.WARNING)
    return analyze_to_reports(job)[1]


def analyze_and_compare(
    job_a: AnalysisJob, job_b: AnalysisJob, *, output_root: Path = Path('reports'), language: Language = Language.EN
) -> Path:
    """
    Analyze two datasets in parallel and compare their saved reports.

    :param job_a: First dataset settings.
    :param job_b: Second dataset settings.
    :param output_root: Parent directory for comparison results.
    :param language: Language of comparison reports.
    :return: The comparison directory, or an exception after both workers finish.
    """
    folders: dict[str, Path] = {}
    failures: list[Exception] = []
    with ProcessPoolExecutor(max_workers=2) as executor:
        pending = {executor.submit(_analyze_worker, job_a): 'a', executor.submit(_analyze_worker, job_b): 'b'}
        for future in as_completed(pending):
            try:
                folder = future.result()
            except Exception as error:
                failures.append(error)
                logger.error('Dataset analysis failed: %s', error)  # noqa: TRY400 - The final error is raised below.
            else:
                folders[pending[future]] = folder
                sys.stdout.write(f'{TEXT[language]["directory"]}: {folder}\n')
    if failures:
        message = 'Dataset analysis failed; successful reports were preserved; no comparison was created'
        raise RuntimeError(message) from failures[0]
    return compare_to_reports(folders['a'], folders['b'], output_root=output_root, language=language)
