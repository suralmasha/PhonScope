import sys

from phonscope import ExpectedUnits, analyze_dataset

if __name__ == '__main__':
    data_path = 'path/to/your/dataset.txt'
    report = analyze_dataset(data_path, expected=ExpectedUnits(phonemes=['a', 'o']))
    sys.stdout.write(report.model_dump_json(indent=2) + '\n')
