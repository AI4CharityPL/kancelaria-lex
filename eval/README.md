# Measurement harness

The numbers in the main README are reproducible. This directory contains the
code that produces them — and this file explains how to obtain the corpora,
which are **not** in the repository.

## Why the corpora are not here

Two reasons, in this order:

1. **The project's first rule** (T-6, `docs/09-compliance/tajemnica-zawodowa.md`):
   real case files never enter a repository. Even public ones. The habit is the
   protection — an exception "just this once" is how the rule dies.
2. They are large: ~175 MB, which is a hundred times the size of all the code.

`.gitignore` enforces this, and a CI gate checks it on every change.

## What the measurement uses

| Corpus | Size | Source | Licence |
|---|---|---|---|
| `eval/korpus-rzeczywisty/` | 16,3 MB · 320 judgments | **SAOS** — the Polish public case-law portal (`saos.org.pl`) | Public court rulings |
| `eval/sprawa-lacey/` | 158,6 MB · 450 PDFs + 402 txt | **RECAP / CourtListener** — US federal court records | Public court records |
| `eval/korpus-syntetyczny/` | small | **In this repository** — hand-written, fictional | MIT, like the code |

The synthetic corpus **is** included: it is fictional, small, and enough to run
the unit tests. The two real corpora are only needed to reproduce the headline
figures.

Two languages is deliberate. A Polish-only measurement would have hidden a whole
class of bug — several of the mistakes found during development appeared **only**
on English documents, and one appeared only on Polish ones.

## Reproducing the measurement

```bash
# full measurement — the only one the quality gates accept (100 cases)
python -m eval.benchmark.przebieg2 --sprawa 3 --sprawa 4 --par 25

# quick diagnostic — deliberately ignored by the gates (~21 min)
python -m eval.benchmark.przebieg2 --sprawa 3 --sprawa 4 --par 8

# both control arms in one run, without running the model twice
python -m eval.benchmark.przebieg2 --sprawa 3 --sprawa 4 --par 25 --cien
```

A full run takes **70–80 minutes** on 8 GB of VRAM with nothing else competing
for the GPU. Results land in `eval/wyniki/` as JSON.

> **Why the quality gates require the full 100 cases.** The same code scored
> 80,0% on the full set and 73,3% on a 60-case subset of it — seven points of
> difference from question selection alone. Judging a subset against thresholds
> calibrated on the whole set produces the worst kind of false alarm: a credible,
> misleading one.

## How the benchmark is built

Every answerable question has a **twin of identical form** that the files cannot
answer. A system that always answers and a system that always refuses both score
zero. This is the property that makes the numbers mean anything.

Each case also records **where it died** — retrieval, anchoring, support, control
or generation — so a drop in quality points at a stage instead of just a number.

Retrieval is measured **in isolation** (LegalBench-RAG style): whether the
reference sentence reached the model at all. Without it, "the model did not find
the answer" and "the model was never shown the answer" are indistinguishable in
the result — and they need entirely different fixes.

## Reading the results honestly

`docs/22-wyniki-docelowe.md` holds the interpretation, including:

- what the system still does **not** achieve,
- four hypotheses that were tested and **refuted** by measurement,
- why the target of 90% correct refusal is recorded as an open gap rather than
  quietly lowered.

Results in `eval/wyniki/` contain counts, timings and generated questions —
**never document text.**
