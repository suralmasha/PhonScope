import json
from html import escape
from pathlib import Path

from .locales import GROUP_LABELS, TEXT, Language
from .models import DatasetReport, ExpectedUnits, GroupName


def _summary_rows(report: DatasetReport, language: Language) -> list[list[str]]:
    """
    Build localized summary rows for the six sound groups.

    :param report: Dataset analysis result.
    :param language: Language of labels.
    :return: Headers and statistics without changing numeric values.
    """
    text = TEXT[language]
    rows = [
        [
            text[key]
            for key in ('group', 'unique', 'total', 'effective_diversity', 'evenness', 'retained', 'excluded_share')
        ]
    ]
    for name, group in report.groups.items():
        evenness = text['undefined'] if group.evenness is None else f'{group.evenness:.3f}'
        diversity = text['undefined'] if group.effective_diversity is None else f'{group.effective_diversity:.3f}'
        excluded = text['undefined'] if group.excluded_frequency is None else f'{group.excluded_frequency:.3%}'
        rows.append(
            [
                GROUP_LABELS[language][name],
                str(group.unique),
                str(group.total),
                diversity,
                evenness,
                str(group.retained_unique),
                excluded,
            ]
        )
    return rows


def terminal_summary(report: DatasetReport, language: Language = Language.EN) -> str:
    """
    Build a compact terminal summary.

    :param report: Dataset analysis result.
    :param language: Summary language, defaulting to English.
    :return: Dataset size, diversity and group evenness.
    """
    text = TEXT[language]
    rows = [
        f'PhonScope | {text["files"]}: {report.files} | {text["lines"]}: {report.lines}',
        f'{text["diversity"]}: {report.score:.6f}',
        '',
    ]
    rows.extend(' | '.join(values) for values in _summary_rows(report, language))
    rows.append('\n' + text['summary_note'])
    if report.metric is not None:
        rows.append(
            f'{text["metric"]}: {report.metric.formula}; {text["threshold"]}: {report.metric.min_relative_frequency:g}'
        )
    return '\n'.join(rows)


def render_report(
    report: DatasetReport,
    source: Path,
    expected: ExpectedUnits | None = None,
    warning_messages: list[str] | None = None,
    language: Language = Language.EN,
) -> str:
    """
    Render a standalone HTML report with frequency tables.

    :param report: Dataset analysis result.
    :param source: Input path without the original utterances.
    :param expected: User inventories used to explain expectation sources.
    :param warning_messages: Diagnostic messages to display in the report.
    :param language: Report language, defaulting to English.
    :return: HTML without external resources.
    """
    template = Path(__file__).with_name('report.html').read_text(encoding='utf-8')
    text = TEXT[language]
    payload = report.model_dump(mode='json')
    payload['labels'] = GROUP_LABELS[language]
    payload['ui'] = text
    payload['language'] = language
    payload['expectations'] = {
        name: text['expected_custom']
        if expected is not None and getattr(expected, name) is not None
        else text['expected_inventory']
        if name in {GroupName.PHONEMES, GroupName.ALLOPHONES}
        else text['expected_unknown']
        for name in report.groups
    }
    for key, value in text.items():
        template = template.replace('{{' + key + '}}', escape(value))
    data = (
        json.dumps(payload, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    )
    details = ''.join(f'<li>{escape(message)}</li>' for message in dict.fromkeys(warning_messages or []))
    return (
        template.replace('{{language}}', language)
        .replace('<!--SOURCE-->', escape(str(source)))
        .replace('<!--WARNINGS-->', str(len(warning_messages or [])))
        .replace('<!--WARNING_DETAILS-->', details or f'<li>{escape(text["no_warnings"])}</li>')
        .replace('/*REPORT_DATA*/', data)
    )


def render_markdown(
    report: DatasetReport, source: Path, warning_messages: list[str] | None = None, language: Language = Language.EN
) -> str:
    """
    Render a readable summary with links to complete results.

    :param report: Dataset analysis result.
    :param source: Path to the input data.
    :param warning_messages: Original diagnostic messages.
    :param language: Report language, defaulting to English.
    :return: Markdown containing group statistics and interpretation notes.
    """
    text = TEXT[language]
    rows = [
        f'# PhonScope - {text["title"]}',
        '',
        f'{text["source"]}: {escape(str(source))}',
        '',
        f'- {text["diversity"]}: **{report.score}**',
        f'- {text["files"]}: {report.files}',
        f'- {text["lines"]}: {report.lines}',
        f'- {text["warnings"]}: {len(warning_messages or [])}',
        '',
        f'## {text["overview"]}',
        '',
    ]
    for index, values in enumerate(_summary_rows(report, language)):
        rows.append('| ' + ' | '.join(values) + ' |')
        if index == 0:
            rows.append('| --- | ' + ' ---: |' * (len(values) - 1))
    rows.extend(['', text['overview_note'], '', text['formula_note'], '', text['filtered_note']])
    if report.metric is not None:
        rows.extend(
            [
                '',
                f'{text["metric"]}: {report.metric.formula}; '
                f'{text["threshold"]}: {report.metric.min_relative_frequency:g}',
            ]
        )
    rows.extend(['', f'## {text["interpretation"]}', ''])
    rows.extend(
        '- ' + text[key]
        for key in (
            'limitation_size',
            'limitation_order',
            'limitation_evenness',
            'limitation_boundaries',
            'limitation_norm',
        )
    )
    rows.extend(
        [
            '',
            f'[{text["details_link"]}](report.html) | [{text["json_link"]}](report.json)',
            '',
            f'## {text["diagnostics"]}',
            '',
            text['diagnostic_note'],
            '',
        ]
    )
    rows.extend('- ' + escape(message).replace('\n', ' ') for message in dict.fromkeys(warning_messages or []))
    if not warning_messages:
        rows.append(text['no_warnings'])
    return '\n'.join(rows) + '\n'


def save_reports(  # noqa: PLR0913 - Pass parameters for all three representations explicitly.
    report: DatasetReport,
    source: Path,
    output: Path,
    *,
    expected: ExpectedUnits | None = None,
    warning_messages: list[str] | None = None,
    language: Language = Language.EN,
) -> None:
    """
    Save JSON and two readable representations in one directory.

    :param report: Analysis result with its original JSON structure.
    :param source: Path to the input data.
    :param output: Directory for the three report files.
    :param expected: User inventories described in HTML.
    :param warning_messages: Complete diagnostic messages.
    :param language: Language of HTML and Markdown.
    """
    contents = {
        'report.json': report.model_dump_json(indent=2) + '\n',
        'report.html': render_report(report, source, expected, warning_messages, language),
        'report.md': render_markdown(report, source, warning_messages, language),
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, content in contents.items():
        (output / name).write_text(content, encoding='utf-8')
