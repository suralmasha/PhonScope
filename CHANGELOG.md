# Changelog

## 2026-10-20 - [PR #2](https://github.com/suralmasha/PhonScope/pull/2)

### Added

- Phoneme and allophone statistics for single sounds, pairs and triples.
- Relative-frequency filtering and custom expected inventories with missing-unit diagnostics.
- Validated comparison of saved reports and parallel analysis of two datasets.
- English and Russian HTML, JSON and Markdown reports, a CLI, and editable analysis clients.
- Unit tests in CI and pre-commit hooks.
- MIT license.

### Changed

- Renamed the package from `phonetic_diversity` to `phonscope`.
- Replaced the previous coefficients with effective Shannon diversity and Pielou evenness;
  previous scores are not directly comparable with the new metric.
- Added CSV input through the `text` column and preserved utterance boundaries during counting.
- Preserved application logging settings during package import and library analysis.
- Configured Python 3.12 directly in CI.

### Removed

- The `get_full_coefficient` and `get_window_coefficient` API functions.
- The redundant `example.py` script and `.python-version` file.
