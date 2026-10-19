def safe_divide(numerator: float, denominator: float) -> float:
    """
    Делит числа с обработкой нулевого знаменателя.

    :param numerator: Числитель.
    :param denominator: Знаменатель.
    :return: Частное или ноль.
    """
    try:
        return numerator / denominator
    except ZeroDivisionError:
        return 0.0


def get_weights(vowels: int, sonorous: int, voiced: int, voiceless: int) -> list[float]:
    """
    Вычисляет процентные доли фонетических групп.

    :param vowels: Число гласных.
    :param sonorous: Число сонорных.
    :param voiced: Число звонких шумных.
    :param voiceless: Число глухих шумных.
    :return: Веса групп в исходном порядке.
    """
    groups = {'vowels': vowels, 'sonorous': sonorous, 'voiced': voiced, 'voiceless': voiceless}
    full_sum = sum(list(groups.values()))

    weights = []
    for v in groups.values():
        w = round(safe_divide((v * 100), full_sum), 2)
        weights.append(w)

    return weights
