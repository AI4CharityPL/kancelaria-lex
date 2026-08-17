# Manifest modeli

Ten katalog przechowuje **manifesty, sumy kontrolne i licencje** — nie same wagi.
Wagi są wyłączone z repozytorium (`.gitignore`) i wnoszone paczką offline.

## ⚠️ Licencja kodu nie jest licencją wag

MIT dla OpenContracts nie mówi nic o modelu językowym. **Każda aktualizacja modelu wymaga ponownej weryfikacji licencji wag.**

Przypadek, który to unaocznia: **Surya** — kod na Apache 2.0, ale wagi na AI Pubs Open-RAIL-M, która ogranicza użycie komercyjne po przekroczeniu progu przychodu. Dla kancelarii komercyjnej wymagałoby to odrębnej licencji. Sama licencja repozytorium nie wystarcza do oceny.

---

## Model językowy

| Pole | Wartość |
|---|---|
| Nazwa | Bielik-11B-v3.0-Instruct |
| Twórca | SpeakLeash + ACK Cyfronet AGH |
| Wydanie | styczeń 2026 |
| **Licencja wag** | **Apache 2.0** |
| Data weryfikacji licencji | 14.08.2026 |
| Źródło | biblioteka Ollama: `SpeakLeash/bielik-11b-v3.0-instruct` |
| Kwantyzacja (profil rozwojowy) | Q4_K_M, ~6,7 GB |
| Kwantyzacja (profil produkcyjny) | Q8_0 lub FP16 |
| Suma kontrolna | _do uzupełnienia po pobraniu_ |
| Wniesiony przez | _do uzupełnienia_ |
| Data wniesienia | _do uzupełnienia_ |

**Ostrzeżenie z karty modelu:** modele kwantyzowane wykazują obniżoną jakość odpowiedzi i podatność na halucynacje. Konsekwencja: Q4 wyłącznie do prac rozwojowych na korpusie syntetycznym.

## Embedder

| Pole | Wartość |
|---|---|
| Nazwa | multilingual-e5-base |
| Wymiary | **768** — mieści się we wspieranym zestawie, bez zmian w schemacie pgvector |
| Powód wyboru | Zamiast domyślnego `all-MiniLM-L6-v2` (384 wym., korpus angielski) — ADR-0004 |
| Uruchomienie | CPU, nie konkuruje o VRAM z modelem językowym |
| Suma kontrolna | _do uzupełnienia_ |

## OCR

| Silnik | Licencja | Rola |
|---|---|---|
| Tesseract 5.x + `pol.traineddata` | Apache 2.0 | domyślny |
| RapidOCR | Apache 2.0 | zapasowy — słabe kserokopie |
| ~~Surya~~ | wagi Open-RAIL-M | **do unikania** — limit komercyjny |

---

## Procedura wniesienia modelu

1. Pobranie w strefie z dostępem do sieci.
2. **Weryfikacja licencji wag** — nie licencji repozytorium.
3. Obliczenie sumy kontrolnej.
4. Wpis do tego manifestu: suma, licencja, data weryfikacji, osoba.
5. Przeniesienie paczką offline — [`../docs/10-operacje/runbook-aktualizacje.md`](../docs/10-operacje/runbook-aktualizacje.md).
6. Weryfikacja sumy po stronie docelowej.
7. Weryfikacja przy każdym starcie (warstwa B izolacji, zagrożenie T-3).

## Zmiana modelu

**Nowszy nie znaczy lepszy dla polskich akt.** Każda zmiana modelu wymaga:

- ponownego przejścia **pełnych bramek jakościowych** (J-1…J-8) na profilu produkcyjnym,
- ponownej weryfikacji licencji wag,
- wpisu do dziennika zmian.

## Historia

| Data | Model | Wersja | Kwantyzacja | Osoba |
|---|---|---|---|---|
| 14.08.2026 | Bielik | 11B-v3.0-Instruct | Q4_K_M | pobranie do PoC |
| 16.08.2026 | multilingual-e5-base | intfloat, 768 wym. | FP32 (CPU) | paczka offline dla embeddera |

---

## Embedder — `intfloat/multilingual-e5-base`

Wagi wnoszone **paczką offline** do `models/e5-base/`, montowane do
kontenera tylko do odczytu. Usługa nie pobiera ich samodzielnie — bez
wag nie wstaje (patrz `src/aplikacje/embedder/README.md`).

Uzasadnienie wyboru: [`docs/14-decyzje/ADR-0004-embedder.md`](../docs/14-decyzje/ADR-0004-embedder.md).

### Sumy kontrolne (pobrane 16.08.2026)

```
9dab198f24c8c0879e481cf7822005d5ecbceedbacb390ffafa594e28d31bac4  config.json
62c24cdc13d4c9952d63718d6c9fa4c287974249e16b7ade6d5a85e7bbb75626  tokenizer.json
efb5c0d09722e5fe59a462cd2a9976ee216d55b037597d997cd3fe833216da15  tokenizer_config.json
06e405a36dfe4b9604f484f6a1e619af1a7f7d09e34a8555eb0b77b66318067f  special_tokens_map.json
cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865  sentencepiece.bpe.model
a18a44fad1d0b46ded15928144138cff1135d5cc8233bdd90be5f18822de09a7  model.safetensors
```

⚠️ **Licencja kodu nie jest licencją wag.** Wagi `multilingual-e5-base`
udostępnia intfloat na licencji MIT — do potwierdzenia przy każdej
aktualizacji, tak samo jak przy Bieliku. Same pliki wag są wyłączone
z repozytorium (`.gitignore`), bo ważą 1,1 GB.
