# The case panel

```bash
python panel/serwer.py
```

Address: **http://127.0.0.1:8713**, with two views: cases and legal provisions.

## Deep analysis: a multi-stage pipeline

The first version of the panel pushed the whole case into one request and returned a single sentence with a citation. That was a search box rather than an analysis, and with more documents it did not fit in the context at all.

The current run:

```
  1. DECOMPOSITION   the model breaks the question into 2 to 4 analytical threads
  2. DOCUMENT PICK   BM25 indicates which documents are worth reading at all
  3. MAPPING         a separate call FOR EACH relevant document,
                     extracting facts with citations
  4. PROVISIONS      retrieval over the corpus of legal provisions
                     (a separate space)
  5. SYNTHESIS       conclusions, discrepancies, gaps, legal basis
  6. VERIFICATION    mechanical check of every citation against the source
```

The result contains: **findings** (numbered, with citations), **conclusions** (indicating which findings they follow from), **discrepancies**, **gaps in the file**, the **legal basis**, and the statements that were **rejected**.

### Anchoring the conclusions

A finding of fact **must** carry a verified citation. A conclusion has no citation, because it is reasoning rather than a fact. Instead it points at the **numbers of the findings** it follows from.

A conclusion resting on a finding that failed verification is rejected along with it. The reasoning becomes traceable down to a sentence in the file, which partly closes the limitation stated openly in ADR-0006: verifying a citation does not confirm that the conclusion is sound.

## Scaling to a hundred documents

**The number of model calls does not grow with the size of the file.** BM25 picks up to 12 of the most relevant documents (`MAKS_DOKUMENTOW_DO_ANALIZY`), so a case of 100 documents costs the same as a case of 15; the rest are skipped as irrelevant, and the panel shows how many.

The mechanics: documents are split into fragments of around 1,400 characters with an overlap, **preserving offsets into the original**. BM25 ranking handles Polish inflection. Only relevant fragments reach the model, within the context budget.

The offsets are a condition of correctness here: the verifier compares a character range against the content of the **source** document. If fragments had their own numbering, every citation would point into the void.

### Real measurement (development profile, Q4, 8 GB VRAM)

| Scope | Time |
|---|---|
| 2 documents (decomposition, 2 mappings, synthesis) | **545 s** |
| Estimated for a full 12 documents | 15 to 25 minutes |

This is slow and will stay slow on this hardware, because one model call takes 40 to 90 seconds. The production profile (Q8, a 24 to 48 GB GPU) shortens it several times over. The panel shows progress stage by stage, so it is visible which document the work is on.

## Legal provisions: a separate view, a separate citation space

Provisions **belong to no case**. They are public and shared, so keeping them together with case files would mix privileged material with the text of the statute book.

The more important reason is **separating the citation spaces**. A finding of fact cites the case file; a legal basis cites a provision. If both lived in one collection, the model could "confirm" a statement about the law with a record of examination, and the verifier would let it through, because the citation would formally exist in the collection.

The findings verifier cannot see the provisions; the legal basis verifier cannot see the case file. The mix-up is structurally impossible rather than "not allowed".

**The firm enters the text of provisions from an official source.** The system deliberately contains no statutory text: a tool built to fight hallucination cannot start from provisions reconstructed out of a model's memory. The `zrodlo` and `zweryfikowal` fields record the provenance, and a provision without verification is marked as such in the interface.

## Scope confined to a single case

The condition set at the outset: documents and data go only into the selected case, and conversation memory is confined to it.

```
  case selected -> baza.tresci_dokumentow(sprawa_id [, dokument_id])
                       <- the ONLY entry point to case content in the panel
                 +-------------+-------------+
          context for the model      collection for the verifier
                 (the same narrowed dictionary)
```

Reinforcements in the data layer: no function returns documents or messages without a `sprawa_id`; `pobierz_dokument` requires the case to match, so a document from another case is indistinguishable from one that does not exist; `dodaj_dokument` rejects a non-existent case; a document thread is separate from a case thread.

**Verified against the live model** (two cases in one installation, questions asked inside "II K 147/26"):

| Question | Result |
|---|---|
| A fact present **only in the other case** (an admission) | refused, as required |
| A registration number, **only in the other case** | refused, as required |
| A fact from this case | answered, with citations |

The proof in code: `tests/test_panel_izolacja_spraw.py` (13 tests).

## Two traps that cost this pipeline dearly

Worth recording, because both produced a **silent zero** instead of an error.

**1. The mapping stage must not answer the question.** The first template said "list the findings relevant to the question", and the question was "are the witness statements consistent?". The model was given one record of examination and correctly returned an empty list, because a single statement says nothing about consistency *between* witnesses. The analysis ended with zero findings on documents full of facts.

Mapping is there to **extract facts**. Comparison belongs to synthesis, which sees every document at once. After rewording, the same two records yielded **11 findings** instead of none.

**2. The model writes in Polish.** The template asked for the key `"watki"` and the model returned `"wątki"`. A rigid read produced an empty list with no trace of an error. Parsing now normalises key names (diacritics stripped, casefolded, spaces and hyphens turned into underscores) and accepts variant field names.

Related: **NFD does not decompose the letter `ł`**, because it is a separate letter rather than an `l` with a diacritic. Without an explicit substitution, half of Polish verb forms landed on different stems. Tests: `tests/test_analiza_parsowanie.py`, `tests/test_wyszukiwarka.py`.

## What the panel still does not have

| Missing | Consequence |
|---|---|
| **Login and accounts** | It listens on `127.0.0.1` only. Exposing it on the LAN needs a reverse proxy with TLS from our own CA, and authentication |
| OCR and file upload | Content is pasted as text; OCR arrives with the full stack (Docling and Tesseract) |
| Vector search | BM25 is in place; the hook for a hybrid is prepared (`polacz_rankingi`, RRF), per ADR-0004 |
| Ethical walls | The data model provides for them; enforcement needs the accounts layer |
| A separate key for defence material | The marking is visible, but a separate store and key belong to Phase 5 (requirement T-1) |
| The deadline engine in the interface | Implemented and tested, not yet wired into the panel |

**The panel runs on the development profile.** The conditions for admitting real case files are unchanged; see [`compliance/gdpr-dpia.md`](compliance/gdpr-dpia.md).

## Programming interface

| Method | Path | Action |
|---|---|---|
| GET, POST | `/api/sprawy` | List cases, create a case |
| GET, POST | `/api/sprawy/{id}/dokumenty` | Case documents, add one |
| GET, DELETE | `/api/sprawy/{id}/dokumenty/{did}` | Content, deletion (the case must match) |
| **POST** | **`/api/sprawy/{id}/analiza`** | **Starts an analysis, returns `zadanie_id` (202)** |
| **GET** | **`/api/zadania/{zadanie_id}`** | **Progress: stage, done out of total, result** |
| GET, POST | `/api/czat`, `/api/sprawy/{id}/czat` | Thread history, a quick question |
| GET, POST, DELETE | `/api/przepisy[/{id}]` | The corpus of provisions |
| GET | `/api/audyt` | Entries and the state of the checksum chain |

Analysis is a **background task**: the POST returns immediately and the panel polls for progress. Previously the request was synchronous and the button went dead for a minute with no information, so work was indistinguishable from a hang.

## Dependencies

**The Python standard library only.** BM25 and tokenisation are written from scratch, so no new packages enter the supply chain (art. 21(2)(d) of the Polish KSC act). It requires Ollama with the `bielik-lex-dev` model.
