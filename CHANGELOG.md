# Dziennik zmian

Format wg [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/).
Wersjonowanie semantyczne.

Zasada: **spadek jakości jest zmianą i ma tu być odnotowany.** Degradacja
modelu, retrievalu lub OCR jest cicha, w przeciwieństwie do awarii
(`docs/11-testy-i-bramki.md`).

---

## [1.0.0] — 17.08.2026 · pierwsze wydanie publiczne

Publikacja na licencji MIT na koncie **AI4CharityPL**, wraz z prośbą
o wsparcie zbiórki dla wrocławskiego schroniska (TOZ, ratujemyzwierzaki.pl).
System mógł być sprzedawany kancelariom — zamiast tego jest darmowy,
a prośba o zapłatę skierowana do schroniska.

### Dodane
- `README.md` po angielsku, zaczynający się od prośby o wsparcie zbiórki,
  z jednoznacznym zaznaczeniem, że **zbiórka nie jest nasza** i nic z niej
  nie mamy.
- `QUICKSTART.md` — instalacja krok po kroku dla osoby nieznającej wiersza
  poleceń, z sekcją „gdy coś nie działa" i listą obowiązków kancelarii
  przed wpuszczeniem prawdziwych akt.
- `eval/README.md` — skąd wziąć korpusy pomiarowe (SAOS, RECAP) i dlaczego
  nie ma ich w repozytorium.

### Usunięte
- `docs/00-wejscie/` — prywatny raport wejściowy przygotowany dla konkretnej
  osoby i podpisany jej imieniem. Nie niósł niczego, czego nie ma
  w `docs/01`–`22`, a jego publikacja ujawniałaby, kto zamówił tę pracę.
  Dopisany do `.gitignore`, żeby nie wrócił.

### Zmienione
- `LICENSE` — właścicielem praw jest **AI4CharityPL**.
- Repozytorium publikowane z **nową historią**: poprzednia zawierała usunięty
  raport prywatny, a plik usunięty z drzewa zostaje w historii i pozostaje
  możliwy do odtworzenia.

---

## [Niewydane]

### Dodane
- Repozytorium git, `pyproject.toml`, `LICENSE`, ten dziennik.
- `panel/__init__.py` — panel jest pakietem, więc działa `kancelaria-lex`
  z instalacji edytowalnej. `python panel/serwer.py` działa jak dotąd.
- `panel/konfiguracja.py` — jedno źródło prawdy o konfiguracji serwera
  modelu, czytane i przez skrypt startowy, i przez bramkę.
- `skrypty/start.ps1` — ustawia konfigurację, wykrywa serwer pracujący
  na starych ustawieniach i restartuje go, sprawdza modele, podnosi panel.
- `skrypty/przygotuj-modele.ps1` — buduje modele robocze z `models/`.
  Dotąd ta wiedza istniała wyłącznie w głowie autora.
- `skrypty/bramki.ps1` — przebieg bramek z podziałem na grupy
  z `docs/11-testy-i-bramki.md`; `-Zainstaluj` zakłada hak pre-commit.
  Świadomie lokalnie, bez GitHub Actions: to repozytorium zawiera model
  zagrożeń i topologię instancji przetwarzającej akta karne i nie
  powinno opuszczać kancelarii.
- `tests/test_konfiguracja_ollamy.py` — bramka sprawdzająca konfigurację
  trwałą i stan żywego serwera, wraz z testem negatywnym odtwarzającym
  regresję z sierpnia.

- **Benchmark dwujęzyczny** (`eval/benchmark/`) — ilościowa ocena wierności
  cytatu i odmowy, z prawdą wzorcową wyznaczaną maszynowo, bez sędziego
  LLM i bez pracy prawnika. Metoda: pary dopasowane — każdy przypadek
  odpowiadalny ma bliźniaka identycznego co do formy, różniącego się
  wyłącznie wartością kotwicy i sprawdzonego jako nieobecny w aktach.
  Miara naczelna (rozróżnialność par) daje zero obu zachowaniom
  zdegenerowanym: „zawsze odpowiadaj" i „zawsze odmawiaj".
  Uzasadnienie i osadzenie w rynku: `eval/benchmark/README.md`.
- **`panel/zdania.py`** — podział na zdania z offsetami w oryginale,
  ze świadomością skrótów prawniczych (`art.`, `§`, `k.p.k.`, `ust.`,
  `Dz.U.`). Bez tego „art. 445 § 1 k.p.k." rozpada się na cztery zdania.
  Wspólny dla benchmarku i planowanego cytowania po numerze zdania.

### Znalezione benchmarkiem *(usterki systemu, nie benchmarku)*

- **Tor szybki nie miał retrievalu — tylko ucięcie do 6 000 znaków.**
  `agent.py` podawał modelowi pierwsze 6 000 znaków każdego dokumentu.
  Przy medianie 21 tys. znaków na orzeczenie oznaczało to komparycję
  i początek uzasadnienia; wszystko dalsze było niewidoczne. Zmierzone
  pokrycie: **28,2%** treści sprawy 3 i **17,8%** sprawy 4. Odmowy
  wyglądały na ostrożność modelu, a wynikały z tego, że nie pokazano mu
  dokumentu. Tor szybki korzysta teraz z tego samego wyboru fragmentów
  BM25, co analiza.
- **Tor szybki nigdy nie dostał lekcji zapisanej przy etapie mapowania.**
  Szablon kazał modelowi ODPOWIADAĆ na pytanie i eksponował odmowę.
  Ablacja na trzech pytaniach z odpowiedzią obecną w aktach:

  | szablon | model | twierdzeń | czas |
  |---|---|---:|---:|
  | odpowiadający | bielik-lex-dev (11B) | **0** | 11,0 s |
  | odpowiadający | bielik-lex-map (7B) | 6 | 39,4 s |
  | wydobywający | bielik-lex-dev (11B) | **8** | 99,0 s |
  | wydobywający | bielik-lex-map (7B) | 6 | 35,1 s |

  Zero było osiągalne **wyłącznie** w konfiguracji wyjściowej — czyli
  dokładnie tej, która działała w panelu. Zmieniono szablon na
  wydobywający i model na `bielik-lex-map` (99 s przekracza cel N-20).
- **`agent.py` szukał cytatu przez `find()`, nie `znajdz_fragment()`.**
  Tor szybki był surowszy od analizy i gubił poprawne cytaty z PDF-ów
  z powodu łamań wierszy — ta sama przyczyna, przez którą wcześniej
  odrzucono 133 ze 147 twierdzeń z powodem „zakres 0-0".
- **42,5% treści sprawy 3 to znaczniki HTML.** Dokumenty SAOS wgrano
  razem z `<p>`, `<div>`, `<td colspan="3">`, `<span class="anon-block">`.
  Panel indeksuje je jako wyrazy treści, oddaje modelowi zamiast akt
  i pokazuje w cytacie. Przy budżecie 9 000 znaków na mapowanie to
  ~3 800 znaków znaczników. Benchmark czyści je przy wczytaniu, ale
  właściwym miejscem naprawy jest ścieżka wgrywania dokumentu.

### Uwaga dla pracujących na Windows
Skrypty `.ps1` są zapisane w UTF-8 **z BOM**. Windows PowerShell 5.1
czyta pliki bez BOM jako ANSI, przez co polskie znaki rozsypują się
i psują parser — skrypt nie uruchamia się z błędem składni w losowym
miejscu. Edytując je, zachowaj BOM.

### Naprawione
- **Ucinana odpowiedź modelu na etapie mapowania (D-1).** Stała
  `KONTEKST_MAPOWANIA = 8192` była zdefiniowana, ale nigdy nieużyta —
  `_mapuj_dokument` szło na domyślnym `num_ctx = 4096`. Przy wsadzie
  `BUDZET_MAPOWANIA = 9000` znaków (~3285 tokenów) plus szablon zostawało
  ~400 tokenów na odpowiedź, która realnie potrzebuje 600–900. Odpowiedź
  była ucinana w połowie. Wszystkie etapy ujednolicone na 8192, co przy
  okazji usuwa przeładowanie modelu między etapami.
- **Serwer Ollamy pracował na ustawieniach sprzed naprawy (D-2).**
  Log pokazywał `8/8 seqs` i cache `K (f16)` — 12,8 GB KV, z czego
  9,2 GB na CPU, czyli dokładnie stan sprzed naprawy opisanej
  w `eval/wyniki/skala-2026-08-14.md`.

  Przyczyna okazała się inna, niż wyglądało na pierwszy rzut oka:
  **konfiguracja trwała była poprawna od dawna.** Stare wartości
  siedziały w środowisku *działających procesów* — serwer Ollamy
  wystartował przed poprawką i odziedziczył je na cały czas życia.
  Serwer czyta zmienne wyłącznie przy starcie, więc poprawka nigdy
  do niego nie dotarła.

  To jest tryb awarii wart zapamiętania: sprawdzenie zmiennych
  odpowiada „wszystko w porządku", a system pracuje osiemnastokrotnie
  wolniej. Dlatego bramka sprawdza **dwie rozłączne warstwy** —
  konfigurację trwałą (rejestr Windows, nie `os.environ`, który
  pokazuje jedynie to, co odziedziczył proces testu) oraz stan żywego
  serwera czytany z jego logu. `skrypty/start.ps1` restartuje serwer,
  gdy wykryje rozjazd, niezależnie od tego, czy sam coś zmieniał.

  Po naprawie: `1/1 seqs`, `K (q8_0)`, cache 680 MiB zamiast
  12 800 MiB, 41/41 warstw na GPU, model w 100% na karcie.

- **Znacznik `izolacja` nie był nadany żadnemu testowi.** Był
  zadeklarowany w `pytest.ini` i opisany jako „bramki izolacji
  (I-1…I-9)", ale nie nosił go ani jeden test. `pytest -m izolacja`
  zbierał zero testów i kończył się kodem 5 — przebieg „bramek
  izolacji" nie sprawdzał niczego, a `-m "not izolacja"` nie wykluczał
  niczego, więc bramki wymagające Dockera wchodziły do szybkiego
  przebiegu jednostkowego. Znacznik nadawany teraz katalogiem
  (`tests/izolacja/conftest.py`), żeby test dopisany w przyszłości
  dostał go sam.

- **`--dozwol-pominiecie` nie dało się podać w wierszu poleceń.**
  `pytest_addoption` stało w `tests/izolacja/conftest.py`, którego
  pytest nie traktuje jako conftestu początkowego — opcja
  rejestrowała się dopiero przy zbieraniu testów, czyli po
  sparsowaniu argumentów. Działała z poziomu kodu, ale próba użycia
  jej tak, jak instruują `docs/11-testy-i-bramki.md` i komunikat samej
  bramki, kończyła się „unrecognized arguments". Furtka, z której nie
  da się skorzystać, jest gorsza od jej braku: pod presją ktoś sięgnie
  po `-k` albo `--ignore` i wyłączy więcej, niż zamierzał.
  Przeniesione do `tests/conftest.py`.

---

## [0.1.0-poc] — 14.08.2026

Stan wyjściowy: proof of concept z pełną dokumentacją projektową.

### Działa
- Panel spraw (`panel/serwer.py`, port 8713) — sprawy, dokumenty, czat
  z pamięcią zamkniętą w obrębie sprawy, korpus przepisów.
- Głęboka analiza map-reduce: dekompozycja → wybór dokumentów (BM25) →
  mapowanie per dokument → przepisy → synteza → weryfikacja cytatów.
- Weryfikator cytatów — porównanie znak po znaku, bez sędziego LLM
  (ADR-0006).
- Deterministyczny silnik terminów (ADR-0005) — zaimplementowany
  i przetestowany, **niepodpięty do panelu**.
- Rozpoznawanie języka dokumentu i dobór modelu per język.
- Log audytowy z łańcuchem sum kontrolnych.
- Fork OpenContracts z patchami 01–03: −14 726 linii kodu MCP
  i discovery.

### Zmierzone
- 320 orzeczeń SAOS (16,3 mln znaków) i 402 dokumenty sprawy Lacey
  (9,1 mln znaków) — analiza pytania w ~265 s i ~283 s.
- Liczba wywołań modelu nie rośnie z rozmiarem akt (BM25 wybiera 12).
- Surowa trafność cytatów: 82% na korpusie polskim, 9% na angielskim
  przed dobraniem modelu do języka.
- Testy: 163 zaliczone, 2 czerwone (nieprzypięte obrazy, wyłączony
  Docker), 88 pominiętych.

### Znane ograniczenia
- Brak kont i profili — panel nasłuchuje tylko na 127.0.0.1.
- Log audytowy nie zapisuje osoby (wymaganie F-33 niespełnione).
- Brak wgrywania plików i OCR — treść wkleja się tekstem.
- Profil Q4 na 8 GB VRAM **niedopuszczony do rzeczywistych akt**
  (`docs/06-stos-ai.md`, DPIA warunek 2).
