# RepoMem Benchmarks

A small, honest retrieval benchmark. It measures **recall@k**: ingest each
example's memories into a throwaway DB, run a query, and check whether the gold
answer appears in the top-k results. Two modes:

- `fts` — the default zero-dependency FTS5 path (queries OR-tokenized, the way
  RepoMem's `answer` primitive queries in production)
- `semantic` — embedding search; requires `pip install repomem[semantic]`

## Quick start (synthetic sample)

```bash
python3 bench/run_benchmark.py --dataset bench/sample_dataset.jsonl --mode fts --k 5
python3 bench/run_benchmark.py --dataset bench/sample_dataset.jsonl --mode semantic --k 5
```

The bundled `sample_dataset.jsonl` is a 3-example smoke test — enough to confirm
the harness runs, **not** a real benchmark.

## Running the real suites

The published comparison numbers require the public eval sets. These are not
vendored (large, separately licensed):

1. **LongMemEval** — https://github.com/xiaowu0162/LongMemEval
2. **LoCoMo** — https://github.com/snap-research/locomo

Convert each into this harness's JSONL format (one object per line):

```json
{
  "id": "q1",
  "memories": [{"type": "learning", "summary": "...", "detail": "..."}],
  "question": "natural-language query",
  "answer_contains": "substring a correct memory must contain"
}
```

- `memories` ← the example's session/haystack turns, one observation each
- `question` ← the eval question
- `answer_contains` ← the gold answer (or a distinctive evidence substring)

Then run both modes and record the output:

```bash
python3 bench/run_benchmark.py --dataset path/to/longmemeval.jsonl --mode fts --k 5
python3 bench/run_benchmark.py --dataset path/to/longmemeval.jsonl --mode semantic --k 5
```

## Results

Run on your own machine and fill this in — **do not commit estimated numbers.**

| Suite        | mode     | k | recall@k |
|--------------|----------|---|----------|
| sample       | fts      | 5 | 1.0      |
| LongMemEval  | fts      | 5 | _TBD_    |
| LongMemEval  | semantic | 5 | _TBD_    |
| LoCoMo       | fts      | 5 | _TBD_    |
| LoCoMo       | semantic | 5 | _TBD_    |

> Methodology note: recall@k over substring-matched gold answers is a coarser
> metric than the LLM-judged accuracy memanto reports (89.8% / 87.1%), so the
> numbers are **not** directly comparable — they measure retrieval, not judged
> answer correctness. State the metric whenever you cite a figure.
