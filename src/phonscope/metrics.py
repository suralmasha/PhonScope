from collections import Counter
from math import exp, fsum, log

from .models import GroupReport, Unit, UnitFrequency


def group_report(counts: Counter[Unit], expected: set[Unit] | None, min_relative_frequency: float = 0) -> GroupReport:
    """
    Calculate effective Shannon diversity after optional filtering.

    :param counts: Original occurrence counts for each unit.
    :param expected: Expected inventory, or None to skip missing-unit diagnostics.
    :param min_relative_frequency: Minimum original share within the group, including the boundary.
    :return: Original frequencies, retained distribution statistics and excluded share.
    """
    total = counts.total()
    frequencies = [
        UnitFrequency(unit=unit, count=count, relative_frequency=count / total)
        for unit, count in sorted(counts.items())
    ]
    retained = [item for item in frequencies if item.relative_frequency >= min_relative_frequency]
    retained_total = sum(item.count for item in retained)
    entropy = -fsum((item.count / retained_total) * log(item.count / retained_total) for item in retained)
    diversity = min(float(len(retained)), max(1.0, exp(entropy))) if retained else 0.0
    evenness = min(1.0, max(0.0, entropy / log(len(retained)))) if len(retained) > 1 else None
    return GroupReport(
        total=total,
        unique=len(counts),
        evenness=evenness,
        frequencies=frequencies,
        missing=sorted(expected - counts.keys()) if expected is not None else None,
        effective_diversity=diversity,
        retained_unique=len(retained),
        retained_total=retained_total,
        excluded_frequency=(total - retained_total) / total if total else 0,
    )
