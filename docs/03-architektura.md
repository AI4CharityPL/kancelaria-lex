# 03 — Architektura

## Poziom 1 — kontekst

```
    ┌──────────────┐        ┌───────────────────────────────┐
    │  Prawnik     │───────►│                               │
    │  Aplikant    │        │        kancelaria-lex         │
    │  Administr.  │◄───────│  (jedna maszyna, sieć LAN     │
    │  IOD         │        │   kancelarii, bez internetu)  │
    └──────────────┘        └───────────────────────────────┘
                                     ▲          │
                              skany, │          │ kopie zapasowe
                              pisma  │          ▼ (szyfrowane, offline)
                            ┌────────┴───┐  ┌──────────────┐
                            │ Skaner /   │  │ Nośnik kopii │
                            │ pliki akt  │  │ zapasowych   │
                            └────────────┘  └──────────────┘

    BRAK połączeń wychodzących. Aktualizacje: wyłącznie paczka offline
    wnoszona ręcznie w oknie serwisowym (runbook-aktualizacje.md).
```

## Poziom 2 — kontenery i segmenty sieci

```
╔═══════════════════ net_edge (jedyny segment z dostępem z LAN) ═══════════════╗
║  traefik ── własne CA, mTLS, BEZ ACME          frontend (React, PL)          ║
╚════════════════════════════════════╤═════════════════════════════════════════╝
                                     │
╔════════════════ net_app  (internal: true — brak trasy na zewnątrz) ══════════╗
║  django          celeryworker      celerybeat       flower (bez ekspozycji)  ║
║  postgres+pgvector      redis      minio                                     ║
║                                                                              ║
║  ── własne aplikacje Django ──                                               ║
║  sprawy    agenci    audyt    dostep    anonimizacja                         ║
╚═════════════╤═══════════════════════════════════════════╤════════════════════╝
              │                                           │
╔═══ net_ai (internal) ══════╗            ╔═══ net_parse (internal) ═══════════╗
║  ollama    (Bielik-11B)    ║            ║  docling + tesseract + rapidocr    ║
║  embedder  (e5-base, 768)  ║            ║  gotenberg   docxodus              ║
╚════════════════════════════╝            ║  privacy_filter                    ║
                                          ╚════════════════════════════════════╝
```

**Reguła:** tylko `net_edge` jest osiągalny z sieci kancelarii. Trzy pozostałe segmenty są `internal: true` — Docker nie tworzy dla nich trasy do bramy, więc kontener nie ma jak wyjść na zewnątrz nawet przy poprawnym DNS i poprawnej konfiguracji aplikacji.

`django` jest jedynym kontenerem należącym do więcej niż jednego segmentu wewnętrznego — pełni rolę punktu styku między aplikacją, modelami a parserami.

## Poziom 3 — komponenty własne

```
                          ┌──────────────────────────┐
    pytanie prawnika ────►│  agenci.orkiestrator     │
                          │  (bez narzędzi sieciowych)│
                          └────────┬─────────────────┘
                                   │ kontekst = wyłącznie dane
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             ┌────────────┐ ┌────────────┐ ┌────────────┐
             │ retrieval  │ │  ollama    │ │ narzędzia  │
             │ (pgvector  │ │  (Bielik)  │ │ domenowe   │
             │  + FTS)    │ │            │ │ (terminy)  │
             └────────────┘ └─────┬──────┘ └────────────┘
                                  │ odpowiedź + deklarowane cytaty
                                  ▼
                      ┌───────────────────────────┐
                      │ agenci.weryfikator_cytatow│  ◄── kluczowy komponent
                      │ porównuje deklarowany span│
                      │ ze źródłem, znak po znaku │
                      └───────────┬───────────────┘
                                  │ twierdzenia bez pokrycia → odrzucone
                                  ▼
                       odpowiedź dla prawnika + log audytowy
```

### Aplikacje własne

| Aplikacja | Odpowiedzialność |
|---|---|
| `sprawy` | Model domenowy: Sprawa, Sygnatura, Organ, Strona, Etap, Termin, Rozprawa. Powiązanie ze zbiorem dokumentów (`Corpus`) forka. |
| `agenci` | Orkiestracja agentów, katalog narzędzi (allowlista), weryfikator cytatów, deterministyczny silnik terminów. |
| `audyt` | Log append-only z łańcuchem sum kontrolnych, poza bazą aplikacji. |
| `dostep` | Uprawnienia imienne, ściany etyczne, odrębne kluczowanie materiału obrończego. |
| `anonimizacja` | Pseudonimizacja przed eksportem i przed użyciem materiału w ewaluacji. |

## Kluczowe różnice wobec upstreamu (OpenContracts)

| Obszar | Upstream | Tutaj | Powód |
|---|---|---|---|
| Sieci | brak definicji, domyślny bridge | 4 segmenty, 3 `internal` | egres trzeba odciąć na poziomie trasy |
| SDK chmurowe | `anthropic`, `google` jako ekstras `pydantic-ai-slim` | usunięte z builda | kod, którego nie ma, nie zadzwoni |
| `openai` | zależność bazowa | **zostaje** | jest transportem do Ollamy — patrz niżej |
| Serwer MCP | `/mcp/` aktywny | usunięty z routingu i zależności | wymóg samodzielnej instancji |
| Telemetria | `posthog==7.35.4` | usunięta z builda | wyciek metadanych |
| TLS | Traefik + ACME (Let's Encrypt) | własne CA + mTLS | ACME wymaga wyjścia na zewnątrz |
| Embedder | `all-MiniLM-L6-v2`, 384 wym., angielski | `multilingual-e5-base`, 768 wym. | jakość retrievalu na polskich pismach |
| Obrazy | tagi `latest` z prywatnych przestrzeni | przypięte po `sha256`, lokalne lustro | łańcuch dostaw dla akt karnych |
| Port 5555 | wystawiony | zamknięty w segmencie | ujawnia metadane zadań Celery |

### Dlaczego pakiet `openai` zostaje

Weryfikacja kodu wykazała, że **Ollama jest obsługiwana przez `OpenAIProvider`**, a nie przez dedykowanego klienta — Ollama wystawia API zgodne z OpenAI. Kod forka wprost podstawia atrapę klucza (`"ollama"`), gdy klucza brak.

Konsekwencja jest istotna i przeczy intuicji z raportu źródłowego: **usunięcie pakietu `openai` zepsułoby lokalny model, a jego pozostawienie nie tworzy ryzyka samo w sobie**. Ryzykiem jest adres, pod który ten klient uderza. Dlatego gwarancją nie jest brak klucza (klucz i tak jest podstawiany), lecz **przypięcie `base_url` do allowlisty** — egzekwowane przy starcie procesu i przy zapisie do bazy — plus brak trasy sieciowej.

Szczegóły i pozostałe ustalenia: [`05-izolacja-i-siec.md`](05-izolacja-i-siec.md).

## Przepływ danych — wgranie i zapytanie

```
WGRANIE
  plik ──► django ──► minio (szyfrowany magazyn)
                 └──► celery ──► gotenberg (konwersja, gdy trzeba)
                              └► docling + tesseract/rapidocr (OCR + układ)
                              └► podgląd i korekta OCR przez człowieka   ◄── bramka
                              └► embedder e5-base ──► pgvector
                              └► agent metadanych ──► propozycja sygnatury,
                                    organu, dat ──► potwierdzenie człowieka ◄── bramka

ZAPYTANIE
  pytanie ──► retrieval hybrydowy ──► kontekst (jako DANE, nie instrukcje)
          ──► ollama/Bielik ──► odpowiedź + deklarowane cytaty
          ──► weryfikator cytatów (porównanie ze źródłem)  ◄── bramka
          ──► odpowiedź prawnikowi + wpis do logu audytowego
```

Trzy bramki z udziałem człowieka są celowe: OCR bywa zawodny na kserokopiach, metadane bywają błędne, a odpowiedź modelu jest materiałem roboczym — nie ustaleniem.

## Decyzje architektoniczne

Uzasadnienia w [`14-decyzje/`](14-decyzje/): ADR-0001 fundament · ADR-0002 model językowy · ADR-0003 strategia izolacji · ADR-0004 embedder · ADR-0005 terminy deterministyczne · ADR-0006 weryfikacja cytatów zamiast sędziego LLM.
