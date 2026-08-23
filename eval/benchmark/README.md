# The kancelaria-lex benchmark

**A bilingual quantitative measurement of citation fidelity and refusal, with no LLM judge.**

Bilingual here refers to the *corpora*, Polish and English. The benchmark itself, like the rest of the documentation, is described in English.

## The problem the market has and cannot measure

Stanford RegLab examined the leading commercial legal research tools. The result, later published in the *Journal of Empirical Legal Studies*:

| Tool | Hallucinations |
|---|---:|
| Lexis+ AI | **over 17%** |
| Westlaw AI-Assisted Research | **over 34%** |

At the time, LexisNexis advertised "100% hallucination-free linked legal citations", and Thomson Reuters said its tools "avoid hallucinations by relying on trusted content". The study showed both claims to be overstated.

An independent review from 2026, grading 3,000 answers, produced a figure that says even more: **24% of answers cited or applied a provision that did not support the claim**. That is not a model getting a fact wrong. The model gave a citation that does not say what it was said to say.

**This is exactly the class of error that neither an LLM judge nor expert grading of 150 questions will catch.** Character-level comparison against the source does catch it, mechanically, across thousands of cases.

## The gap

| Benchmark | Scope | Grading method | Polish |
|---|---|---|:--:|
| LegalBench-RAG | retrieval in case files (EN) | human annotation | no |
| LRAGE | end-to-end RAG evaluation (EN, KO, ZH) | **an LLM judge** | no |
| LexGLUE | legal classification (EN, EU) | labels | no |
| Harvey LAB | 1,200 agentic tasks across 24 areas | 75,000 expert criteria | no |
| Multi-Legal-Bench | 6 jurisdictions, Poland among them | registry metadata | partly |
| LEPISZCZE and LLMzSzŁ | general NLP and examinations | labels | yes |

**No benchmark measures citation fidelity over Polish case files.** Multi-Legal-Bench covers Poland, but in classification tasks (type of court, form of ruling) rather than in questions about a case file with a citation. That is the gap this fills.

## Why no LLM judge

Because a grading model shares the weaknesses of the model it grades, and is lenient exactly where the risk is greatest, namely with a confidently phrased answer (ADR-0006).

The position has independent support in the **Polish legal setting**: a peer-reviewed paper in *Artificial Intelligence and Law* (Springer, 2026), built on the qualification examination for the Polish National Appeal Chamber, is titled outright *"LLM-as-a-Judge is Bad"*.

It is worth noting that LRAGE, currently the leading tool for evaluating legal RAG, scores with a rubric-based LLM judge. This benchmark deliberately goes the other way.

## The method

### Matched pairs

Every answerable case has a **twin identical in form**, differing only in the value of the anchor:

```
A.  "What does the amount of 12,500 zloty in this case file relate to?"   the amount IS there
B.  "What does the amount of 12,840 zloty in this case file relate to?"   the amount is NOT there
```

The sentence containing 12,500 zloty is known to the character, so the ground truth is produced without human involvement. The amount in the twin was checked by exhaustive search across the whole file and does not occur, so the only correct answer is a refusal.

**The twin has to be plausible.** The first version of the generator produced "16 April 7029", and a case like that measures the reaction to an absurd year rather than whether the file was checked. The shifts therefore depend on the type: in dates the day and month change and the year stays; in amounts the order of magnitude is preserved.

### The headline measure: pair discriminability

A pair counts **only** when the system cited the correct fragment in the answerable case **and** refused in the twin.

| Behaviour | J-3 (correct refusal) | J-4 (false refusal) | **Pair discriminability** |
|---|---:|---:|---:|
| Always refuse | 100% | 100% | **0%** |
| Always answer | 0% | 0% | **0%** |
| Discriminates | high | low | **above 0%** |

Classical metrics can be gamed by degenerate behaviour and have to be read in pairs. This measure cannot be: both degenerations score zero. The two questions in a pair are identical in form, so the difference cannot be explained by difficulty. It is an ordinary controlled experiment, carried over into RAG evaluation.

> A result of 50% does **not** mean "half right". It means that in half the pairs the system behaved identically towards a question with an answer and one without, that is, in those pairs it did not check the file.

### What this buys in practice

- **It scales with the corpus rather than with a lawyer's time.** A gold set needing human verification grows to around 150 questions and stops there. This generator produces thousands of cases from the same files.
- **It does not replace the gold set.** It measures citation fidelity and refusal, not substantive correctness. Both measures are needed, for different things.
- **It is repeatable.** The random seed is recorded in the result, so the same run produces the same cases and a difference between releases is a difference in the system.

## Running it

```bash
python -m eval.benchmark.przebieg --sprawa 3 --sprawa 4 --par 25
```

| Parameter | Meaning |
|---|---|
| `--sprawa N` | a case id in the panel database; may be repeated |
| `--par N` | matched pairs per case |
| `--dokumenty N` | cap on the number of documents loaded |
| `--ziarno N` | random seed (default 42) |
| `--bez-szczelnosci` | skip the cross-case leakage test |

The result goes to `eval/wyniki/benchmark-<date>.{md,json}`: a report and the full data for further analysis.

## Case categories

| Category | Expectation | What it measures |
|---|---|---|
| `fakt_zakotwiczony` | a citation | citation fidelity, hitting the right range |
| `bez_pokrycia` | a refusal | resistance to invention (J-3) |
| `pulapka_liczbowa` | a refusal | sensitivity to a close but different value |
| `szczelnosc` | a refusal | **cross-case leakage, with a zero threshold** |

Leakage has a zero threshold rather than a percentage one. A single hit is a breach of professional privilege, not a dip in a metric.

## Data policy

The benchmark runs only on synthetic and public corpora (requirement T-6, `docs/compliance/legal-professional-privilege.md`). Cases 3 and 4 are public SAOS judgments and public US federal court records. **Real client files do not enter any evaluation run.**

## Sources

- Stanford RegLab, *Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools*: <https://reglab.stanford.edu/publications/hallucination-free-assessing-the-reliability-of-leading-ai-legal-research-tools/>
- *LLM-as-a-Judge is Bad*, Artificial Intelligence and Law (Springer, 2026): <https://link.springer.com/article/10.1007/s10506-026-09505-w>
- LegalBench-RAG: <https://www.semanticscholar.org/paper/3daedc1e0a9db8c4dda7e06724b0b556f64c0752>
- LRAGE: <https://arxiv.org/html/2504.01840>
- Multi-Legal-Bench: <https://arxiv.org/html/2605.29738v1>
- Harvey LAB: <https://github.com/harveyai/harvey-labs>
- LLMzSzŁ: <https://arxiv.org/abs/2501.02266>
