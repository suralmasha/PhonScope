import logging

from phonetic_diversity import get_full_coefficient, get_window_coefficient

if __name__ == '__main__':
    data_path = 'path/to/your/dataset.txt'
    res_window = get_window_coefficient(data_path)
    res_full = get_full_coefficient(data_path)
    logging.basicConfig(level=logging.INFO)
    logging.info('Window coefficient: %s; full coefficient: %s', res_window, res_full)
