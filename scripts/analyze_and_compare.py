import csv
import logging
from pathlib import Path

from phonscope.execution import AnalysisJob, analyze_and_compare
from phonscope.locales import Language

project_root = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    dataset_a = project_root / 'path/to/first/dataset.csv'
    dataset_b = project_root / 'path/to/second/dataset.csv'
    output_root = project_root / 'reports'
    language: Language = Language.RU
    min_relative_frequency = 0.0
    expected_path: Path | None = None

    try:
        job_a = AnalysisJob(
            data_path=dataset_a,
            output_root=output_root,
            language=language,
            min_relative_frequency=min_relative_frequency,
            expected_path=expected_path,
        )
        job_b = job_a.model_copy(update={'data_path': dataset_b})
        analyze_and_compare(job_a, job_b, output_root=output_root, language=language)

    except (OSError, ValueError, RuntimeError, KeyError, csv.Error) as error:
        logging.getLogger(__name__).error('Analysis failed: %s', error)  # noqa: TRY400
        raise SystemExit(1) from error
