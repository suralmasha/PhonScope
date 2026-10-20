from enum import StrEnum
from math import fsum, isclose
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

FORMULA_VERSION = 'shannon-effective-v1'

MARKERS = frozenset({'', '_', '+', '-', '|', '||'})


def _validate_symbol(symbol: str) -> str:
    """
    Validate a sound symbol rather than a boundary marker.

    :param symbol: Transcription symbol.
    :return: The validated symbol.
    """
    if symbol in MARKERS or any(character.isspace() for character in symbol):
        message = 'Sound symbols must be nonempty and contain no whitespace or boundary markers'
        raise ValueError(message)
    return symbol


type Symbol = Annotated[str, AfterValidator(_validate_symbol)]
type Unit = tuple[Symbol, ...]


class Representation(StrEnum):
    """Sound representations returned by the transcriber."""

    PHONEMES = 'phonemes'
    ALLOPHONES = 'allophones'


class GroupName(StrEnum):
    """The six sound groups used by analysis and reports."""

    PHONEMES = 'phonemes'
    PHONEME_BIGRAMS = 'phoneme_bigrams'
    PHONEME_TRIGRAMS = 'phoneme_trigrams'
    ALLOPHONES = 'allophones'
    ALLOPHONE_BIGRAMS = 'allophone_bigrams'
    ALLOPHONE_TRIGRAMS = 'allophone_trigrams'


class Presence(StrEnum):
    """Presence of a unit in the two compared datasets."""

    COMMON = 'common'
    ONLY_A = 'only_a'
    ONLY_B = 'only_b'


class Winner(StrEnum):
    """Numerical outcome of comparing dataset scores."""

    A = 'a'
    B = 'b'
    TIE = 'tie'


GROUPS: dict[GroupName, tuple[Representation, int]] = {
    GroupName.PHONEMES: (Representation.PHONEMES, 1),
    GroupName.PHONEME_BIGRAMS: (Representation.PHONEMES, 2),
    GroupName.PHONEME_TRIGRAMS: (Representation.PHONEMES, 3),
    GroupName.ALLOPHONES: (Representation.ALLOPHONES, 1),
    GroupName.ALLOPHONE_BIGRAMS: (Representation.ALLOPHONES, 2),
    GroupName.ALLOPHONE_TRIGRAMS: (Representation.ALLOPHONES, 3),
}


class ExpectedUnits(BaseModel):
    """Expected inventories overriding defaults for the specified groups."""

    model_config = ConfigDict(extra='forbid')

    phonemes: list[Symbol] | None = None
    phoneme_bigrams: list[tuple[Symbol, Symbol]] | None = None
    phoneme_trigrams: list[tuple[Symbol, Symbol, Symbol]] | None = None
    allophones: list[Symbol] | None = None
    allophone_bigrams: list[tuple[Symbol, Symbol]] | None = None
    allophone_trigrams: list[tuple[Symbol, Symbol, Symbol]] | None = None


class UnitFrequency(BaseModel):
    """Frequency of a phoneme, allophone or sound combination."""

    unit: Unit = Field(min_length=1, max_length=3)
    count: int = Field(gt=0)
    relative_frequency: float = Field(gt=0, le=1)


class MetricSettings(BaseModel):
    """Formula version and relative threshold used to check compatibility."""

    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

    formula: str = Field(default=FORMULA_VERSION, min_length=1)
    min_relative_frequency: float = Field(default=0, ge=0, le=1)


class GroupReport(BaseModel):
    """Statistics for one of the six sound groups."""

    model_config = ConfigDict(allow_inf_nan=False)

    total: int = Field(ge=0)
    unique: int = Field(ge=0)
    evenness: float | None = Field(ge=0, le=1)
    frequencies: list[UnitFrequency]
    missing: list[Unit] | None
    effective_diversity: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    retained_unique: int | None = Field(default=None, ge=0)
    retained_total: int | None = Field(default=None, ge=0)
    excluded_frequency: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode='after')
    def validate_frequencies(self) -> Self:
        """
        Check that counts, frequencies and missing units agree.

        :return: The validated group.
        """
        units = {item.unit for item in self.frequencies}
        if len(units) != len(self.frequencies) or self.unique != len(units):
            message = 'Group unique count must match distinct frequency units without duplicates'
            raise ValueError(message)
        if self.total != sum(item.count for item in self.frequencies):
            message = 'Group total must equal the sum of unit counts'
            raise ValueError(message)
        if any(
            not isclose(item.relative_frequency, item.count / self.total, rel_tol=1e-9, abs_tol=1e-12)
            for item in self.frequencies
        ):
            message = 'Unit relative frequencies must match counts divided by the group total'
            raise ValueError(message)
        if self.missing is not None and (
            len(set(self.missing)) != len(self.missing) or units.intersection(self.missing)
        ):
            message = 'Missing units must be distinct and absent from the frequency table'
            raise ValueError(message)
        return self


class DatasetReport(BaseModel):
    """Diversity score, dataset size and statistics for all six groups."""

    score: float = Field(ge=0, allow_inf_nan=False)
    metric: MetricSettings | None = None
    files: int = Field(gt=0)
    lines: int = Field(gt=0)
    groups: dict[GroupName, GroupReport]

    @model_validator(mode='after')
    def validate_groups(self) -> Self:
        """
        Check group completeness, unit lengths and the current formula score.

        :return: The validated report, including supported legacy reports.
        """
        if set(self.groups) != set(GroupName):
            message = 'Reports must contain all six groups; repeat dataset analysis'
            raise ValueError(message)
        for name, group in self.groups.items():
            order = GROUPS[name][1]
            if any(len(item.unit) != order for item in group.frequencies) or any(
                len(unit) != order for unit in group.missing or []
            ):
                message = f'Unit lengths must match group {name}'
                raise ValueError(message)
        if self.metric is not None and self.metric.formula == FORMULA_VERSION:
            if any(group.effective_diversity is None for group in self.groups.values()):
                message = 'Current formula reports must include effective diversity for every group'
                raise ValueError(message)
            score = fsum(group.effective_diversity or 0 for group in self.groups.values())
            if not isclose(self.score, score, rel_tol=1e-9, abs_tol=1e-12):
                message = 'Dataset score must equal the sum of group effective diversities'
                raise ValueError(message)
        return self


class DatasetStatistics(BaseModel):
    """Dataset size, score and settings without frequency tables."""

    score: float
    files: int
    lines: int
    metric: MetricSettings | None


class GroupStatistics(BaseModel):
    """Summary statistics for comparing one sound group."""

    total: int
    unique: int
    evenness: float | None
    effective_diversity: float | None
    retained_unique: int | None
    excluded_frequency: float | None


class UnitComparison(BaseModel):
    """Original unit frequencies and inclusion in the two scores."""

    unit: Unit
    count_a: int
    count_b: int
    frequency_a: float
    frequency_b: float
    frequency_difference: float
    presence: Presence
    included_a: bool | None
    included_b: bool | None


class GroupComparison(BaseModel):
    """Group summary and comparison of every original unit."""

    dataset_a: GroupStatistics
    dataset_b: GroupStatistics
    common: int
    only_a: int
    only_b: int
    units: list[UnitComparison]


class ComparisonReport(BaseModel):
    """Comparison of scores and frequencies from two saved reports."""

    source_a: str
    source_b: str
    dataset_a: DatasetStatistics
    dataset_b: DatasetStatistics
    compatible: bool
    forced: bool
    winner: Winner
    score_difference: float
    groups: dict[GroupName, GroupComparison]
