from pathlib import Path

from setuptools import find_packages, setup

ROOT = Path(__file__).resolve().parent


if __name__ == '__main__':
    setup(
        name='phonetic_diversity',
        version='0.1.0',
        description='A metric of phonetic diversity and balance of textual data.',
        long_description=(ROOT / 'README.md').read_text(encoding='utf-8'),
        long_description_content_type='text/markdown',
        url='https://github.com/suralmasha/PhonDB',
        classifiers=[
            'Natural Language :: Russian',
            'Programming Language :: Python :: 3.11',
            'Programming Language :: Python :: 3.12',
            'Topic :: Text Processing :: Linguistic',
        ],
        author='Badasyan Alexandra',
        keywords='nlp russian phonetics linguistic voice tts asr',
        author_email='sashabadasyan@icloud.com',
        packages=find_packages(),
        python_requires='>=3.11,<3.13',
        install_requires=(ROOT / 'requirements.txt').read_text(encoding='utf-8').splitlines(),
        extras_require={'dev': ['build==1.4.0', 'ruff==0.15.12']},
        zip_safe=False,
    )
