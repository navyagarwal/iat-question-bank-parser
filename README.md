## IAT question option shuffler

This repo includes a script to parse IAT PDFs and randomize answer option order so
correct answers are no longer always option A.

### Setup

```bash
pip install -r requirements.txt
```

### Usage

```bash
python scripts/shuffle_iat_options.py \
  --input files \
  --output output/shuffled_questions.json \
  --seed 42
```

### Output format

The output JSON file contains a list of objects like:

- `question_no`
- `question`
- `options` (A-D with shuffled text)
- `answer` (new correct label after shuffle)
- `source_pdf`

> Note: the parser assumes the original correct answer is `A` unless changed with
> `--assumed-correct`.
