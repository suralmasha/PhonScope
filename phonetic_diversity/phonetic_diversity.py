import logging
from pathlib import Path

from ru_transcript import get_allophone_info
from tqdm import tqdm

from .transcribator import Transcribator
from .weights import get_weights, safe_divide

logger = logging.getLogger(__name__)


def count_phonemes_and_allophones(sounds: list[str], group: str) -> list[str]:
    """
    Выбирает звуки заданной фонетической группы.

    :param sounds: Последовательность звуков.
    :param group: Название группы.
    :return: Звуки выбранной группы.
    """
    if group == 'vowels':
        group = 'vowel'
    elif group in ['deaf', 'silent']:
        group = 'voiceless'
    if group not in ['vowel', 'sonorous', 'voiced', 'voiceless']:
        raise ValueError(f'Unknown sound group: {group}')

    result = []
    for phon in sounds:
        try:
            if get_allophone_info(phon)['class'] == group:
                result.append(phon)
        except KeyError:
            continue

    return result


def phoneme_allophone_ratio(ph: list[str], al: list[str]) -> float:
    """
    Вычисляет отношение числа уникальных фонем к числу аллофонов.

    :param ph: Фонемы группы.
    :param al: Аллофоны группы.
    :return: Отношение или ноль для пустой группы.
    """
    n_allophones = len(al)
    n_phonemes = len(set(ph))

    return safe_divide(n_phonemes, n_allophones)


def phon_db(
    text_ph: list[str],
    text_al: list[str],
    vowels_weight: float = 0.4,
    sonorous_weight: float = 0.3,
    voiced_weight: float = 0.2,
    voiceless_weight: float = 0.1,
    print_inter_res: bool = False,
) -> float:
    """
    Вычисляет коэффициент по полной транскрипции.

    :param text_ph: Фонемы текста.
    :param text_al: Аллофоны текста.
    :param vowels_weight: Вес гласных.
    :param sonorous_weight: Вес сонорных.
    :param voiced_weight: Вес звонких шумных.
    :param voiceless_weight: Вес глухих шумных.
    :param print_inter_res: Выводить промежуточные значения через logger.
    :return: Взвешенный коэффициент.
    """
    vowels_ph = count_phonemes_and_allophones(text_ph, 'vowels')
    vowels_al = count_phonemes_and_allophones(text_al, 'vowels')
    sonorous_ph = count_phonemes_and_allophones(text_ph, 'sonorous')
    sonorous_al = count_phonemes_and_allophones(text_al, 'sonorous')
    voiced_ph = count_phonemes_and_allophones(text_ph, 'voiced')
    voiced_al = count_phonemes_and_allophones(text_al, 'voiced')
    voiceless_ph = count_phonemes_and_allophones(text_ph, 'voiceless')
    voiceless_al = count_phonemes_and_allophones(text_al, 'voiceless')

    vowels = phoneme_allophone_ratio(vowels_ph, vowels_al)
    sonorous = phoneme_allophone_ratio(sonorous_ph, sonorous_al)
    voiced = phoneme_allophone_ratio(voiced_ph, voiced_al)
    voiceless = phoneme_allophone_ratio(voiceless_ph, voiceless_al)

    if print_inter_res:
        logger.info(
            'Phonetic ratios: vowels=%.8f, sonorous=%.8f, voiced=%.8f, voiceless=%.8f',
            vowels,
            sonorous,
            voiced,
            voiceless,
        )

    x1, x2, x3, x4 = get_weights(len(vowels_al), len(sonorous_al), len(voiced_al), len(voiceless_al))
    vowels_weight = vowels_weight * x1
    sonorous_weight = sonorous_weight * x2
    voiced_weight = voiced_weight * x3
    voiceless_weight = voiceless_weight * x4
    res = round(
        (vowels * vowels_weight + sonorous * sonorous_weight + voiced * voiced_weight + voiceless * voiceless_weight)
        * 100,
        4,
    )

    return res


def phon_db_window(text_ph: list[str], text_al: list[str], window_length: int = 50) -> float:
    """
    Усредняет коэффициенты полных окон по словам.

    :param text_ph: Фонемы текста с границами слов.
    :param text_al: Аллофоны текста с границами слов.
    :param window_length: Положительное число слов в окне.
    :return: Средний коэффициент или коэффициент всего короткого текста.
    """
    if isinstance(window_length, bool) or not isinstance(window_length, int) or window_length <= 0:
        raise ValueError('window_length must be a positive integer')
    words_ph = [word.split() for word in ' '.join(text_ph).split('_') if word.strip()]
    words_al = [word.split() for word in ' '.join(text_al).split('_') if word.strip()]
    if len(words_ph) != len(words_al):
        raise ValueError('Phoneme and allophone word counts must match')

    if len(words_ph) < (window_length + 1):
        ma_par = phon_db(text_ph, text_al)
    else:
        sum_par = 0.0
        denom = len(words_ph) - window_length + 1
        for x in tqdm(range(denom)):
            window_text_ph = [sound for word in words_ph[x : x + window_length] for sound in word]
            window_text_al = [sound for word in words_al[x : x + window_length] for sound in word]
            sum_par += phon_db(window_text_ph, window_text_al)
        ma_par = safe_divide(sum_par, denom)

    return ma_par


def get_window_coefficient(data_path: str | Path, window_length: int = 50) -> float:
    """
    Вычисляет средний коэффициент для текстового датасета.

    :param data_path: Файл или каталог с файлами txt.
    :param window_length: Положительное число слов в окне.
    :return: Средний коэффициент окон.
    """
    if isinstance(window_length, bool) or not isinstance(window_length, int) or window_length <= 0:
        raise ValueError('window_length must be a positive integer')
    transcribator = Transcribator(data_path)
    transcribator.transcribe()
    return phon_db_window(transcribator.phonemes, transcribator.allophones, window_length=window_length)


def get_full_coefficient(data_path: str | Path) -> float:
    """
    Вычисляет коэффициент для полного текстового датасета.

    :param data_path: Файл или каталог с файлами txt.
    :return: Коэффициент полной транскрипции.
    """
    transcribator = Transcribator(data_path)
    transcribator.transcribe()
    return phon_db(transcribator.phonemes, transcribator.allophones)
