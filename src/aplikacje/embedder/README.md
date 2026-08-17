# Embedder — `multilingual-e5-base`

Usługa embeddingów dla wyszukiwania w aktach. 768 wymiarów, CPU,
segment `net_ai` bez trasy do internetu.

Uzasadnienie wyboru modelu: [`docs/14-decyzje/ADR-0004-embedder.md`](../../../docs/14-decyzje/ADR-0004-embedder.md).

---

## Dlaczego ta usługa nie pobiera modelu sama

`transformers` przy nieznalezionym modelu domyślnie **dociąga go
z internetu**. W systemie przetwarzającym akta objęte tajemnicą
zawodową byłoby to wyjście na zewnątrz — ciche, bo wyglądające jak
poprawny start usługi.

Trzy niezależne warstwy pilnują, żeby do tego nie doszło:

| Warstwa | Mechanizm |
|---|---|
| Biblioteka | `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` w obrazie |
| Aplikacja | `_sprawdz_wagi()` przerywa start **przed** importem `transformers` |
| Sieć | segment `net_ai` ma `internal: true` — brak trasy do bramy |

**Brak wag = brak startu.** Usługa nie wstaje „w trybie ograniczonym"
i nie zwraca wektorów zerowych: embedder zwracający zera wygląda na
działający, a retrieval przestaje działać w ciszy.

---

## Przygotowanie paczki offline z wagami

Wykonywane **raz**, w strefie przygotowawczej z dostępem do sieci —
nigdy na maszynie, na której leżą akta.

```bash
# 1. Pobranie wag (maszyna z internetem)
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

# 2. Suma kontrolna — do wpisania w models/manifest.md
find e5-base -type f -exec sha256sum {} \; | sort

# 3. Przeniesienie na maszynę docelową do models/e5-base/
```

Katalog `models/e5-base/` jest montowany do kontenera **tylko do
odczytu** (`:ro` w `compose.yml`).

⚠️ **Licencja kodu nie jest licencją wag.** Każda zmiana modelu wymaga
ponownego sprawdzenia warunków licencyjnych i wpisu w
[`models/manifest.md`](../../../models/manifest.md).

---

## API

Kształt zgodny z OpenAI — klient forka rozmawia tym protokołem także
z Ollamą (ustalenie U-1), więc jeden klient obsługuje oba adresy
z allowlisty `LEX_DOZWOLONE_BASE_URL`.

### `POST /v1/embeddings`

```json
{ "input": ["treść fragmentu"], "typ": "passage" }
```

| Pole | Znaczenie |
|---|---|
| `input` | tekst albo lista tekstów (najwyżej 128) |
| `typ` | **obowiązkowe, bez wartości domyślnej**: `query` dla pytania, `passage` dla fragmentu akt |

Odpowiedź:

```json
{ "object": "list", "model": "intfloat/multilingual-e5-base",
  "data": [{ "object": "embedding", "index": 0, "embedding": [ ... 768 ... ] }] }
```

### ⚠️ Pole `typ` nie jest opcjonalne bez powodu

Rodzina E5 była trenowana z prefiksami `query:` i `passage:`. Ich
pominięcie **nie daje błędu** — daje cicho gorszy retrieval, czyli
usterkę widoczną dopiero jako spadek trafności o kilka punktów, bez
żadnego komunikatu. Dlatego pole jest jawne i walidowane, a wartość
spoza zbioru kończy się odpowiedzią 400.

### `GET /zdrowie`

```json
{ "stan": "gotowy", "model": "...", "wymiary": 768, "zrodlo_wag": "/modele/e5-base" }
```

---

## Uruchomienie samodzielne (diagnostyka)

```bash
docker build -t kancelaria-lex-embedder src/aplikacje/embedder
docker run --rm -p 8000:8000 \
    -v "$(pwd)/models/e5-base:/modele/e5-base:ro" \
    kancelaria-lex-embedder
```

Bez zamontowanych wag kontener zakończy się kodem 2 i komunikatem
wskazującym ten plik — i tak ma być.
