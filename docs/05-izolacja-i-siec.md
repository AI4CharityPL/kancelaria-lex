# 05 — Izolacja: trzy warstwy gwarancji

To jest dokument rozstrzygający dla całego projektu. Wszystko inne można poprawić po wdrożeniu — wyciek akt karnych jest nieodwracalny.

## Teza

**Izolacja oparta na konfiguracji nie jest izolacją.** Konfigurację można cofnąć jednym wpisem — świadomie, przez pomyłkę, albo przy merge'u z upstreamem. Raport źródłowy proponował gwarancję opartą na braku kluczy API w `.env`. Weryfikacja kodu wykazała, że ta gwarancja nie działa (ustalenie U-1 i U-2 poniżej).

Zamiast tego trzy warstwy, z których **każda działa samodzielnie**, gdy dwie pozostałe zawiodą:

| | Warstwa | Mechanizm | Czemu zapobiega |
|---|---|---|---|
| **A** | Build | Kodu dostawców chmurowych nie ma w obrazie | Wywołaniu, którego nie da się napisać |
| **B** | Proces | Adres modelu musi należeć do allowlisty; inaczej proces nie wstaje | Błędnej i celowej zmianie konfiguracji |
| **C** | Sieć | Segmenty `internal: true` — brak trasy do bramy | Wszystkiemu powyższemu, gdyby zawiodło |

---

## Ustalenia z weryfikacji kodu OpenContracts

Weryfikacja gałęzi `main` z 14.08.2026. **Przed forkiem należy powtórzyć** — upstream się zmienia.

### U-1 · Ollama jedzie przez klienta OpenAI

`model_factory` obsługuje dostawców `openai`, `ollama`, `anthropic`, `google-gla`. **Ollama jest routowana przez `OpenAIProvider`**, ponieważ wystawia API zgodne z OpenAI. Kod wprost komentuje, że klient OpenAI wymaga *jakiegoś* klucza, nawet gdy serwer go ignoruje, i **podstawia atrapę `"ollama"`**, gdy klucza brak.

> **Konsekwencja:** teza „bez klucza te ścieżki nie są dostępne" jest fałszywa dla ścieżki lokalnej — klucz jest podstawiany automatycznie. Co więcej, pakiet `openai` **musi zostać** w obrazie, bo bez niego nie zadziała model lokalny. Punktem kontroli nie jest więc klucz, tylko **adres**.

### U-2 · Poświadczenia mogą mieszkać w bazie danych

`PipelineSettings` przechowuje `api_key` i `base_url` w bazie, z regułą **„baza wygrywa, zmienna środowiskowa jest zapasem"**.

> **Konsekwencja:** czysty `.env` niczego nie gwarantuje. Osoba z dostępem do panelu administracyjnego może wpisać klucz dostawcy chmurowego i zewnętrzny `base_url` bezpośrednio w bazie, nie dotykając plików. Potrzebna jest blokada na poziomie zapisu do modelu, nie tylko walidacja zmiennych.

### U-3 · SDK chmurowe i MCP to zależności twarde

W `requirements/base.txt`:
```
openai>=2.52.0,<3
pydantic-ai-slim[openai,anthropic,google,mcp]>=1.107.1,<2
posthog==7.35.4
mcp>=1.28.1,<2
```

> **Konsekwencja:** SDK Anthropic i Google, biblioteka telemetryczna i serwer MCP trafiają do obrazu produkcyjnego. Wyłączenie ich konfiguracją zostawia żywy, importowalny kod.

### U-4 · Żaden plik compose nie definiuje sieci

Ani `local.yml`, ani `production.yml` nie zawierają sekcji `networks`. Wszystkie usługi lądują na domyślnym mostku, który **ma trasę do internetu**.

> **Konsekwencja:** „ograniczenie egresu na poziomie sieci Docker" z raportu nie jest przełącznikiem do włączenia. Topologię trzeba napisać od zera.

### U-5 · Obrazy z tagiem `latest` z prywatnych przestrzeni

`jscrudato/docsling-local`, `jscrudato/vector-embedder-microservice`, `ghcr.io/jsv4/vectorembeddermicroservice:latest`, `ghcr.io/open-source-legal/privacy-filter:latest`.

> **Konsekwencja:** przy aktach karnych nie do przyjęcia. `latest` oznacza, że treść obrazu może się zmienić między jednym `pull` a drugim, bez śladu w repozytorium.

### U-6 · Traefik używa ACME

Certyfikaty przez Let's Encrypt, wolumen `production_traefik` na dane ACME.

> **Konsekwencja:** ACME **z definicji wymaga połączenia wychodzącego** i publicznie rozwiązywalnej domeny. W środowisku zamkniętym nie ma prawa działać. Raport tego nie wychwycił.

### U-7 · Domyślny embedder jest anglojęzyczny

`all-MiniLM-L6-v2`, 384 wymiary, trenowany na korpusie angielskim.

> **Konsekwencja:** to kwestia jakości, nie bezpieczeństwa, ale znacząca — retrieval na polskich pismach procesowych będzie słaby. Zamiana na `multilingual-e5-base` (768 wym.).

### U-8 · Port 5555 wystawiony

Panel Celery/flower w obu plikach compose.

> **Konsekwencja:** ujawnia nazwy zadań i ich argumenty — a więc identyfikatory dokumentów i spraw. Metadane też są objęte tajemnicą.

---

## Warstwa A — build

Cel: **kod, którego nie ma w obrazie, nie wykona połączenia.**

### Zmiany w zależnościach

| Pakiet | Działanie | Uzasadnienie |
|---|---|---|
| `pydantic-ai-slim[openai,anthropic,google,mcp]` | → `pydantic-ai-slim[openai]` | Usuwamy ekstras `anthropic`, `google`, `mcp`. **Ekstras `openai` zostaje** — U-1. |
| `openai` | **zostaje** | Transport do lokalnej Ollamy. Usunięcie zepsułoby model lokalny. |
| `posthog==7.35.4` | usunięty | Telemetria — I-3 |
| `mcp>=1.28.1` | usunięty | Wymóg samodzielnej instancji — I-4 |

### Zmiany w kodzie

- Usunięcie routingu `/mcp/` z `urls.py`; test sprawdza, że `GET /mcp/` zwraca 404.
- Usunięcie gałęzi dostawców `anthropic` i `google-gla` z `model_factory` — nie tylko wyłączenie, lecz usunięcie kodu, żeby import nie był możliwy.
- Traefik: konfiguracja ACME zastąpiona certyfikatami z własnego CA (`infra/ca/`).

### Bramka CI — najważniejszy element tej warstwy

Build **pada**, jeśli w lockfile pojawi się którykolwiek z: `anthropic`, `google-genai`, `google-generativeai`, `posthog`, `mcp`.

To zabezpieczenie przed najbardziej prawdopodobnym trybem awarii projektu: **za pół roku ktoś zrobi merge z upstreamem i cicho przywróci ekstras.** Bez bramki nikt tego nie zauważy, dopóki nie będzie za późno. Z bramką — build pada tego samego dnia.

Implementacja: `tests/izolacja/test_czystosc_builda.py`.

---

## Warstwa B — proces

Cel: **proces z niepoprawnym adresem modelu nie może wstać.**

### Allowlista adresów

Jedyne dopuszczalne adresy bazowe:
```
http://ollama:11434/v1        # model językowy
http://embedder:8000          # embeddingi
```

### Strażnik startowy

W `AppConfig.ready()` aplikacji `agenci`: każdy skonfigurowany `base_url` — ze zmiennych środowiskowych i z bazy — jest porównywany z allowlistą. Adres spoza listy podnosi `ImproperlyConfigured` i **proces się nie uruchamia**.

Świadomie wybrano twarde zatrzymanie zamiast ostrzeżenia w logu. System, który przy błędnej konfiguracji działa dalej i loguje ostrzeżenie, będzie działał dalej — ostrzeżenia nikt nie czyta.

### Blokada zapisu do bazy (odpowiedź na U-2)

Sygnał `pre_save` na `PipelineSettings`:
- adres spoza allowlisty → wyjątek, zapis odrzucony,
- próba zapisu → wpis w logu audytowym z tożsamością użytkownika,
- ustawienie niepustego `api_key` dla dostawcy innego niż lokalny → odrzucone.

To zamyka drogę, której nie zamyka czysty `.env`.

### Weryfikacja sum kontrolnych wag

Przy starcie: porównanie sum kontrolnych wag modeli z manifestem w `models/`. Rozbieżność → zatrzymanie (T-3).

---

## Warstwa C — sieć

Cel: **nawet poprawnie zbudowane żądanie nie ma którędy wyjść.**

### Topologia (odpowiedź na U-4)

| Segment | `internal` | Usługi | Uzasadnienie |
|---|---|---|---|
| `net_edge` | nie | traefik, frontend | Jedyny punkt styku z LAN kancelarii |
| `net_app` | **tak** | django, celery×2, postgres, redis, minio, flower | Rdzeń aplikacji i dane |
| `net_ai` | **tak** | ollama, embedder | Modele — U-1 |
| `net_parse` | **tak** | docling, gotenberg, docxodus, privacy_filter | Parsery — I-2 |

`internal: true` sprawia, że Docker **nie tworzy trasy do bramy**. Kontener w takim segmencie nie wyjdzie na zewnątrz nawet z poprawnym DNS i poprawną konfiguracją aplikacji.

`net_parse` osobno od `net_app` z powodu I-2: LibreOffice w gotenbergu potrafi próbować pobrać zasoby osadzone w konwertowanym pliku. Pismo od strony przeciwnej z linkowanym obrazem staje się wtedy potwierdzeniem odbioru pod kontrolowanym adresem. Kontrola aplikacyjna jest tu zawodna — trasa jej nie ma.

Port 5555 schodzi z ekspozycji (U-8).

### Łańcuch dostaw (odpowiedź na U-5)

- Wszystkie obrazy przypięte po `sha256`, nie po tagu.
- Lokalne lustro rejestru; środowisko docelowe nie pobiera z internetu.
- SBOM (CycloneDX) generowany przy buildzie i przechowywany razem z wydaniem.
- Przegląd i weryfikacja sum przed wniesieniem paczki do strefy zamkniętej — [`10-operacje/runbook-aktualizacje.md`](10-operacje/runbook-aktualizacje.md).

### Zabezpieczenia kontenerów

Bez roota · read-only rootfs tam, gdzie możliwe · profile seccomp · brak dostępu do gniazda Dockera · limity zasobów (D-1) · `no-new-privileges`.

---

## Dowód, nie deklaracja

Izolacja jest testowana, nie opisywana. `tests/izolacja/` sprawdza dla **każdego** kontenera:

1. **DNS nie rozwiązuje** nazw zewnętrznych.
2. **TCP nie łączy** na zewnątrz (adres IP wprost, z pominięciem DNS).
3. **Kanarek DNS** — unikatowa nazwa, której zapytanie nigdy nie pojawia się w sinkhole'u.
4. **`GET /mcp/` → 404.**
5. **Lockfile czysty** z zakazanych pakietów.
6. **Strażnik działa** — podmieniony `base_url` blokuje start; zapis do bazy odrzucony i zalogowany.
7. **Przechwycenie ruchu** na mostku hosta podczas pełnego przebiegu dokumentu → **zero pakietów wychodzących**.

Punkt 7 jest dowodem końcowym: nie sprawdza konfiguracji, tylko obserwuje rzeczywistość.

## Co pozostaje poza zasięgiem tych warstw

Uczciwe zamknięcie: trzy warstwy chronią przed wyciekiem **przez system**. Nie chronią przed osobą z legalnym dostępem, która skopiuje akta na pendrive, ani przed zajęciem fizycznym serwera. Te ryzyka adresują kontrola dostępu do pomieszczenia, szyfrowanie nośnika, log audytowy i zobowiązania zawodowe — patrz [`04-model-zagrozen.md`](04-model-zagrozen.md), ryzyka rezydualne.
