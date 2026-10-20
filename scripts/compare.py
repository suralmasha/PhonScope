import logging
from pathlib import Path

from phonscope.execution import compare_to_reports
from phonscope.locales import Language

project_root = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    report_a = project_root / 'path/to/first/report-folder'
    report_b = project_root / 'path/to/second/report-folder'
    output_root = project_root / 'reports'
    language: Language = Language.RU
    allow_incompatible = False

    try:
        compare_to_reports(
            report_a, report_b, output_root=output_root, language=language, allow_incompatible=allow_incompatible
        )

    except (OSError, ValueError, KeyError) as error:
        logging.getLogger(__name__).error('Comparison failed: %s', error)  # noqa: TRY400
        raise SystemExit(1) from error
