from enum import StrEnum

from .models import GroupName


class Language(StrEnum):
    """Languages supported by reports and progress messages."""

    EN = 'en'
    RU = 'ru'


GROUP_LABELS: dict[Language, dict[GroupName, str]] = {
    Language.EN: {
        GroupName.PHONEMES: 'Phonemes',
        GroupName.PHONEME_BIGRAMS: 'Phoneme pairs',
        GroupName.PHONEME_TRIGRAMS: 'Phoneme triples',
        GroupName.ALLOPHONES: 'Allophones',
        GroupName.ALLOPHONE_BIGRAMS: 'Allophone pairs',
        GroupName.ALLOPHONE_TRIGRAMS: 'Allophone triples',
    },
    Language.RU: {
        GroupName.PHONEMES: 'Фонемы',
        GroupName.PHONEME_BIGRAMS: 'Пары фонем',
        GroupName.PHONEME_TRIGRAMS: 'Тройки фонем',
        GroupName.ALLOPHONES: 'Аллофоны',
        GroupName.ALLOPHONE_BIGRAMS: 'Пары аллофонов',
        GroupName.ALLOPHONE_TRIGRAMS: 'Тройки аллофонов',
    },
}

TEXT: dict[Language, dict[str, str]] = {
    Language.EN: {
        'title': 'Dataset report',
        'subtitle': 'Phonetic composition of a text dataset',
        'source': 'Source',
        'diversity': 'Diversity score',
        'score_note': 'Sum of effective Shannon diversities across six groups',
        'lines': 'Utterances',
        'files': 'Files',
        'warnings': 'Analysis warnings',
        'warning_note': 'Check stress annotations and transcription when warnings occur. Their count is not a '
        'dataset quality score.',
        'diagnostics': 'Diagnostic messages',
        'no_warnings': 'No warnings.',
        'overview': 'Overview',
        'overview_note': 'Unique units and occurrences describe the original data. Effective diversity and '
        'evenness use the retained units after frequency filtering. Evenness is undefined for '
        'fewer than two retained units.',
        'group': 'Group',
        'unique': 'Unique units',
        'total': 'Occurrences',
        'evenness': 'Evenness',
        'undefined': 'Undefined',
        'frequency_title': 'Sounds and combinations',
        'search': 'Search',
        'placeholder': 'Example: m · a',
        'download': 'Download group CSV',
        'frequency_note': 'Symbols in combinations are separated by ·. Shares are relative to all occurrences in '
        'the selected group. CSV includes the entire group regardless of the search filter.',
        'top': 'Most frequent units',
        'all_frequencies': 'All frequencies',
        'unit': 'Unit',
        'share': 'Share, %',
        'previous': 'Previous',
        'next': 'Next',
        'page': 'Page',
        'of': 'of',
        'found': 'Found',
        'empty': 'There are no units in this group.',
        'missing_title': 'Missing expected units',
        'missing_unknown': 'Missing units were not assessed: no expected list was provided.',
        'missing_none': 'No missing units (the expected list may be empty).',
        'expected_custom': 'User-provided list',
        'expected_inventory': 'RuTranscript inventory (standard literary pronunciation)',
        'expected_unknown': 'No expected list provided',
        'expectation_note': 'Expected units only support diagnostics and do not affect diversity or evenness. '
        'RuTranscript follows standard literary pronunciation without modeling spontaneous '
        'speech. Default expected units come from its inventory; no target frequency '
        'distribution is specified.',
        'interpretation': 'Interpreting the results',
        'limitation_size': 'The diversity score is not limited to 0-100. Larger datasets may contain more unique '
        'units; compare scores alongside dataset size and all six counts.',
        'limitation_order': 'Pairs and especially triples usually contribute more to the score than single sounds.',
        'limitation_evenness': 'Evenness only includes observed units. High evenness does not establish complete '
        'coverage or TTS/ASR quality.',
        'limitation_boundaries': 'Results depend on transcription. Combinations cross word boundaries within an '
        'utterance, but never utterance boundaries.',
        'limitation_norm': 'Transcription follows standard literary pronunciation without modeling spontaneous '
        'speech. The score does not measure similarity to natural speech frequencies or '
        'acoustic quality.',
        'summary_note': 'Score combines richness and frequency balance; original frequencies remain available.',
        'analyzing': 'Analyzing dataset...',
        'processed': 'Processed utterances',
        'directory': 'Report directory',
        'open_manually': 'Open the report manually',
        'details_link': 'Interactive HTML report',
        'json_link': 'Full JSON data',
        'diagnostic_note': 'Diagnostic messages are preserved in their original language.',
        'formula_note': 'For each group D = exp(-sum(p * ln(p))); the final score is the sum of six group values. '
        'Probabilities are renormalized after filtering. Empty groups contribute 0, a single '
        'retained unit contributes 1.',
        'metric': 'Formula',
        'threshold': 'Minimum relative frequency',
        'effective_diversity': 'Effective diversity',
        'retained': 'Retained units',
        'excluded': 'Excluded units',
        'excluded_share': 'Excluded share',
        'filtered_note': 'All original units and relative frequencies are shown below, including excluded units. '
        'Score and evenness use only units at or above the threshold. A retained count of 0 '
        'indicates a fully excluded or originally empty group.',
        'comparison_title': 'Dataset comparison',
        'dataset_a': 'Dataset A',
        'dataset_b': 'Dataset B',
        'difference': 'Difference A - B',
        'winner_a': 'Dataset A has the higher diversity score.',
        'winner_b': 'Dataset B has the higher diversity score.',
        'tie': 'The diversity scores are equal; there is no winner.',
        'incompatible': 'WARNING: formula versions or thresholds differ, or metadata is missing. This comparison '
        'was forced. The reported scores are compared as provided and do not establish '
        'superiority under a common metric.',
        'common': 'Shared units',
        'only_a': 'Only in A',
        'only_b': 'Only in B',
        'presence': 'Presence',
        'count_a': 'Occurrences A',
        'count_b': 'Occurrences B',
        'frequency_a': 'Share A, %',
        'frequency_b': 'Share B, %',
        'frequency_difference': 'Share difference A - B, percentage points',
        'included_a': 'Retained in A',
        'included_b': 'Retained in B',
        'yes': 'Yes',
        'no': 'No',
        'comparison_note': 'Presence and frequency differences refer to the complete original distributions, '
        'including units excluded from scoring. Missing units have frequency 0. A higher score '
        'is not proof of better TTS/ASR quality. The score is not normalized by sample size; '
        'small differences are not a significance test.',
        'size_note': 'Dataset size and sampling affect the result. Compare all six groups as well as the final score.',
    },
    Language.RU: {
        'title': 'Отчет о датасете',
        'subtitle': 'Фонетический состав текстового датасета',
        'source': 'Источник',
        'diversity': 'Балл разнообразия',
        'score_note': 'Сумма эффективных разнообразий Шеннона шести групп',
        'lines': 'Реплики',
        'files': 'Файлы',
        'warnings': 'Предупреждения при анализе',
        'warning_note': 'При наличии предупреждений проверьте разметку ударений и корректность транскрипции. Их '
        'количество не является оценкой качества датасета.',
        'diagnostics': 'Сообщения диагностики',
        'no_warnings': 'Предупреждений нет.',
        'overview': 'Обзор',
        'overview_note': 'Уникальные единицы и вхождения описывают исходные данные. Эффективное разнообразие и '
        'равномерность считаются после частотного отсечения. Для менее двух оставшихся единиц '
        'равномерность не определена.',
        'group': 'Группа',
        'unique': 'Уникальных',
        'total': 'Вхождений',
        'evenness': 'Равномерность',
        'undefined': 'Не определена',
        'frequency_title': 'Звуки и сочетания',
        'search': 'Поиск',
        'placeholder': 'Например: m · a',
        'download': 'Скачать CSV группы',
        'frequency_note': 'Символы в сочетаниях разделены знаком ·. Доля считается от всех вхождений выбранной '
        'группы. CSV содержит всю группу независимо от поиска.',
        'top': 'Самые частые единицы',
        'all_frequencies': 'Все частоты',
        'unit': 'Единица',
        'share': 'Доля, %',
        'previous': 'Назад',
        'next': 'Далее',
        'page': 'Страница',
        'of': 'из',
        'found': 'Найдено',
        'empty': 'В этой группе нет единиц.',
        'missing_title': 'Отсутствующие ожидаемые единицы',
        'missing_unknown': 'Отсутствие не оценивалось: ожидаемый список не задан.',
        'missing_none': 'Отсутствующих единиц нет (ожидаемый список может быть пустым).',
        'expected_custom': 'Пользовательский список',
        'expected_inventory': 'Инвентарь RuTranscript (литературная норма)',
        'expected_unknown': 'Ожидаемый список не задан',
        'expectation_note': 'Ожидания используются только для диагностики и не влияют на балл и равномерность. '
        'RuTranscript выполняет транскрипцию по литературной норме произношения, без учета '
        'особенностей спонтанной речи. Ожидаемые единицы по умолчанию берутся из инвентаря '
        'транскрибатора; целевое частотное распределение не задается.',
        'interpretation': 'Как читать результаты',
        'limitation_size': 'Балл разнообразия не ограничен шкалой 0-100. Большие датасеты могут содержать больше '
        'уникальных единиц; сравнивайте балл вместе с объемом и шестью счетчиками.',
        'limitation_order': 'Пары и особенно тройки обычно дают больший вклад в сумму, чем одиночные звуки.',
        'limitation_evenness': 'Равномерность учитывает только найденные единицы. Высокое значение не доказывает '
        'полноту покрытия или качество TTS/ASR.',
        'limitation_boundaries': 'Результат зависит от транскрипции. Сочетания пересекают границы слов внутри '
        'реплики, но не границы реплик.',
        'limitation_norm': 'Транскрипция соответствует литературной норме без учета спонтанной речи. Балл не '
        'оценивает близость к естественным частотам речи или акустическое качество.',
        'summary_note': 'Балл учитывает число единиц и распределение частот; полные исходные частоты сохранены.',
        'analyzing': 'Анализ датасета...',
        'processed': 'Обработано реплик',
        'directory': 'Папка отчетов',
        'open_manually': 'Откройте отчет вручную',
        'details_link': 'Интерактивный HTML-отчет',
        'json_link': 'Полные данные JSON',
        'diagnostic_note': 'Сообщения диагностики сохранены на исходном языке.',
        'formula_note': 'Для каждой группы D = exp(-sum(p * ln(p))); итоговый балл равен сумме шести вкладов. '
        'После отсечения доли перенормируются. Пустая группа дает 0, одна оставшаяся единица дает '
        '1.',
        'metric': 'Формула',
        'threshold': 'Минимальная относительная частота',
        'effective_diversity': 'Эффективное разнообразие',
        'retained': 'Оставшиеся единицы',
        'excluded': 'Исключенные единицы',
        'excluded_share': 'Исключенная доля',
        'filtered_note': 'Ниже показаны все исходные единицы и относительные частоты, включая исключенные. Балл и '
        'равномерность учитывают единицы с долей не ниже порога. Ноль оставшихся единиц означает '
        'полное отсечение или исходно пустую группу.',
        'comparison_title': 'Сравнение датасетов',
        'dataset_a': 'Датасет A',
        'dataset_b': 'Датасет B',
        'difference': 'Разница A - B',
        'winner_a': 'У датасета A выше балл разнообразия.',
        'winner_b': 'У датасета B выше балл разнообразия.',
        'tie': 'Баллы разнообразия равны; победителя нет.',
        'incompatible': 'ВНИМАНИЕ: версии формулы или пороги различаются либо метаданные отсутствуют. Сравнение '
        'выполнено принудительно. Исходные баллы сравниваются как есть и не доказывают '
        'превосходства по единой метрике.',
        'common': 'Общие единицы',
        'only_a': 'Только в A',
        'only_b': 'Только в B',
        'presence': 'Наличие',
        'count_a': 'Вхождения A',
        'count_b': 'Вхождения B',
        'frequency_a': 'Доля A, %',
        'frequency_b': 'Доля B, %',
        'frequency_difference': 'Разница долей A - B, процентные пункты',
        'included_a': 'Учтено в A',
        'included_b': 'Учтено в B',
        'yes': 'Да',
        'no': 'Нет',
        'comparison_note': 'Наличие единиц и разницы частот относятся к полным исходным распределениям, включая '
        'исключенные из расчета единицы. Для отсутствующей единицы частота равна 0. Больший '
        'балл не доказывает лучшего качества TTS/ASR. Нормализации по объему нет; малая '
        'разница не является проверкой статистической значимости.',
        'size_note': 'Объем и состав выборки влияют на результат. Сравнивайте все шесть групп вместе с итоговым '
        'баллом.',
    },
}
