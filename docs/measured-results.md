# Measured results: the best and the target

Everything measured up to **16.08.2026**. The document serves two purposes at once: showing what the system can do in its best configuration, and recording what it does not yet achieve, because a table containing only good numbers stops being a measurement and becomes marketing material.

> **How to read these numbers.** "Correct in total" means hits on answerable questions **plus** justified refusals on questions with no coverage. It is the only measure resistant to both degenerations: "always answer" and "always refuse" each score zero on it.

## 1. Best results: what the system is capable of

| Measure | Best measured result | Conditions |
|---|---|---|
| **Citations inconsistent with the source** | **0** | every measurement, without exception |
| **Accuracy with a single document** | **8 of 8** | case 4, one document selected, around 5 s |
| **Correct refusal (J-3)** | **8 of 8** | the same set |
| **False answers** | **0** | the same set |
| **Retrieval recall** | **96 to 100%** | the reference sentence reached the model |
| **Median time** | **around 5 s** | one document |
| **Data sent outside** | **0 bytes** | every run |

**The zero in the first row matters most and is not a matter of luck.** The model indicates only a sentence NUMBER, and the code reconstructs the citation text straight from the document (ADR-0007). A citation is not rejected at verification; it is **inexpressible**. For comparison, a Stanford University study found **17 to 34% fabricated citations** in leading commercial legal tools.

### Select less, get more

Measured on nine questions where the system had previously refused:

| Documents selected | Hits | Mean time |
|---|---|---|
| **1 document** | **8 of 9** | around 5 s |
| 4 documents | 4 of 9 | 13.4 s |
| the whole case (12 documents) | 2 of 9 | 18.7 s |

A fourfold difference in accuracy with the same model. The cause is the "lost in the middle" effect: the more material unrelated to the question, the worse the model is at finding the right sentence.

## 2. The shipping configuration and the full comparison

Every variant was measured in **a single run** in shadow mode (100 cases, the full corpus, 16.08.2026, after the discriminator extractor was fixed), so the differences between them come from the layers rather than from differing conditions:

| Variant | Accuracy | J-3 | False answers | **Correct** |
|---|---:|---:|---:|---:|
| no control | 80% | 76% | 12 | 78 |
| mechanical only | 72% | 78% | 11 | 75 |
| **model controller only, shipping** | **78%** | **82%** | **9** | **80** |
| both controls | 70% | 84% | 8 | 77 |
| NL-to-format, no control | 58% | 86% | 7 | 72 |
| NL-to-format, both controls | 48% | 90% | 5 | 69 |

**The conclusion is visible in every row:** J-3 is bought only with accuracy. The last row reaches the 90% target and is at the same time the worst configuration, losing half the correct answers. That is evidence that the problem sits **before** generation rather than after it.

### Final confirmation: full run, 16.08.2026, 21:43

The shipping configuration, 100 cases, **without shadow mode**, so the controller really does reject. This is the report the gates rest on.

| Measure | Shadow predicted | **Real measurement** |
|---|---:|---:|
| Accuracy | 78% | **80.0%** |
| J-3, correct refusal | 82% | **82.0%** |
| False answers | 9 | **9** |
| Retrieval recall | | 96.0% |
| False refusals | | 4 |
| Wrong answers | | 6 |

**J-3 and the count of false answers matched exactly.** The shadow method, computing both arms in one run, is therefore trustworthy and can be the basis for further decisions without double runs.

Stage distribution: `{odpowiedz: 55, zakotwiczenie: 41, kontrola: 4}`. Four cases were stopped by the controller, two of them rightly, and two cost a correct answer. That is exactly the trade chosen deliberately.

**All quality gates green**, with the warning about the unmet J-3 target (90%), which appears on every run that falls short of it.

### Intermediate confirmation (60 cases)

Shadow mode is a counterfactual computation, so the shipping configuration was checked in a separate run **with the controller genuinely enabled**. Comparison on **identical 60 cases** (a subset of the 100 above):

| | Accuracy | J-3 | False | Correct |
|---|---:|---:|---:|---:|
| no control | 73.3% | 70.0% | 9 | 43 |
| **controller, real measurement** | 70.0% | **76.7%** | **7** | **44** |

The controller gives up one hit and gains two justified refusals. **The direction matches the shadow prediction, so the choice is confirmed.**

> The same code gives 80% accuracy on the full 100 cases and 73.3% on this 60-case subset. **Seven points of difference come from question selection alone.** That is why gate thresholds are now assessed only on the full set (`MIN_PRZYPADKOW = 100`); comparing a subset result against a threshold calibrated on the whole produces a false alarm.

## 3. The road these numbers travelled

| Date | Change | Accuracy | J-3 |
|---|---|---:|---:|
| 14.08 | starting point | 76% | 66% |
| 15.08 | language fixes (stopwords, model per language) | 82% | 76% |
| 16.08 | discriminator extractor fixed | 80% | 76% |
| 16.08 | model controller added | 78% | **82%** |

**Fixing the discriminator extractor** was the single largest quality improvement, even though it barely shows in the accuracy column. The `_OKRES_PL` pattern read "13 January 2025 **roku**" as a duration of 2,025 years, creating a hard requirement that could not be met. The result was **2,585 false discriminators** in case 3 alone, and after the fix harmful citation rejections fell from **14 to 1**.

## 4. What the system does not achieve

This section matters as much as the three above it.

| Item | State | Target |
|---|---|---|
| **J-3, correct refusal** | **82%** (confirmed) | **90%**, not reached (RY-16) |
| False answers | **9** out of 50 questions without coverage | 0 |
| Accuracy | **80%** (confirmed) | higher |
| Gap between recall and accuracy | 96% against 80% | 16 points to recover |

**The 16-point gap is the most interesting open item.** The sentence containing the answer REACHES the model in 96 cases out of 100, and yet in 16 of them the model points at a different one. That is not a retrieval problem; it is a selection problem.

**The remedy for J-3 (J2.2, not implemented):** judging answerability before the model starts answering. The basis is *Sufficient Context* (ICLR 2025): retrieval augmentation paradoxically LOWERS the tendency to refuse, because the added context raises the model's confidence.

### Hypotheses tested and rejected

Recorded so that nobody tries them a second time without reason:

| Hypothesis | Measurement result |
|---|---|
| NL-to-format (arXiv 2408.02442) will raise accuracy | **Rejected.** 58% against 80%; 17 cases with no sentence indicated at all. It loses the conversion step, not the generation step. |
| Overeager English period matching spoils the result | **Rejected.** Periods are ten times rarer in English than in Polish; the culprit was the POLISH pattern. |
| The model controller does nothing | **Rejected.** It only looked that way because the broken extractor flooded the mechanical layer with false rejections. |
| The context size (8192) limits quality | **Rejected.** Llama 3.1 8B scores 94.6% on RULER at 16K, so we work well inside the strong zone. |

### Paths not explored

- **q6_k instead of q4_k_m.** The model's publisher warns plainly that quantised models show reduced response quality and possible hallucinations. We run q4, the most aggressive of the four available.
- **Bielik-11B instead of Minitron-7B.** Our model is a pruned version of the 11B and recovers around 90% of the base quality. The 11B sits downloaded and unused.
- **Extending the reference set.** With six questions, measure J-2 remains unmeasurable.

## 5. How to repeat the measurement

```bash
# full measurement, the only one the gates assess (100 cases)
python -m eval.benchmark.przebieg2 --sprawa 3 --sprawa 4 --par 25
```

```bash
# quick diagnostic, ignored by the gates, around 25 min
python -m eval.benchmark.przebieg2 --sprawa 3 --sprawa 4 --par 8
```

```bash
# both control arms in one run
python -m eval.benchmark.przebieg2 --sprawa 3 --sprawa 4 --par 25 --cien
```

Hardware: 8 GB VRAM, Ollama with `NUM_PARALLEL=1`. Models: `bielik-lex-map` (Bielik-Minitron-7B-v3.0, Q4_K_M) for Polish, `llama-lex-map` (Llama 3.1 8B, Q4_K_M) for English.

**Machine load affects the timing result, not the quality result.** On 16.08.2026 one case took 10.4 hours because other processes were occupying the machine, which is why `BUDZET_ESKALACJI_S = 900` exists.
