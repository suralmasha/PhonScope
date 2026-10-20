import json
from html import escape
from pathlib import Path

from .locales import GROUP_LABELS, TEXT, Language
from .models import ComparisonReport, UnitComparison, Winner


def _value(value: str | float | None, language: Language) -> str:
    """
    Format a number or an unavailable legacy value.

    :param value: Label, statistic or None for a legacy report.
    :param language: Language of the unavailable-value label.
    :return: Readable text without modifying stored JSON values.
    """
    if value is None:
        return TEXT[language]['undefined']
    return f'{value:.6g}' if isinstance(value, float) else str(value)


def _summary_rows(report: ComparisonReport, language: Language) -> list[list[str]]:
    """
    Build a table of dataset statistics and A - B differences.

    :param report: Dataset comparison result.
    :param language: Language of labels.
    :return: Rows for HTML, Markdown and terminal output.
    """
    text = TEXT[language]
    rows = []
    for field in ('score', 'files', 'lines'):
        a, b = getattr(report.dataset_a, field), getattr(report.dataset_b, field)
        label = text['diversity'] if field == 'score' else text[field]
        rows.append([label, _value(a, language), _value(b, language), _value(a - b, language)])
    for field, label in (('formula', 'metric'), ('min_relative_frequency', 'threshold')):
        a = getattr(report.dataset_a.metric, field, None)
        b = getattr(report.dataset_b.metric, field, None)
        rows.append([text[label], _value(a, language), _value(b, language), '-'])
    for name, group in report.groups.items():
        for field, label in (
            ('unique', 'unique'),
            ('total', 'total'),
            ('effective_diversity', 'effective_diversity'),
            ('evenness', 'evenness'),
            ('retained_unique', 'retained'),
            ('excluded_frequency', 'excluded_share'),
        ):
            a, b = getattr(group.dataset_a, field), getattr(group.dataset_b, field)
            difference = a - b if a is not None and b is not None else None
            rows.append(
                [
                    f'{GROUP_LABELS[language][name]} / {text[label]}',
                    _value(a, language),
                    _value(b, language),
                    _value(difference, language),
                ]
            )
        for field in ('common', 'only_a', 'only_b'):
            count = getattr(group, field)
            a = count if field != 'only_b' else 0
            b = count if field != 'only_a' else 0
            rows.append([f'{GROUP_LABELS[language][name]} / {text[field]}', str(a), str(b), str(a - b)])
    return rows


def _unit_values(unit: UnitComparison, language: Language) -> list[str]:
    """
    Build a unit frequency row including filtering status.

    :param unit: Unit frequencies from the two original datasets.
    :param language: Language of presence labels.
    :return: Values in detailed table column order.
    """
    text = TEXT[language]
    values = [' · '.join(unit.unit), text[unit.presence], str(unit.count_a), str(unit.count_b)]
    values.extend(
        _value(value * 100, language) for value in (unit.frequency_a, unit.frequency_b, unit.frequency_difference)
    )
    values.extend(
        text['undefined'] if included is None else text['yes'] if included else text['no']
        for included in (unit.included_a, unit.included_b)
    )
    return values


def _markdown_row(values: list[str]) -> str:
    """
    Escape Markdown table cell contents.

    :param values: Cell contents.
    :return: A table row without embedded HTML or column separators.
    """
    return '| ' + ' | '.join(escape(value).replace('|', '&#124;').replace('\n', ' ') for value in values) + ' |'


def comparison_conclusion(report: ComparisonReport, language: Language = Language.EN) -> str:
    """
    Describe the numerical outcome and warn about incompatibility.

    :param report: Comparison of saved scores.
    :param language: Output language.
    :return: A conclusion without claims about speech model quality.
    """
    text = TEXT[language]
    conclusion = text['tie'] if report.winner == Winner.TIE else text['winner_' + report.winner]
    return (text['incompatible'] + '\n\n' if not report.compatible else '') + conclusion


def save_comparison(report: ComparisonReport, output: Path, language: Language = Language.EN) -> None:
    """
    Save JSON, standalone HTML and complete Markdown comparisons.

    :param report: Comparison of two saved dataset reports.
    :param output: New directory for comparison results.
    :param language: Language of readable reports.
    """
    text = TEXT[language]
    headers = [text['group'], text['dataset_a'], text['dataset_b'], text['difference']]
    rows = _summary_rows(report, language)
    conclusion = comparison_conclusion(report, language)
    markdown = [
        f'# PhonScope - {text["comparison_title"]}',
        '',
        conclusion,
        '',
        f'{text["dataset_a"]}: {escape(report.source_a)}',
        '',
        f'{text["dataset_b"]}: {escape(report.source_b)}',
        '',
        _markdown_row(headers),
        '| --- | --- | --- | --- |',
    ]
    markdown.extend(_markdown_row(row) for row in rows)
    markdown.extend(['', text['comparison_note'], '', text['size_note']])
    unit_headers = [
        text[key]
        for key in (
            'unit',
            'presence',
            'count_a',
            'count_b',
            'frequency_a',
            'frequency_b',
            'frequency_difference',
            'included_a',
            'included_b',
        )
    ]
    for name, group in report.groups.items():
        markdown.extend(
            [
                '',
                f'## {GROUP_LABELS[language][name]}',
                '',
                _markdown_row(unit_headers),
                '| ' + ' --- |' * len(unit_headers),
            ]
        )
        markdown.extend(_markdown_row(_unit_values(unit, language)) for unit in group.units)
    template = Path(__file__).with_name('comparison.html').read_text(encoding='utf-8')
    styles = (
        Path(__file__).with_name('report.html').read_text(encoding='utf-8').split('<style>')[1].split('</style>')[0]
    )
    for key, value in text.items():
        template = template.replace('{{' + key + '}}', escape(value))
    summary = '<thead><tr>' + ''.join(f'<th>{escape(header)}</th>' for header in headers) + '</tr></thead><tbody>'
    summary += ''.join('<tr>' + ''.join(f'<td>{escape(value)}</td>' for value in row) + '</tr>' for row in rows)
    payload = report.model_dump(mode='json') | {'ui': text, 'labels': GROUP_LABELS[language], 'language': language}
    data = (
        json.dumps(payload, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    )
    html = (
        template.replace('{{language}}', language)
        .replace('/*STYLES*/', styles)
        .replace('<!--SUMMARY-->', summary + '</tbody>')
        .replace('<!--CONCLUSION-->', escape(conclusion).replace('\n', '<br>'))
        .replace('<!--SOURCE_A-->', escape(report.source_a))
        .replace('<!--SOURCE_B-->', escape(report.source_b))
        .replace('/*REPORT_DATA*/', data)
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / 'report.json').write_text(report.model_dump_json(indent=2) + '\n', encoding='utf-8')
    (output / 'report.html').write_text(html, encoding='utf-8')
    (output / 'report.md').write_text('\n'.join(markdown) + '\n', encoding='utf-8')
