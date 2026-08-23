# The local AI stack

## The principle

Everything runs locally: the language model, the embeddings, the OCR. Weights are downloaded **once**, in a controlled window, verified by checksum and carried into the closed zone. During operation the system downloads nothing.

## The language model

**Bielik-11B-v3.0-Instruct** (SpeakLeash and ACK Cyfronet AGH, January 2026, weights under Apache 2.0), run through Ollama.

Why this one: a good fit for Polish legal terminology and syntax, a fully open commercial licence on the weights, availability in the Ollama library in GGUF format, and institutional backing (PLGrid, ACK Cyfronet). Alternatives and rejected options: [`adr/0002-language-model-bielik.md`](adr/0002-language-model-bielik.md).

### Quantisation and trustworthiness

The model card carries an explicit warning that **quantised models show reduced answer quality and a greater tendency to hallucinate**.

That warning weighs more here than in a typical application. A hallucination in the analysis of a criminal case file is not an inconvenience; it is a potential error in someone's defence.

| Profile | Quantisation | Model VRAM | Context | Data permitted |
|---|---|---|---|---|
| **Development** (this laptop, 8 GB) | Q4_K_M | around 6.7 GB | around 8k | **synthetic corpus only** |
| **Production, minimum** (24 GB) | Q8_0 | around 12 GB | 32k | real case files, after the gates |
| **Production, recommended** (48 GB) | FP16 | around 22 GB | 32k and above, with concurrency | real case files |

**A hard rule: the development profile never touches real case files.** Not because of isolation, which works the same either way, but because Q4 on 8 GB of VRAM does not give quality that can responsibly be applied to a criminal case.

### Configuring the development profile

The Quadro RTX 4000 Max-Q has 8 GB of VRAM. Bielik Q4_K_M occupies around 6.7 GB, leaving roughly 1 GB for the KV cache, so the real context is about 8k tokens.

With 64 GB of RAM there is an alternative: offloading some layers to the CPU raises the context at the cost of speed. The parameters live in `models/Modelfile.bielik-dev`; measuring the throughput of both variants belongs to Phase 3.

The practical consequence is that at an 8k context retrieval has to be frugal: a few precise fragments rather than whole documents. That happens to reinforce the citation requirement.

## Embeddings

**`multilingual-e5-base`**, 768 dimensions, in place of the default `all-MiniLM-L6-v2` (384 dimensions, English corpus, finding U-7).

The reasons:
- retrieval on Polish procedural documents is the system's foundational operation, and choosing an English-language model ruins everything above it,
- 768 falls within the supported set of dimensions, so it **needs no work on the pgvector schema**,
- it runs on the CPU at acceptable speed and does not compete with the language model for VRAM.

`bge-m3` (1024 dimensions, longer context) was considered and deferred, because it would require schema changes. Worth revisiting once retrieval quality has been measured. Recorded in [`adr/0004-embedder-multilingual-e5.md`](adr/0004-embedder-multilingual-e5.md).

**Search is hybrid**, combining vector and full-text. Vector search loses case references and figures; full-text search loses paraphrase. Procedural documents contain both kinds of query.

## OCR

OpenContracts has no OCR of its own. PDF parsing is directed by **Docling**, which acts as an orchestrator, while text recognition is done by whichever engine is attached.

| Engine | Licence | Role | Reasoning |
|---|---|---|---|
| **Tesseract 5.x with `pol.traineddata`** | Apache 2.0 | default | Mature, light (around 10 MB), no GPU needed, a good Polish pack, under a second per page |
| **RapidOCR** | Apache 2.0 | fallback | ONNX with PP-OCR underneath; better on poor photocopies and unusual layouts, still without a GPU |
| PaddleOCR and PaddleOCR-VL | Apache 2.0 | last resort | The highest accuracy, but computationally expensive; for individual difficult cases |
| EasyOCR | Apache 2.0 | alternative | Supported natively by Docling |
| ~~Surya~~ | Apache 2.0 code, **Open-RAIL-M weights** | **to be avoided** | The weights licence restricts commercial use above a revenue threshold, so a commercial firm would need a separate licence |

Every engine chosen runs fully locally, with no network call.

### The OCR quality gate

OCR is the **first** link in the chain, so an error here propagates into the embeddings, the retrieval and the agent's answer. Hence:

- the character error rate is measured on a sample stratified by scan quality (gates N-14 and N-15),
- documents above the error threshold go into a manual review queue rather than into the index,
- the lawyer can inspect and correct the OCR output before indexing (F-03).

Realistically, local OCR performs worse than commercial cloud services on photocopies and handwriting. That is the price of confidentiality and we accept it, on condition that quality is **measured** rather than assumed.

## Format conversion

Formats other than PDF, DOCX and TXT (legacy `.doc`, ODF, images, HTML and more than 120 others) go through **Gotenberg** (LibreOffice).

**Gotenberg has to sit in an `internal` segment.** LibreOffice can try to fetch resources embedded in files, such as linked images or XML entities. With a letter from the opposing party that becomes a read receipt at an address they control (threat I-2). Application-level control is unreliable here; only the absence of a network route works.

## Managing the weights

The `models/` directory holds **manifests and checksums**, not the weights themselves.

For each model:
- name, version, quantisation, source,
- the checksum of the weights,
- **the weights licence** together with the date it was verified,
- the date it entered the closed zone and the person responsible.

**The code licence is not the weights licence.** MIT for OpenContracts says nothing about Bielik. Every model update requires the licence to be verified again; the Surya case (Apache 2.0 code, Open-RAIL-M weights with a commercial threshold) shows this is not a formality.

Checksums are verified at startup (isolation layer B, threat T-3).

## What we deliberately do not do

| Rejected | Reason |
|---|---|
| Fine-tuning the model on the firm's case files | Risk of fixing personal data in the weights; the GDPR and professional privilege. Retrieval gives a similar effect without that risk. |
| A cloud model "only for non-sensitive tasks" | There is no way to guarantee lastingly that non-sensitive data contains nothing sensitive. The boundary would be fiction. |
| A reranker as an external model | The same principle: everything local or not at all. |
| Downloading models automatically during operation | That would be an outbound connection. Weights arrive only as an offline package. |
