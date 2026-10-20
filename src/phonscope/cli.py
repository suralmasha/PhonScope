import argparse
import csv
import logging
import sys
import webbrowser
from enum import StrEnum
from pathlib import Path

from .execution import AnalysisJob, analyze_to_reports
from .locales import TEXT, Language
from .report import terminal_summary

logger = logging.getLogger(__name__)


class OutputFormat(StrEnum):
    """Formats printed to stdout after saving the reports."""

    HTML = 'html'
    JSON = 'json'


def _parser() -> argparse.ArgumentParser:
    """
    Describe dataset analysis and report output arguments.

    :return: The command-line argument parser.
    """
    parser = argparse.ArgumentParser(description='PhonScope - phonetic analysis of text datasets')
    parser.add_argument('data_path', type=Path, help='UTF-8 TXT/CSV file or directory; CSV requires a text column')
    parser.add_argument('--expected', type=Path, help='JSON containing expected units by group')
    parser.add_argument(
        '--language', type=Language, choices=tuple(Language), default=Language.EN, help='Report language (default: en)'
    )
    parser.add_argument(
        '--min-frequency',
        type=float,
        default=0,
        help='Minimum relative frequency within each group, from 0 to 1 (default: 0)',
    )
    parser.add_argument(
        '--output', type=Path, help='Parent directory for timestamped report folders (default: reports)'
    )
    parser.add_argument('--open', action='store_true', help='Open report.html in a browser after analysis')
    parser.add_argument(
        '--format',
        type=OutputFormat,
        choices=tuple(OutputFormat),
        default=OutputFormat.HTML,
        help='Terminal output: summary (html) or JSON; all three reports are always saved',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Save JSON, HTML and Markdown reports and display their directory.

    :param argv: Command-line arguments, or None to use process arguments.
    :return: Zero on success or one on analysis or output failure.
    """
    parser = _parser()
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, force=True)
    if arguments.output is not None and arguments.output.is_file():
        parser.error('--output must be a directory')
    language: Language = arguments.language
    text = TEXT[language]
    try:
        job = AnalysisJob(
            data_path=arguments.data_path,
            output_root=arguments.output or Path('reports'),
            expected_path=arguments.expected,
            language=language,
            min_relative_frequency=arguments.min_frequency,
        )
        report, output = analyze_to_reports(job, show_progress=arguments.format != OutputFormat.JSON)
        directory_message = f'{text["directory"]}: {output.resolve()}\n'
        if arguments.format == OutputFormat.JSON:
            sys.stdout.write(report.model_dump_json(indent=2) + '\n')
            sys.stderr.write(directory_message)
        else:
            sys.stdout.write(terminal_summary(report, language) + '\n\n' + directory_message)
    except (OSError, ValueError, KeyError, RuntimeError, csv.Error) as error:
        logger.error('Analysis failed: %s', error)  # noqa: TRY400 - CLI errors only need a message without a traceback.
        return 1
    if arguments.open and not webbrowser.open((output / 'report.html').resolve().as_uri()):
        sys.stderr.write(f'{text["open_manually"]}: {(output / "report.html").resolve()}\n')
    return 0
