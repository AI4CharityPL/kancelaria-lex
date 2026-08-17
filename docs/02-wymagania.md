# 02 — Wymagania

Priorytety wg MoSCoW: **M** = musi mieć (brak = projekt nie ma sensu), **S** = powinien mieć, **C** = może mieć, **W** = poza tą fazą.

## Wymagania funkcjonalne

### Obieg dokumentu

| ID | Wymaganie | Prio |
|---|---|---|
| F-01 | Wgranie dokumentu (PDF, DOCX, TXT, obrazy, formaty starsze przez konwersję) do sprawy | M |
| F-02 | OCR skanów w języku polskim z zachowaniem układu strony | M |
| F-03 | Wynik OCR podlega podglądowi i ręcznej korekcie przed indeksowaniem | M |
| F-04 | Automatyczna klasyfikacja rodzaju pisma (akt oskarżenia, postanowienie, wyrok, protokół, opinia biegłego, pismo procesowe) | S |
| F-05 | Ekstrakcja metadanych: sygnatura, organ, strony, daty, data doręczenia | M |
| F-06 | Wersjonowanie dokumentu i historia zmian | S |

### Praca z aktami

| ID | Wymaganie | Prio |
|---|---|---|
| F-10 | Pytanie w języku naturalnym do akt sprawy z odpowiedzią **zawsze z cytatami** | M |
| F-11 | Każdy cytat prowadzi do konkretnego miejsca w dokumencie (dokument + zakres znaków) | M |
| F-12 | Odmowa odpowiedzi, gdy akta nie zawierają podstawy — zamiast odpowiedzi prawdopodobnej | M |
| F-13 | Chronologia zdarzeń sprawy budowana z dokumentów | S |
| F-14 | Wykrywanie rozbieżności między relacjami (zeznania, wyjaśnienia) | S |
| F-15 | Wyszukiwanie łączone: semantyczne + pełnotekstowe | M |
| F-16 | Ekstrakcja masowa jednego pola z wielu dokumentów naraz | C |

### Sprawy i terminy

| ID | Wymaganie | Prio |
|---|---|---|
| F-20 | Rejestr spraw: sygnatura, organ, etap, strony, prowadzący | M |
| F-21 | **Terminy procesowe liczone deterministycznie** na podstawie zdarzenia inicjującego | M |
| F-22 | Model może *zaproponować* zdarzenie inicjujące; termin wylicza kod, nie model | M |
| F-23 | Każdy termin wymaga potwierdzenia przez prawnika przed uznaniem za obowiązujący | M |
| F-24 | Kalendarz terminów i rozpraw z ostrzeganiem z wyprzedzeniem | M |
| F-25 | Rozpoznawanie polskich wzorców sygnatur (`II K 123/26`, `III Kp 45/26`, `PO I Ds 12.2026`) | S |
| F-26 | Szkic pisma z szablonu, zawsze do redakcji przez prawnika | C |

### Poufność i dostęp

| ID | Wymaganie | Prio |
|---|---|---|
| F-30 | Dostęp do sprawy nadawany imiennie, zasada wiedzy koniecznej | M |
| F-31 | **Materiał obrończy w odrębnym, osobno kluczowanym magazynie** | M |
| F-32 | Ściany etyczne — blokada dostępu przy konflikcie interesów | M |
| F-33 | Log audytowy: kto, kiedy, który dokument, jaka operacja | M |
| F-34 | Log audytowy odporny na manipulację (łańcuch sum kontrolnych) | M |
| F-35 | Pseudonimizacja przed jakimkolwiek eksportem poza system | S |
| F-36 | Uwierzytelnianie wieloskładnikowe | M |

## Wymagania niefunkcjonalne

### Izolacja — wymagania rozstrzygające

| ID | Wymaganie | Weryfikacja |
|---|---|---|
| N-01 | Żaden kontener nie nawiązuje połączenia poza segment | `tests/izolacja/` — DNS i TCP zawodzą dla każdego kontenera |
| N-02 | Pełny przebieg dokumentu nie generuje ruchu wychodzącego | Przechwycenie na mostku hosta, asercja zera pakietów |
| N-03 | Obraz produkcyjny nie zawiera SDK dostawców chmurowych | Skan lockfile w CI, build pada przy wykryciu |
| N-04 | Brak serwera MCP | `GET /mcp/` → 404 |
| N-05 | Adres modelu poza allowlistą blokuje start procesu | Test uruchomieniowy z podmienioną zmienną |
| N-06 | Zapis adresu spoza allowlisty do bazy jest odrzucany i logowany | Test integracyjny na `PipelineSettings` |
| N-07 | Brak telemetrii w obrazie | `posthog` nieobecny w lockfile |
| N-08 | Wszystkie obrazy przypięte po sumie `sha256` | Skan compose w CI |

### Jakość odpowiedzi

| ID | Wymaganie | Próg |
|---|---|---|
| N-10 | Trafność cytowań (cytat istnieje i treść się zgadza) — sprawdzana maszynowo | ≥ 99% |
| N-11 | Poprawność merytoryczna na gold secie, ocena ludzka | ≥ 85% |
| N-12 | Poprawna odmowa przy pytaniu bez pokrycia w aktach | ≥ 90% |
| N-13 | Odporność na wstrzyknięcie polecenia w treści dokumentu | 100% — zero wykonanych poleceń |
| N-14 | CER OCR na skanach dobrej jakości | ≤ 2% |
| N-15 | CER OCR na kserokopiach słabej jakości | ≤ 10%, oznaczone do weryfikacji ręcznej |

Progi N-10 do N-15 są **bramkami**: dopóki nie są spełnione, system nie dotyka rzeczywistych akt.

### Pozostałe

| ID | Wymaganie | Wartość |
|---|---|---|
| N-20 | Odpowiedź agenta na pytanie do akt | < 60 s (profil rozwojowy), < 20 s (produkcja) |
| N-21 | OCR strony | < 3 s (Tesseract), < 10 s (RapidOCR) |
| N-22 | Szyfrowanie danych w spoczynku | pełne szyfrowanie nośnika + klucz per sprawa |
| N-23 | Odtworzenie z kopii zapasowej | RPO ≤ 24 h, RTO ≤ 8 h, test odtworzenia kwartalnie |
| N-24 | Interfejs w języku polskim | pełna lokalizacja |
| N-25 | Retencja zgodna z zasadami przechowywania akt | konfigurowalna, domyślnie 10 lat |

## Poza zakresem tej fazy (W)

Rozliczenia i fakturowanie · integracja z Portalem Informacyjnym sądów · podpis kwalifikowany · e-Doręczenia · aplikacja mobilna · praca wielooddziałowa z replikacją · zewnętrzny pentest · migracja danych historycznych.
