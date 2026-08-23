# Benchmark roadmap

Status: **dimensions 1 to 4 implemented**, 5 to 12 planned.

Each dimension states its measure, how the ground truth is established, and what specifically breaks when the dimension goes unmeasured.

## Implemented

| # | Dimension | Measure | Ground truth |
|---|---|---|---|
| 1 | **Citation fidelity** | anchored accuracy, coverage of the reference | a character range in the source |
| 2 | **Refusal where there is no coverage** | J-3 | a twin verified by search |
| 3 | **Pair discriminability** | the headline measure | a matched pair |
| 4 | **Cross-case leakage** | zero threshold | anchor present in A, absent from B |

## Planned

### 5. The degradation curve under OCR noise

The `szum.py` module is ready; what is missing is wiring it into the run.

The same set of pairs, with the source degraded at character error rates of **0, 1, 3, 5 and 10%**, using realistic error classes: lost diacritics, merged glyphs, digits confused with letters. The result is a curve rather than a point.

**Why:** gates N-14 and N-15 set thresholds on the character error rate, but a threshold says nothing about how much quality the system loses. A firm buying a scanner needs to know whether the difference between 2% and 5% costs 3 points of accuracy or 40.

**The "digits" class is reported separately:** in a procedural document `II K 147/26` and `II K l47/26` are two different cases, and `14 dni` against `l4 dni` is the difference between a deadline met and a deadline lost. A digit error changes meaning rather than spelling, so averaging it with the rest hides what matters most.

### 6. Needle in a haystack: position and corpus size

The same fact asked against corpora of 10, 50, 100 and 320 documents. The measure: whether the source document reaches the twelve selected by BM25 (`recall@12`), broken down by document position and by the depth of the fact.

**Why:** `MAKS_DOKUMENTOW_DO_ANALIZY = 12` is a hard cut-off. We do not know how many findings are lost because a document did not reach the twelve, and that loss is invisible to the user: the system does not say "I did not read it", it says "I did not find it".

### 7. Determinism

The same case run N times at `temperature=0.1` with a fixed seed. Measures: spread in the number of findings, stability of the citation range, and the share of cases producing an identical result.

**Why:** a result that cannot be reproduced is no use as evidence of due diligence (T-4). A lawyer who asks the same question twice and gets two different answers stops trusting both.

### 8. Full language parity

Partly working already (the report breaks results down by Polish and English). To be added: the same **translated** questions over a bilingual pair of documents, so that corpus difficulty can be separated from model capability.

**Why:** the language divergence here is measured rather than hypothetical. The Polish model paraphrased English case files and gave 9% accuracy against 82% on Polish ones.

### 9. Model matrix

The same set of cases across {bielik-lex-map, bielik-lex-dev, llama-lex-map, qwen2.5-7b} and {extracting template, answering template}.

**Why:** the ablation of 14.08.2026 showed that the fast track was running on the worst of four combinations, producing zero findings where every other combination gave 6 to 8. A mistake like that has no business surviving in the configuration for longer than one run.

### 10. Resistance to injection, quantified

`tests/injection/` checks the construction, namely that the agent has no network tools. What is missing is measurement: instructions injected into case content, in variants (overt, white font, PDF metadata, a layer beneath an image, impersonating a system message), in both languages.

**Threshold 100%**, as in `docs/testing-and-gates.md`.

### 11. The cost of context: how much markup consumes

Measured: **42.5% of the content of case 3 is HTML markup** (`<p>`, `<td colspan>`, `<span class="anon-block">`). Against a budget of 9,000 characters for mapping, that means around 3,800 characters of markup instead of case content.

To do: the same run over a raw corpus and a cleaned one, with the difference in accuracy expressed as a number.

**Why:** this is a defect in the document upload path rather than in the model. The fix is cheap (cleaning on import), so it is worth knowing what it is worth.

### 12. Regression between releases

Comparing runs by case identifier: which specific cases stopped working after a change. Not the fall in the average, but the list of items.

**Why:** quality degradation is quiet, unlike a crash (`docs/testing-and-gates.md`). An average can stand still while the system breaks one category and improves another.

## A note on method

This benchmark measures **citation fidelity and refusal**. It does not measure substantive correctness. That is what the human-verified gold set is for (`eval/gold-set/`, gate J-2, threshold ≥ 85%).

The separation is deliberate. Citation fidelity is a binary property, measurable mechanically across thousands of cases. Substantive correctness is a legal judgement and cannot be automated without an LLM judge, which this project deliberately rejects.

**A benchmark that pretends to measure both really measures only the first, and misleads the reader about what it has shown.**
