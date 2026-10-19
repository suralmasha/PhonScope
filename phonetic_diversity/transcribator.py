import logging
from pathlib import Path

from ru_transcript import RuTranscript
from tqdm import tqdm

logger = logging.getLogger(__name__)


class Transcribator:
    """Транскрибирует текстовый датасет для вычисления метрики."""

    def __init__(self, data_path: str | Path) -> None:
        """
        Подготавливает транскрибирование текстового датасета.

        :param data_path: Файл или каталог с файлами txt.
        """
        self.data_path = Path(data_path)
        self.phonemes: list[str] = []
        self.allophones: list[str] = []
        self.errors: dict[str, Exception] = {}

    def _open_file(self) -> list[str]:
        """
        Читает строки выбранного файла.

        :return: Строки текста в UTF-8.
        """
        return self.data_path.read_text(encoding='utf-8').splitlines()

    def _open_dir(self) -> list[str]:
        """
        Читает текстовые файлы каталога в стабильном порядке.

        :return: Строки текста в UTF-8.
        """
        files = sorted(path for path in self.data_path.iterdir() if path.is_file() and path.suffix.lower() == '.txt')
        data = []
        for path in tqdm(files, desc='Reading text files'):
            data.extend(path.read_text(encoding='utf-8').splitlines())
        return data

    def transcribe(self) -> None:
        """
        Транскрибирует непустые строки, сохраняя границы между ними.

        Ошибки транскрипции передаются вызывающему коду.
        """
        self.phonemes.clear()
        self.allophones.clear()
        self.errors.clear()
        if self.data_path.is_file():
            data = self._open_file()
        elif self.data_path.is_dir():
            data = self._open_dir()
        else:
            message = 'data_path must be a text file or a directory with txt files'
            raise ValueError(message)

        for text in tqdm(data, desc='Transcribing text'):
            if not text.strip():
                continue
            try:
                ru_transcript = RuTranscript(text, stress_place='before')
                ru_transcript.transcribe()
                phonemes = ru_transcript.get_phonemes(save_spaces=True)
                allophones = ru_transcript.get_allophones(save_spaces=True)
            except (ValueError, KeyError, RuntimeError) as error:
                self.errors[text] = error
                raise
            if not phonemes and not allophones:
                continue
            if not phonemes or not allophones:
                message = 'Transcription must contain both phonemes and allophones'
                raise ValueError(message)
            if self.phonemes:
                self.phonemes.append('_')
                self.allophones.append('_')
            self.phonemes.extend(phonemes)
            self.allophones.extend(allophones)

        if not self.phonemes or not self.allophones:
            message = 'Dataset contains no transcribable text'
            raise ValueError(message)

    def see_errors(self) -> None:
        """Выводит сохраненные ошибки через стандартный logger."""
        for error in self.errors.values():
            logger.error('Transcription failed: %s', error)
