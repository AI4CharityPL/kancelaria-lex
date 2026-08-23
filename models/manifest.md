# Model manifest

This directory holds **manifests, checksums and licences**, not the weights themselves. The weights are excluded from the repository (`.gitignore`) and brought in as an offline package.

## The code licence is not the weights licence

MIT for OpenContracts says nothing about the language model. **Every model update requires the weights licence to be verified again.**

The case that makes this concrete: **Surya**, with Apache 2.0 code but weights under AI Pubs Open-RAIL-M, which restricts commercial use above a revenue threshold. For a commercial law firm that would require a separate licence. A repository's licence is not enough to judge by.

## Language models in production

> **Corrected 17.08.2026.** This section previously listed only Bielik-11B, described as "the" language model of the system. **The system does not use it.** The ablation of 14.08.2026 rejected the 11B in the extraction role (8 errors in 99.0 s against 6 in 35.1 s for the minitron), and since model selection by document language was introduced (`panel/jezyk.py`) production has run on **two** models rather than one. A manifest describing an unused model is worse than no manifest: it leads directly to installing something other than what was measured.

Versions are pinned by digest in [`../QUICKSTART.md`](../QUICKSTART.md), step 3.

| Role | Working model | Base | Base digest | Weights licence |
|---|---|---|---|---|
| **Polish** documents | `bielik-lex-map` | `SpeakLeash/bielik-minitron-7B-v3.0-instruct:Q4_K_M` | `6660954d0758` | Apache 2.0 |
| **English** documents | `llama-lex-map` | `llama3.1:8b-instruct-q4_K_M` | `46e0c10c039e` | Llama 3.1 Community License |

| Field | Value |
|---|---|
| Authors | SpeakLeash and ACK Cyfronet AGH (Bielik), Meta (Llama 3.1) |
| Licence verified | 17.08.2026 |
| Context | `num_ctx 8192`, measured rather than default |
| Seed | `seed 42`, for repeatable runs |
| VRAM footprint | 5.2 GB, entirely on the GPU (measured 17.08.2026) |

> **The Llama licence is not Apache.** The Llama 3.1 Community License carries conditions that Apache 2.0 does not, among them a threshold of 700 million monthly active users and a requirement to state "Built with Llama". For a law firm that has no practical effect, but **it is not a free licence**, and it has to be checked afresh on every model change, exactly as with Surya above.

**Warning from the model card:** quantised models show reduced answer quality and a tendency to hallucinate. The published results (80.0% accuracy, 82.0% correct refusal) **already include that cost**, because they were measured on Q4_K_M rather than on full-precision weights.

### A rejected model, kept only for development

| Field | Value |
|---|---|
| Name | Bielik-11B-v3.0-Instruct (`bielik-lex-dev`) |
| Source | `SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M`, around 6.7 GB |
| Weights licence | Apache 2.0 (verified 14.08.2026) |
| Status | **not used in production**; `models/Modelfile.bielik-dev` stays so the ablation can be repeated |

The setup guide **deliberately does not build it**: it costs 6.7 GB of download and 1.5 GB of VRAM beyond the budget of an 8 GB card, and gives nothing in return.

## Embedder: `intfloat/multilingual-e5-base`

| Field | Value |
|---|---|
| Dimensions | **768**, within the supported set, so no change to the pgvector schema |
| Why chosen | In place of the default `all-MiniLM-L6-v2` (384 dimensions, English corpus); see ADR-0004 |
| Execution | CPU, so it does not compete with the language model for VRAM |
| Weights licence | MIT (intfloat) |

The weights are brought in as an **offline package** into `models/e5-base/` and mounted into the container read-only. The service does not fetch them itself; without the weights it does not start (see `src/aplikacje/embedder/README.md`).

Reasoning for the choice: [`../docs/adr/0004-embedder-multilingual-e5.md`](../docs/adr/0004-embedder-multilingual-e5.md).

### Checksums (downloaded 16.08.2026)

```
9dab198f24c8c0879e481cf7822005d5ecbceedbacb390ffafa594e28d31bac4  config.json
62c24cdc13d4c9952d63718d6c9fa4c287974249e16b7ade6d5a85e7bbb75626  tokenizer.json
efb5c0d09722e5fe59a462cd2a9976ee216d55b037597d997cd3fe833216da15  tokenizer_config.json
06e405a36dfe4b9604f484f6a1e619af1a7f7d09e34a8555eb0b77b66318067f  special_tokens_map.json
cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865  sentencepiece.bpe.model
a18a44fad1d0b46ded15928144138cff1135d5cc8233bdd90be5f18822de09a7  model.safetensors
```

The weight files themselves are excluded from the repository (`.gitignore`), because they come to 1.1 GB.

## OCR language data (Tesseract)

The `models/tessdata/` directory. The files **are not versioned**; they are downloaded once and checked by checksum. `TESSDATA_PREFIX` points at this directory, so installation needs no administrator rights.

| File | Size | sha256 | Source |
|---|---:|---|---|
| `pol.traineddata` | 11.4 MB | `e80cc4cefbdface06e9223f43f089556b9dcf104020fbc0a200f6863c57d4405` | `tesseract-ocr/tessdata_best` |
| `eng.traineddata` | 3.9 MB | `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2` | Tesseract 5.4.0 installation |
| `osd.traineddata` | 10.1 MB | `9cf5d576fcc47564f11265841e5ca839001e7e6f38ff7f7aacf46d15a96b00ff` | Tesseract 5.4.0 installation |

**Polish is required and English is not a substitute.** Recognising a Polish document with the English engine returns text with no diacritics; see [`../docs/document-loading-and-ocr.md`](../docs/document-loading-and-ocr.md).

## OCR engines

| Engine | Licence | Role |
|---|---|---|
| Tesseract 5.x with `pol.traineddata` | Apache 2.0 | default |
| RapidOCR | Apache 2.0 | fallback for poor photocopies |
| ~~Surya~~ | Open-RAIL-M weights | **to be avoided**, commercial threshold |

## Procedure for introducing a model

1. Download in a zone with network access.
2. **Verify the weights licence**, not the repository licence.
3. Compute the checksum.
4. Record it in this manifest: checksum, licence, date verified, person.
5. Transfer as an offline package; see [`../docs/operations/offline-updates.md`](../docs/operations/offline-updates.md).
6. Verify the checksum on the target side.
7. Verify at every startup (isolation layer B, threat T-3).

## Changing a model

**Newer does not mean better for Polish case files.** Every model change requires:

- passing the **full quality gates** (J-1 to J-8) again on the production profile,
- verifying the weights licence again,
- an entry in the changelog.

## History

| Date | Model | Version | Quantisation | Person |
|---|---|---|---|---|
| 14.08.2026 | Bielik | 11B-v3.0-Instruct | Q4_K_M | downloaded for the proof of concept |
| 16.08.2026 | multilingual-e5-base | intfloat, 768 dimensions | FP32 (CPU) | offline package for the embedder |
| 17.08.2026 | Bielik-minitron-7B, Llama 3.1 8B | production pair | Q4_K_M | digests recorded, 11B moved to development only |
