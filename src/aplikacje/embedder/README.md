# Embedder: `multilingual-e5-base`

The embedding service for searching case files. 768 dimensions, CPU, in the `net_ai` segment with no route to the internet.

Reasoning for the choice of model: [`docs/adr/0004-embedder-multilingual-e5.md`](../../../docs/adr/0004-embedder-multilingual-e5.md).

## Why this service does not fetch the model itself

When `transformers` does not find a model locally, it **downloads it from the internet** by default. In a system processing material covered by professional privilege that would be an exit outwards, and a quiet one, because it looks like a correct startup.

Three independent layers make sure that cannot happen:

| Layer | Mechanism |
|---|---|
| Library | `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` in the image |
| Application | `_sprawdz_wagi()` stops startup **before** `transformers` is imported |
| Network | the `net_ai` segment is `internal: true`, so there is no route to the gateway |

**No weights means no start.** The service does not come up "in reduced mode" and does not return zero vectors: an embedder returning zeros looks as if it works while retrieval stops working in silence.

## Preparing the offline weights package

Done **once**, in a preparation zone with network access, and never on the machine that holds case files.

```bash
# 1. Download the weights (machine with internet)
pip install "huggingface_hub==0.24.6"
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    "intfloat/multilingual-e5-base",
    local_dir="e5-base",
    allow_patterns=["config.json", "model.safetensors",
                    "tokenizer.json", "tokenizer_config.json",
                    "special_tokens_map.json", "sentencepiece.bpe.model"],
)
PY

# 2. Checksums, to be recorded in models/manifest.md
find e5-base -type f -exec sha256sum {} \; | sort

# 3. Move to the target machine, into models/e5-base/
```

The `models/e5-base/` directory is mounted into the container **read-only** (`:ro` in `compose.yml`).

**The code licence is not the weights licence.** Every model change requires the licence terms to be checked again and an entry made in [`models/manifest.md`](../../../models/manifest.md).

## API

The shape follows OpenAI, because the fork's client speaks that protocol to Ollama as well (finding U-1), so one client serves both addresses on the `LEX_DOZWOLONE_BASE_URL` allowlist.

### `POST /v1/embeddings`

```json
{ "input": ["fragment text"], "typ": "passage" }
```

| Field | Meaning |
|---|---|
| `input` | text or a list of texts (at most 128) |
| `typ` | **mandatory, with no default**: `query` for a question, `passage` for a fragment of a case file |

Response:

```json
{ "object": "list", "model": "intfloat/multilingual-e5-base",
  "data": [{ "object": "embedding", "index": 0, "embedding": [ "... 768 values ..." ] }] }
```

### The `typ` field is not optional, and for a reason

The E5 family was trained with the prefixes `query:` and `passage:`. Omitting them **produces no error**; it produces quietly worse retrieval, a defect that shows up only as a drop of a few points in accuracy, with no message at all. That is why the field is explicit and validated, and a value outside the set returns 400.

### `GET /zdrowie`

```json
{ "stan": "gotowy", "model": "...", "wymiary": 768, "zrodlo_wag": "/modele/e5-base" }
```

The field names in the response are Polish, like the rest of the application.

## Running it on its own (diagnostics)

```bash
docker build -t kancelaria-lex-embedder src/aplikacje/embedder
```

```bash
docker run --rm -p 8000:8000 \
    -v "$(pwd)/models/e5-base:/modele/e5-base:ro" \
    kancelaria-lex-embedder
```

Without the weights mounted, the container exits with code 2 and a message pointing at this file. That is the intended behaviour.
