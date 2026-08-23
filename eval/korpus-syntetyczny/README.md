# Synthetic corpus

**Every document in this directory is fictional.** The people, cases, references and events were invented for testing.

## Why a synthetic corpus

A lawyer does not discuss the details of a case with an outsider. The same rule applies to tools: real case files do not go into the repository, into a test environment, or into the context of external tools (requirement T-6 in [`../../docs/compliance/legal-professional-privilege.md`](../../docs/compliance/legal-professional-privilege.md)).

The corpus is meant to reproduce the **structure and the difficulties** of real documents, not real data.

## Rules for building it

| Rule | Reason |
|---|---|
| Names from a fictional list, never from real cases | Self-evident |
| Case references in valid format but with non-existent numbers | Exercises pattern validation |
| Dates internally consistent | Exercises the deadline engine |
| **Deliberate discrepancies between documents** | Exercises agent A-5 |
| **Deliberate gaps in the information** | Exercises refusal to answer (gate J-3) |
| Scans of varying quality | Exercises the character error rate (gates J-5, J-6) |
| Variants with an injected instruction | Kept separately in [`../../tests/injection/`](../../tests/injection/) |

## Contents

| File | Kind | What it exercises |
|---|---|---|
| `01-protokol-przesluchania-kowalski.txt` | record of a witness examination | extraction, citation |
| `02-protokol-przesluchania-nowak.txt` | record, **inconsistent with 01** | the discrepancy agent A-5 |
| `03-postanowienie-doreczenie.txt` | court order with a date of service | the deadline engine, A-2 |
| `04-akt-oskarzenia.txt` | indictment | classification, metadata |

The documents are deliberately short: they exercise the mechanics rather than performance. A performance corpus of hundreds of pages is built separately in Phase 7.

The file names and the document text are Polish, because the corpus imitates Polish procedural documents. That is the material the system is built for.

## Gold set

Questions and verified answers live in `eval/gold-set/`, which is **not in this
repository**: it needs a lawyer's time to build and today holds six questions,
which is why measure J-2 is recorded as unmeasurable.

Answers in the gold set are verified **by a human**. We deliberately do not use a model as a judge, because an LLM judge lets hallucinations through (ADR-0006).
