from collections import Counter
from math import isclose
from pathlib import Path

from .metrics import group_report
from .models import (
    FORMULA_VERSION,
    GROUPS,
    ComparisonReport,
    DatasetReport,
    DatasetStatistics,
    GroupComparison,
    GroupReport,
    GroupStatistics,
    MetricSettings,
    Presence,
    UnitComparison,
    Winner,
)


def _load_report(folder: str | Path) -> DatasetReport:
    """
    Validate saved statistics against their original frequency tables.

    :param folder: Directory containing report.json.
    :return: A consistent report without modifying its stored statistics.
    """
    report = DatasetReport.model_validate_json((Path(folder) / 'report.json').read_text(encoding='utf-8'))
    if report.metric is None or report.metric.formula != FORMULA_VERSION:
        return report
    for name, group in report.groups.items():
        expected = group_report(
            Counter({item.unit: item.count for item in group.frequencies}),
            None,
            report.metric.min_relative_frequency,
        )
        for field in ('retained_unique', 'retained_total', 'excluded_frequency', 'effective_diversity', 'evenness'):
            actual, value = getattr(group, field), getattr(expected, field)
            if actual is None or value is None:
                matches = actual is value
            elif isinstance(value, float):
                matches = isclose(actual, value, rel_tol=1e-9, abs_tol=1e-12)
            else:
                matches = actual == value
            if not matches:
                message = f'Saved {name}.{field} does not match counts and metric settings; repeat dataset analysis'
                raise ValueError(message)
    return report


def _compare_group(
    group_a: GroupReport, group_b: GroupReport, metric_a: MetricSettings | None, metric_b: MetricSettings | None
) -> GroupComparison:
    """
    Compare original units without replacing saved scores.

    :param group_a: Group from the first report.
    :param group_b: Group from the second report.
    :param metric_a: First metric settings, or None for a legacy report.
    :param metric_b: Second metric settings, or None for a legacy report.
    :return: Original frequencies, A - B differences, presence and score inclusion.
    """
    units_a = {item.unit: item for item in group_a.frequencies}
    units_b = {item.unit: item for item in group_b.frequencies}
    units = []
    for unit in sorted(units_a.keys() | units_b.keys()):
        a, b = units_a.get(unit), units_b.get(unit)
        frequency_a = a.relative_frequency if a is not None else 0.0
        frequency_b = b.relative_frequency if b is not None else 0.0
        if a is None:
            presence = Presence.ONLY_B
        elif b is None:
            presence = Presence.ONLY_A
        else:
            presence = Presence.COMMON
        units.append(
            UnitComparison(
                unit=unit,
                count_a=a.count if a is not None else 0,
                count_b=b.count if b is not None else 0,
                frequency_a=frequency_a,
                frequency_b=frequency_b,
                frequency_difference=frequency_a - frequency_b,
                presence=presence,
                included_a=(a is not None and frequency_a >= metric_a.min_relative_frequency) if metric_a else None,
                included_b=(b is not None and frequency_b >= metric_b.min_relative_frequency) if metric_b else None,
            )
        )
    return GroupComparison(
        dataset_a=GroupStatistics.model_validate(group_a.model_dump(include=set(GroupStatistics.model_fields))),
        dataset_b=GroupStatistics.model_validate(group_b.model_dump(include=set(GroupStatistics.model_fields))),
        common=len(units_a.keys() & units_b.keys()),
        only_a=len(units_a.keys() - units_b.keys()),
        only_b=len(units_b.keys() - units_a.keys()),
        units=units,
    )


def compare_reports(
    folder_a: str | Path, folder_b: str | Path, *, allow_incompatible: bool = False
) -> ComparisonReport:
    """
    Compare two saved JSON reports after validating their statistics.

    :param folder_a: Directory containing the first report.json.
    :param folder_b: Directory containing the second report.json.
    :param allow_incompatible: Explicitly allow incompatible settings with a warning.
    :return: Summary, numerical winner and original frequencies without retranscription.
    """
    a = _load_report(folder_a)
    b = _load_report(folder_b)
    compatible = a.metric is not None and b.metric is not None and a.metric == b.metric
    if not compatible and not allow_incompatible:
        message = (
            'Formula or threshold mismatch, or missing metadata; repeat analysis or explicitly allow incompatibility'
        )
        raise ValueError(message)
    winner = Winner.TIE
    if not isclose(a.score, b.score, rel_tol=1e-12, abs_tol=1e-12):
        winner = Winner.A if a.score > b.score else Winner.B
    return ComparisonReport(
        source_a=str(Path(folder_a).resolve()),
        source_b=str(Path(folder_b).resolve()),
        dataset_a=DatasetStatistics.model_validate(a.model_dump(include=set(DatasetStatistics.model_fields))),
        dataset_b=DatasetStatistics.model_validate(b.model_dump(include=set(DatasetStatistics.model_fields))),
        compatible=compatible,
        forced=not compatible and allow_incompatible,
        winner=winner,
        score_difference=a.score - b.score,
        groups={name: _compare_group(a.groups[name], b.groups[name], a.metric, b.metric) for name in GROUPS},
    )
