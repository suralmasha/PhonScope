import logging

from phonetic_diversity import get_full_coefficient, get_window_coefficient

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    data_path = 'path/to/your/dataset.txt'
    res_window = get_window_coefficient(data_path)
    res_full = get_full_coefficient(data_path)
    logger.info('Window coefficient: %s; full coefficient: %s', res_window, res_full)
