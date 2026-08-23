# Measurement results

Dated records of benchmark runs, together with the two reports from the proof of concept.

| File | What it holds |
|---|---|
| `benchmark-<date>.md` | a report from one benchmark run |
| `poc-2026-08-14.md` | the first end-to-end measurement of the proof of concept |
| `skala-2026-08-14.md` | measurement at the scale of 320 and 402 documents |

## Why these files are in Polish

They are **output from the report generator** (`eval/benchmark/raport.py`), not documentation. Rewriting a record of a measurement after the fact would mean editing evidence of what happened, and the next run would produce Polish again in any case.

The right way to change this is to change the labels the generator emits, so that future reports are English while the historical ones stay as the record of the runs that produced them. That change has not been made yet.

Every report carries its date, the model, the seed and the number of cases, so a result can be tied to the version of the system that produced it.

## How to read them

The interpretation lives in [`../../docs/measured-results.md`](../../docs/measured-results.md), including what the system does not achieve and the four hypotheses that measurement rejected.

The method, and why there is no LLM judge, is in [`../benchmark/README.md`](../benchmark/README.md).

## Data policy

The reports contain counts, timings and generated questions. **They never contain document text.** Full run data in `.jsonl` form is excluded from the repository (`.gitignore`), because it can carry fragments of case files.
