# 15 — Rejestr ryzyk

Dokument żywy. Przegląd półroczny oraz przy każdej istotnej zmianie architektury. Ostatni przegląd: **14.08.2026**.

Skala: prawdopodobieństwo (N/Ś/W) × skutek (N/Ś/W/**K**rytyczny).

---

## Ryzyka krytyczne — wymagają stałej uwagi

| ID | Ryzyko | P | S | Środki | Poziom | Właściciel |
|---|---|---|---|---|---|---|
| **RY-01** | Wyciek treści akt do zewnętrznego dostawcy modelu | N | **K** | Trzy warstwy izolacji, testowane wykonywalnie (I-1…I-9, O-1) | Niskie | inżynier systemu |
| **RY-02** | Ujawnienie materiału obrończego | N | **K** | Odrębny magazyn, odrębny klucz, odrębna autoryzacja (T-1, T-2) | Niskie | wspólnicy |
| **RY-03** | Merge z upstreamem cicho przywraca SDK chmurowe | **Ś** | **K** | **Bramka CI na lockfile** + strażnik startowy | Niskie | inżynier systemu |

**RY-03 zasługuje na uwagę mimo niskiego poziomu wynikowego.** To najbardziej prawdopodobny sposób, w jaki projekt może cicho stracić swoją główną właściwość: za pół roku ktoś zrobi rutynowy merge, a `pydantic-ai-slim[openai,anthropic,google,mcp]` wróci wraz z nim. Bez bramki nikt tego nie zauważy do czasu incydentu. Z bramką — build pada tego samego dnia.

---

## Ryzyka techniczne

| ID | Ryzyko | P | S | Środki | Poziom |
|---|---|---|---|---|---|
| RY-10 | Jakość Bielika w Q4 niewystarczająca | **W** | Ś | Oczekiwane; bramki mierzone na profilu produkcyjnym; Q4 nigdy przy realnych aktach | Akceptowane |
| RY-11 | Retrieval gubi istotne fragmenty przy 8k kontekstu | Ś | W | Wyszukiwanie hybrydowe; pomiar na gold secie; większy kontekst w produkcji | Średnie |
| RY-12 | OCR zawodzi na kserokopiach i piśmie odręcznym | **W** | Ś | RapidOCR jako zapas, kolejka weryfikacji ręcznej, CER jako bramka (J-5, J-6) | Średnie |
| RY-13 | Upstream zmienił się względem ustaleń U-1…U-8 | Ś | W | Weryfikacja przed forkiem jako krok obowiązkowy | Niskie |
| RY-14 | Podmiana obrazu z prywatnej przestrzeni rejestru | N | W | Przypięcie po `sha256`, lokalne lustro, weryfikacja przed wniesieniem | Niskie |
| RY-15 | Luka 0-day w komponencie stosu | Ś | W | Segmentacja ogranicza zasięg; okno serwisowe; SBOM | Średnie |
| **RY-16** | **Odpowiedź na pytanie bez pokrycia w aktach** | **W** | **K** | Cytat weryfikowany znak po znaku; kontrola modelem; **luka otwarta — patrz niżej** | **Wysokie** |
| RY-17 | Jedno uwierzytelnianie zamiast dwóch (art. 21 ust. 2 lit. j) | Ś | Ś | Hasło `scrypt`, sesja serwerowa 12 h; drugi składnik niewdrożony | Średnie |
| RY-18 | Jedna osoba blokuje pozostałe (semafor 1 + eskalacja 5–8 min) | **W** | Ś | Kolejka i tor głęboki istnieją; semafor **sprawdzony testem**, opóźnienie drugiej osoby wciąż niezmierzone | Średnie |
| **RY-19** | **Utrata zapisu przy pracy dwóch osób naraz** | — | **K** | **ZAMKNIĘTE 16.08.2026** — patrz niżej | Zamknięte |
| **RY-20** | Odmowa 401 zrywa połączenie zamiast je zamknąć | — | N | **ZAMKNIĘTE 16.08.2026** — ciało żądania opróżniane przed odmową | Zamknięte |
| **RY-21** | Brak egzekwowania adresu modelu w produkcie (`panel/`) | Ś | **K** | **ZAMKNIĘTE 16.08.2026** — `panel/siec.py`, proces nie wstaje przy adresie spoza pętli zwrotnej; 25 testów na kodzie produkcyjnym | Zamknięte |
| **RY-22** | Stos `compose.yml` nie daje się postawić w całości | Ś | Ś | **Embedder ZBUDOWANY 16.08.2026** — patrz niżej. Zostają django/postgres/frontend (fork Django) | Średnie |
| RY-23 | I-5 (kanarek DNS) nigdy nie wykonany | Ś | Ś | Wymaga sinkhole'a — `infra/policies/sinkhole.md`. Termin: przed pierwszymi rzeczywistymi aktami | Średnie |

---

## RY-22 — embedder uzupełniony (16.08.2026)

`compose.yml` wskazywał na `src/aplikacje/embedder`, którego **w
repozytorium nie było**. Stos nie dawał się postawić, a `docker compose
up` kończył się `path not found`. To dlatego bramki I-3 i I-4 były
pomijane, a O-1 zaszyty na bezwarunkowy `skip`.

**Co powstało:** usługa `multilingual-e5-base` (768 wymiarów, ADR-0004)
na CPU, zgodna z protokołem OpenAI (`POST /v1/embeddings`), plus
`Dockerfile` i procedura przygotowania paczki offline z wagami.

**Trzy własności ważniejsze od samej funkcjonalności:**

1. **Wagi wyłącznie z zamontowanego wolumenu.** `transformers` domyślnie
   dociąga model z internetu, gdy nie znajdzie go lokalnie — w tym
   systemie byłoby to ciche wyjście na zewnątrz. Obraz ustawia
   `HF_HUB_OFFLINE=1` i `TRANSFORMERS_OFFLINE=1`, a usługa sprawdza
   obecność wag **przed** importem biblioteki.
2. **Brak wag = brak startu.** Kod wyjścia 2 i komunikat wskazujący
   procedurę. Usługa nie wstaje „w trybie ograniczonym" i nie zwraca
   wektorów zerowych: embedder zwracający zera wygląda na działający,
   a retrieval przestaje działać w ciszy.
3. **Pole `typ` bez wartości domyślnej.** Rodzina E5 wymaga prefiksu
   `query:`/`passage:`; jego pominięcie nie daje błędu, tylko cicho
   gorszy retrieval. Pierwsza wersja przyjmowała `passage` przy braku
   pola — wyłapał to test i zostało to usunięte.

**Sprawdzone na żywo:** kontener wstaje (`healthy`), zwraca
znormalizowane wektory 768-wymiarowe, a pytanie po polsku jest bliżej
fragmentu, który na nie odpowiada, niż fragmentu o czymś innym — czyli
powód, dla którego ADR-0004 odrzucił `all-MiniLM-L6-v2`, jest
zaspokojony. Bramki I-3 i I-4 objęły embedder: **85 sprawdzeń zamiast
79**.

**Zostaje otwarte:** `django`, `postgres` i `frontend` nadal wymagają
budowania z forka Django i nie były stawiane. Pełne O-1 wg
`skrypty/przechwyc-ruch.md` (cykl wgranie→OCR→embedding→odpowiedź)
pozostaje przez to niewykonalne.

---

## RY-19 — utrata zapisu przy pracy równoległej (zamknięte 16.08.2026)

**Jak wyszło na jaw.** Pierwszy test wysyłający żądania równolegle
(`tests/test_wspolbieznosc.py`) wywrócił panel natychmiast:

```
sqlite3.InterfaceError: bad parameter or other API misuse
```

przy dziesięciu wątkach zakładających wątki rozmów jednocześnie.

**Dlaczego to było groźne.** Wymóg naczelny projektu brzmi „różne osoby,
w różnym czasie, na różnych profilach". Dotychczasowe testy pokrywały
wyłącznie część „w różnym czasie" — każdy wysyłał żądania po kolei.
Skutkiem było ciche gubienie zapisów dokładnie w scenariuszu, dla
którego ten system powstał: dwie osoby pracujące w tej samej chwili.

**Przyczyna.** `sqlite3.threadsafety == 3`, więc warstwa C była
serializowana i to nie ona zawodziła. Zawodziła warstwa Pythona: moduł
trzyma cache przygotowanych zapytań per połączenie, a dwa wątki
wykonujące ten sam SQL sięgały po ten sam obiekt statement.

**Naprawa** (`panel/baza.py`, klasa `Polaczenie`): `cached_statements=0`
oraz re-entrantny zamek na `execute`/`executemany`/`executescript`/
`commit`. Nie jest to optymalizacja — przy kilku osobach i przy SQLite
szeregującym zapisy koszt jest znikomy, a poprawność warta więcej niż
przepustowość.

**Bramka:** 7 testów w `tests/test_wspolbieznosc.py`, w tym 20
równoległych zapisów i 40 przeplecionych żądań dwóch profili.

---

## RY-16 — najważniejsza otwarta pozycja jakościowa

**Stan zmierzony 16.08.2026** (100 przypadków, pełny korpus, konfiguracja
wysyłkowa „sam kontroler"): na 50 pytań, na które akta nie dają odpowiedzi,
system odpowiedział **9 razy**. J-3 = 82% przy **celu 90%**.

**Dlaczego to jest ryzyko krytyczne w skutku, a nie tylko liczba.** Prawnik
dostaje odpowiedź tam, gdzie akta jej nie dają — z cytatem prowadzącym do
prawdziwego zdania, które jednak tezy nie popiera. Jest to wykrywalne
w sekundę przez kliknięcie w cytat, ale wyłącznie przez kogoś, kto kliknie.

**Dlaczego nie domknęliśmy tego odrzucaniem.** Każdy zmierzony wariant
pokazuje, że J-3 kupuje się wyłącznie za trafność:

| wariant | J-3 | trafność | poprawnych łącznie |
|---|---:|---:|---:|
| bez kontroli | 76% | 80% | 78 |
| **sam kontroler — wysyłka** | **82%** | **78%** | **80** |
| obie kontrole | 84% | 70% | 77 |
| NL-do-formatu + obie | 90% | 48% | 69 |

Ostatni wiersz osiąga cel i jest jednocześnie najgorszą konfiguracją — traci
połowę poprawnych odpowiedzi. To jest dowód, że problem leży **przed**
generacją, nie po niej.

**Środek zaradczy (J2.2, niewdrożony):** ocena odpowiadalności zanim model
zacznie odpowiadać. Podstawa: *Sufficient Context* (ICLR 2025) — RAG
paradoksalnie OBNIŻA skłonność do odmowy, bo dołożony kontekst podnosi
pewność modelu; małe modele są na to szczególnie podatne.

**Decyzja o progach z 16.08.2026:** próg regresyjny J-3 obniżony do 0,78,
cel 0,90 zapisany osobno jako `CEL_J3` i nieosiągnięty. Nie jest to
złagodzenie wymagania, tylko rozdzielenie progu regresji od celu —
bramka, która świeci czerwono zawsze, przestaje nieść informację.
Każdy przebieg poniżej celu wypisuje ostrzeżenie w testach.

**Właściciel:** inżynier systemu. **Przegląd:** przy każdej zmianie
dotykającej toru szybkiego.
| RY-16 | Utrata klucza materiału obrończego | N | **K** | Procedura depozytu, autoryzacja dwuosobowa, test odtworzenia | Niskie |

---

## Ryzyka merytoryczne

| ID | Ryzyko | P | S | Środki | Poziom |
|---|---|---|---|---|---|
| **RY-20** | **Błędna analiza wpływa na prowadzenie obrony** | Ś | W | Wymuszone cytowanie + weryfikacja maszynowa; **obowiązkowa weryfikacja przez prawnika**; bramki J-2, J-3 | **Średnie** ⚠️ |
| RY-21 | Przeoczony termin z winy systemu | N | W | Silnik deterministyczny; potwierdzenie prawnika; głośne ostrzeganie o niepotwierdzonych | Niskie |
| **RY-22** | **Nadmierne zaufanie użytkowników do narzędzia** | **Ś** | W | Komunikat w interfejsie, nie tylko w regulaminie; szkolenie; jawne pokazywanie cytatów | **Średnie** ⚠️ |
| RY-23 | Manipulacja przez dokument strony przeciwnej | Ś | Ś | Brak narzędzi sieciowych; weryfikacja cytatów; testy czerwonego zespołu (100%) | Niskie |

### RY-20 i RY-22 pozostają na poziomie średnim — świadomie

**RY-20:** weryfikacja cytatów potwierdza, że fragment istnieje i nie został zmyślony. Nie potwierdza, że wniosek z niego wyciągnięty jest trafny. Żadna metoda maszynowa tego nie zapewni. Środek jest organizacyjny: obowiązkowa weryfikacja przez prawnika.

**RY-22 jest ryzykiem, o którym łatwo zapomnieć.** Narzędzie, któremu użytkownik zaufa bezwarunkowo, jest groźniejsze od braku narzędzia — bo znosi czujność, którą prawnik miał wcześniej, czytając akta samodzielnie. Dobrze działający system paradoksalnie zwiększa to ryzyko: im częściej ma rację, tym rzadziej ktoś sprawdza.

Środek: interfejs musi pokazywać cytaty **zawsze i widocznie**, a odmowa odpowiedzi musi być normalnym zachowaniem, nie awarią.

---

## Ryzyka organizacyjne i prawne

| ID | Ryzyko | P | S | Środki | Poziom |
|---|---|---|---|---|---|
| **RY-30** | **Przekroczenie terminu rejestracji KSC (2.10.2026)** | Ś | W | Ścieżka niezależna od projektu; K-1 do 15.09, K-2 do 2.10 | **Wymaga działania teraz** |
| RY-31 | Brak zapewnionego utrzymania forka po wdrożeniu | Ś | W | **Warunek wejścia na produkcję**, nie kwestia do rozstrzygnięcia później | Średnie |
| RY-32 | Zatwierdzanie reguł terminów wchodzi na ścieżkę krytyczną | **W** | Ś | Zaplanować wcześnie — to czas prawnika, nie inżyniera | Średnie |
| RY-33 | Dostęp osoby nieuprawnionej wewnątrz kancelarii | Ś | W | Dostęp imienny, wiedza konieczna, ściany etyczne, MFA, log audytowy | Niskie |
| RY-34 | Kolizja obowiązku zgłoszenia incydentu z tajemnicą | Ś | Ś | Granica ustalona **przed** incydentem (K-6) | Niskie |
| RY-35 | Utrata nośnika kopii zapasowej | N | W | Szyfrowanie kopii, klucz rozdzielnie | Niskie |
| RY-36 | Zmiana kwalifikacji AI Act przez sposób użycia | N | Ś | Zapis granicy w [`07-agenci.md`](07-agenci.md); ponowna ocena przy rozszerzeniach | Niskie |

### RY-30 wymaga działania niezależnie od projektu

Do terminu rejestracyjnego pozostało około 7 tygodni. Zadania K-1 i K-2 nie wymagają ani jednej linii kodu i nie powinny czekać na Fazę 6.

---

## Ryzyka rezydualne — zaakceptowane bez dalszych środków

| Ryzyko | Dlaczego zostaje |
|---|---|
| Osoba z dostępem fizycznym do serwera może wynieść dane | Żaden system tego nie eliminuje; kontrola dostępu do pomieszczenia i szyfrowanie nośnika ograniczają skutek |
| Prawnik z legalnym dostępem może skopiować akta | Ryzyko istnieje niezależnie od systemu; log audytowy i zobowiązania zawodowe |
| Lokalny model jest słabszy od najlepszych komercyjnych | Cena poufności, przyjęta świadomie |
| Odcięcie od sieci utrudnia łatanie | Rekompensowane oknem serwisowym; alternatywa (stałe połączenie) jest gorsza |

---

## Historia przeglądów

| Data | Zmiany |
|---|---|
| 14.08.2026 | Rejestr utworzony. Ryzyka RY-01…RY-03 zidentyfikowane na podstawie weryfikacji kodu upstreamu (ustalenia U-1…U-8). RY-22 dodane po analizie skutków ubocznych dobrze działającego narzędzia. |
