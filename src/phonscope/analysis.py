import csv
import logging
from collections import Counter
from collections.abc import Callable, Iterator
from math import fsum
from pathlib import Path
from typing import TYPE_CHECKING

from .metrics import group_report
from .models import (
    GROUPS,
    MARKERS,
    DatasetReport,
    ExpectedUnits,
    GroupName,
    MetricSettings,
    Representation,
    Unit,
)

if TYPE_CHECKING:
    from ru_transcript import RuTranscript as Transcriber


def _load_transcriber() -> tuple[type['Transcriber'], frozenset[str], frozenset[str]]:
    """
    Import RuTranscript without retaining Epitran's global logging configuration.

    :return: The transcriber class and its phoneme and allophone inventories.
    """
    root_logger = logging.getLogger()
    handlers, level = root_logger.handlers[:], root_logger.level
    try:
        from ru_transcript import RuTranscript as Transcriber  # noqa: PLC0415 - Isolate dependency import side effects.
        from ru_transcript.data_constants import ALPHABET, KNOWN_PHONEMES  # noqa: PLC0415
    finally:
        for handler in root_logger.handlers[:]:
            if handler not in handlers:
                root_logger.removeHandler(handler)
                handler.close()
        root_logger.setLevel(level)
    return Transcriber, frozenset(KNOWN_PHONEMES), frozenset(ALPHABET)


RuTranscript, KNOWN_PHONEMES, ALPHABET = _load_transcriber()


def _input_files(data_path: str | Path) -> list[Path]:
    """
    Select a file or sorted TXT and CSV files in a directory.

    :param data_path: UTF-8 file or directory containing TXT and CSV files.
    :return: File paths without recursive traversal.
    """
    path = Path(data_path)
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(file for file in path.iterdir() if file.is_file() and file.suffix.lower() in {'.txt', '.csv'})
    message = 'data_path must be a text file or a directory with txt or csv files'
    raise ValueError(message)


def _input_texts(path: Path) -> Iterator[str]:
    """
    Read utterances from TXT lines or the CSV text column.

    :param path: UTF-8 input file with an optional BOM.
    :return: Utterances with separate line and CSV record boundaries.
    """
    with path.open(encoding='utf-8-sig', newline='') as source:
        if path.suffix.lower() != '.csv':
            yield from source
            return
        reader = csv.DictReader(source, strict=True)
        if reader.fieldnames is None or reader.fieldnames.count('text') != 1:
            message = 'CSV must contain exactly one column named text'
            raise ValueError(message)
        for row in reader:
            text = row['text']
            if not isinstance(text, str) or None in row:
                message = f'Invalid CSV record at line {reader.line_num}'
                raise ValueError(message)
            yield ' '.join(text.splitlines())


def _expected_groups(expected: ExpectedUnits) -> dict[GroupName, set[Unit] | None]:
    """
    Build expected inventories while preserving unspecified defaults.

    :param expected: User-provided expected units.
    :return: Expected sets, or None for groups without an inventory.
    """
    inventories = {
        Representation.PHONEMES: set(KNOWN_PHONEMES) - MARKERS,
        Representation.ALLOPHONES: set(ALPHABET) - MARKERS,
    }
    overrides = expected.model_dump(exclude_none=True)
    result: dict[GroupName, set[Unit] | None] = {}
    for name, (representation, order) in GROUPS.items():
        if name in overrides:
            result[name] = {(unit,) if order == 1 else tuple(unit) for unit in overrides[name]}
        elif order == 1:
            result[name] = {(symbol,) for symbol in inventories[representation]}
        else:
            result[name] = None
    return result


def _transcribe_line(text: str) -> dict[Representation, list[str]]:
    """
    Transcribe one line without stress, pauses or word boundaries.

    :param text: One input utterance.
    :return: Phoneme and allophone sequences.
    """
    annotated = text.replace("'", '"')
    transcript = RuTranscript(annotated.replace('+', ''), stressed_text=annotated, stress_place='before')
    transcript.transcribe()
    sounds: dict[Representation, list[str]] = {
        Representation.PHONEMES: [symbol for symbol in transcript.get_phonemes() if symbol not in MARKERS],
        Representation.ALLOPHONES: [symbol for symbol in transcript.get_allophones() if symbol not in MARKERS],
    }
    if bool(sounds[Representation.PHONEMES]) != bool(sounds[Representation.ALLOPHONES]):
        message = 'Transcription must contain both phonemes and allophones'
        raise ValueError(message)
    return sounds


def analyze_dataset(
    data_path: str | Path,
    expected: ExpectedUnits | None = None,
    *,
    progress: Callable[[int], None] | None = None,
    min_relative_frequency: float = 0,
) -> DatasetReport:
    """
    Analyze sound diversity and distribution in a text dataset.

    :param data_path: UTF-8 file or directory containing TXT and CSV files.
    :param expected: Expected units overriding defaults for the specified groups.
    :param progress: Optional callback receiving the processed utterance count.
    :param min_relative_frequency: Minimum unit share within each group, from 0 to 1.
    :return: Diversity score and statistics for all six groups across the dataset.
    """
    metric = MetricSettings(min_relative_frequency=min_relative_frequency)
    expected_groups = _expected_groups(expected if expected is not None else ExpectedUnits())
    files = _input_files(data_path)
    counters: dict[GroupName, Counter[Unit]] = {name: Counter() for name in GROUPS}
    lines = 0
    for path in files:
        for text in _input_texts(path):
            if not text.strip():
                continue
            sounds = _transcribe_line(text)
            if not sounds[Representation.PHONEMES]:
                continue
            lines += 1
            for name, (representation, order) in GROUPS.items():
                sequence = sounds[representation]
                counters[name].update(
                    tuple(sequence[start : start + order]) for start in range(len(sequence) - order + 1)
                )
            if progress is not None:
                progress(lines)
    if not lines:
        message = 'Dataset contains no transcribable text'
        raise ValueError(message)
    groups = {
        name: group_report(counts, expected_groups[name], metric.min_relative_frequency)
        for name, counts in counters.items()
    }
    return DatasetReport(
        score=fsum(group.effective_diversity or 0 for group in groups.values()),
        metric=metric,
        files=len(files),
        lines=lines,
        groups=groups,
    )
