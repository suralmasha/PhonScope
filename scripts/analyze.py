import csv
import logging
import sys
from pathlib import Path

from phonscope.execution import AnalysisJob, analyze_to_reports
from phonscope.locales import TEXT, Language
from phonscope.report import terminal_summary

project_root = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    data_path = project_root / 'path/to/dataset.csv'
    output_root = project_root / 'reports'
    language: Language = Language.RU
    min_relative_frequency = 0.0
    expected_path: Path | None = None

    try:
        job = AnalysisJob(
            data_path=data_path,
            output_root=output_root,
            language=language,
            min_relative_frequency=min_relative_frequency,
            expected_path=expected_path,
        )
        report, report_folder = analyze_to_reports(job)
        sys.stdout.write(terminal_summary(report, language) + f'\n\n{TEXT[language]["directory"]}: {report_folder}\n')

    except (OSError, ValueError, RuntimeError, KeyError, csv.Error) as error:
        logging.getLogger(__name__).error('Analysis failed: %s', error)  # noqa: TRY400
        raise SystemExit(1) from error
