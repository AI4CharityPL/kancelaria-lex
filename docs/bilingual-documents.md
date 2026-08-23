# Bilingual documents: language detection and engine selection

Every uploaded document has its language detected automatically, and the mapping stage is routed to the model appropriate for that language.

## Why language detection is not done by the model

Telling Polish from English is a settled, deterministic task. A model would cost seconds per document (at 400 documents, a quarter of an hour), occupy VRAM and still be uncertain. Counting function words and diacritics answers in microseconds, always identically, with no GPU.

It is the same principle as with procedural deadlines (ADR-0005): **where a rule suffices, the model is the worse tool.**

For borderline cases (a very short document, a mixed one, one that is purely tabular) the result is `nieznany` with a stated confidence, and the decision is taken a layer up. The fallback is Polish, because the installation is Polish.

The signals are the diacritics `ąćęłńóśźż` (their presence is close to decisive, their absence proves nothing, because scans lose the tails after OCR) together with the frequency of function words and procedural terms in both languages.

### Accuracy on real case material

| Corpus | Documents | Detection | Mean confidence |
|---|---|---|---|
| USA v. Lacey (PDF, English) | 402 | **397 en**, 4 pl, 1 unknown | 0.87 |
| SAOS judgments (Polish) | 320 | **320 pl** | 0.99 |
| Synthetic corpus | 3 | 3 pl | 0.99 |

That is 98.8% on English and 100% on Polish. The language is detected **once, on upload**, and stored in the database; it is not recomputed for every analysis.

## Engine selection

| Language | Model | Reasoning |
|---|---|---|
| Polish | `bielik-lex-map` (Bielik-minitron-7B Q4) | Trained for Polish; 38 tokens per second, fits entirely in VRAM |
| English | `llama-lex-map` (Llama 3.1 8B Q4) | Reported in market reviews as the most reliable where a strict JSON schema is required; good on legal terminology |

Documents are **grouped by language before mapping**. That is not cosmetic: with 8 GB of VRAM only one model fits at a time, so every change of language means unloading one and loading the other. Grouping reduces that to a single swap instead of a dozen.

The prompt template is chosen by language as well, so an English document gets an English instruction.

## What was actually breaking citations from PDFs

The first diagnosis was "the Polish model paraphrases English text". It was **incomplete**.

Every rejection carried the reason `zakres 0-0`, meaning the fragment **was not found at all** in the source. The cause was in our own code: offsets were determined by a plain `zrodlo.find(fragment)`, that is, an exact string match.

Text extracted from a PDF looks like this:

```
Attorney for Defendant: Paul Cambria, \nRetained \nDefendant: [x] Present [ ] Not Present
```

Line breaks in mid-sentence, page layout characters. The model quotes the sentence as it reads it, `find()` did not locate the exact string, and **a correct citation was lost**.

The verifier had whitespace tolerance from the start. It never got the chance to use it, because the filtering happened one step earlier.

**The fix:** `znajdz_fragment()` searches with the same normalisation the verifier uses and maps the positions back onto the original, so the citation points at a real place in the document rather than in a processed copy. The tolerance limits were left alone: a changed figure, a removed negation or a paraphrase still fails (`tests/test_znajdz_fragment.py`).

## Results: the contribution of each fix

The USA v. Lacey file, 402 documents from PDFs, the same question:

| Configuration | Findings | Rejected | Accuracy |
|---|---|---|---|
| Bielik (Polish) with exact `find()` | 6 | 62 | 9% |
| Llama (English) with exact `find()` | 14 | 133 | 10% |
| **Llama with tolerant search** | **111** | **38** | **74%** |

The Polish corpus, 320 judgments (clean text from an API rather than from PDFs):

| Configuration | Findings | Rejected | Accuracy |
|---|---|---|---|
| Bielik with exact `find()` | 28 | 6 | 82% |
| Bielik with tolerant search | 29 | 7 | 81% |

**Interpretation.** Polish did not move, because it comes from clean text and had nothing to fix. English rose eightfold, because it comes from PDFs. The main cause was therefore **how the text was extracted, not the language**, although the choice of model helped too (6 findings became 14 even before the search was fixed).

The lesson for next time: when judging a model's quality, first rule out that the problem lies in data preparation. Otherwise you replace the model when it is the parser that is failing.

## Timings

| Corpus | Documents | Analysis time |
|---|---|---|
| Polish (SAOS) | 320 | 261 s |
| English (Lacey) | 402 | 414 s |

Llama 3.1 8B is slower than Bielik-minitron (a larger model, a tighter fit in VRAM), hence the longer time for a comparable number of documents.

## Configuration

`panel/jezyk.py` holds the `MODELE` dictionary; `panel/analiza.py` holds `MODEL_SYNTEZY`.

Modelfiles: `models/Modelfile.bielik-map`, `models/Modelfile.llama-map`.

```bash
ollama create bielik-lex-map -f models/Modelfile.bielik-map
```

```bash
ollama create llama-lex-map -f models/Modelfile.llama-map
```
