# 20 — Droga do produktu enterprise

> **Dokument planistyczny.** Opisuje, co dzieli obecny stan od systemu,
> który kancelaria może wdrożyć do pracy na rzeczywistych aktach.
> Wszystkie liczby pochodzą z pomiarów, nie z oszacowań — źródło podane
> przy każdej. Stan na 15.08.2026.

---

## 0. Zasada tego dokumentu

Każda pozycja ma podane: **co**, **z czym się łączy**, **jak sprawdzić,
że działa**. Pozycja bez sprawdzalnego kryterium jest życzeniem, nie
zadaniem.

Trzy tygodnie prac nad tym systemem nauczyły jednej rzeczy dobitnie:
**deklaracja, że coś działa, nie jest dowodem, że działa.** W tej sesji
cztery kolejne poprawki miały sensowne uzasadnienie i nie zmieniły ani
jednej cyfry w pomiarze. Dlatego plan poniżej jest zbudowany wokół bramek,
a nie wokół listy funkcji.

---

## 1. Stan faktyczny — co jest zmierzone

### 1.1 Działa i jest zmierzone

| Obszar | Stan | Dowód |
|---|---|---|
| Cytowanie po numerze zdania | działa | ADR-0007; gramatyka `enum` wymusza numer ze zbioru pokazanych zdań |
| Weryfikacja cytatu znak po znaku | działa | `weryfikator_cytatow.py`, 17 testów |
| Zamknięcie w obrębie sprawy | działa | `test_panel_izolacja_spraw.py`, 13 testów |
| Odporność na wstrzyknięcia | 100% | `tests/injection/`, 15 testów konstrukcyjnych |
| Silnik terminów | działa, **niepodpięty** | 14 testów, zero użycia w panelu |
| Analiza map-reduce (tor głęboki) | działa | 320 orzeczeń / 16,3 mln znaków w ~265 s |
| Benchmark v2 z przypisaniem etapu | działa | `eval/benchmark/v2.py` |
| Dziennik kontroli bez treści akt | działa | `test_dziennik.py`, 10 testów |
| Testy jednostkowe | **318 zielonych** | `pytest -m "not behawioralny"` |

### 1.2 Jakość odpowiedzi — liczby, nie wrażenia

Pomiar v2, `--par 25`, ziarno 42, pełny korpus (320 orzeczeń SAOS +
402 dokumenty USA v. Lacey):

| Miara | Wartość | Uwaga |
|---|---:|---|
| Trafność | **68,0%** | cytat trafia w jedno z prawdziwych wystąpień |
| Recall retrievalu | **90,0%** | zdanie wzorcowe dociera do modelu |
| Średnio wystąpień kotwicy | 5,9 | v1 znał jedno i karał za resztę |
| Fałszywe odmowy | 16 z 50 | dominowało `zakotwiczenie` (9) |

**Luka 22 punktów między recallem a trafnością** to strata po retrievalu:
zdanie dociera do modelu, a nie zamienia się w cytat.

### 1.3 Zmierzone przyczyny strat

| Przyczyna | Pomiar | Status |
|---|---|---|
| „Lost in the middle" — 12 dokumentów w jednym wywołaniu | 12 dok. → **2/9**, 1 dok. → **8/9** | naprawione kaskadą |
| Eskalacja przy pytaniach bez pokrycia | odmowy 141–350 s | naprawione bramką wyróżnika (→ 10–24 s) |
| HTML w aktach sprawy 3 | **42,5% treści to znaczniki** | **otwarte** |
| Kontrola wsparcia | kosztowała 6,2 pkt trafności | wyłączona, czeka na zbiór do oceny |

### 1.4 Czego nie ma wcale

| Brak | Wymaganie | Konsekwencja |
|---|---|---|
| Konta, logowanie, role | F-30, F-36 | panel wyłącznie na `127.0.0.1`, praca jednoosobowa |
| Osoba w logu audytowym | **F-33** | log nie jest dowodem należytej staranności (T-4) |
| Wgrywanie plików i OCR | F-01…F-03 | treść wkleja się ręcznie; **11% akt Lacey to skany** |
| Terminy w interfejsie | F-21…F-24 | silnik gotowy i nieużywany |
| Ściany etyczne | F-32 | konflikt interesów niewykrywalny |
| Odrębny klucz materiału obrończego | T-1, T-2 | flaga w bazie zamiast szyfrowania |
| Eksport do pisma procesowego | F-35 | prawnik przepisuje ręcznie |
| Kopie zapasowe i odtworzenie | `10-operacje/backup-i-dr.md` | brak procedury wykonalnej |
| Przypięcie obrazów po `sha256` | **I-8** | jedyna czerwona bramka niezwiązana z Dockerem |

---

## 2. Definicja gotowości — co znaczy „enterprise"

System jest gotowy, gdy **wszystkie poniższe są prawdziwe jednocześnie**.
Nie „większość", nie „w zasadzie".

### 2.1 Bramki jakościowe

| Bramka | Próg | Dziś |
|---|---|---:|
| J-1 wierność cytatu | ≥ 99% | ~100% (numer zdania) |
| J-2 poprawność merytoryczna | ≥ 85% na gold secie | **niemierzone** — gold set ma 6 pytań |
| J-3 odmowa przy braku pokrycia | ≥ 90% | 87,5% ❌ |
| J-4 odmowa fałszywa | ≤ 10% | 12,5% ❌ |
| Trafność zakotwiczona | ≥ 85% | 68,0% ❌ |
| Przeciek między sprawami | **0** | 0 |

### 2.2 Bramki izolacji

Wszystkie I-1…I-9 zielone, w tym **I-8** (obrazy po `sha256`) i **O-1**
(przechwycenie ruchu: zero pakietów wychodzących w pełnym cyklu).

### 2.3 Bramki zgodności

| | Termin |
|---|---|
| K-1 ocena podmiotowa KSC | **15.09.2026** |
| K-2 rejestracja KSC | **02.10.2026** |
| DPIA zatwierdzona przez IOD | przed pierwszymi rzeczywistymi aktami |
| Reguły terminów zatwierdzone przez prawnika | przed włączeniem terminów |

⚠️ **K-1 i K-2 nie zależą od kodu i nie czekają na nic.** To jedyne
pozycje w tym dokumencie z terminem ustawowym.

### 2.4 Bramki operacyjne

- Odtworzenie z kopii zapasowej wykonane i **udokumentowane czasem**
- Runbook incydentu przećwiczony, nie tylko napisany
- Zapewnione utrzymanie: kilka–kilkanaście godzin miesięcznie
  (`12-sprzet-i-koszty.md`)

---

## 3. Architektura docelowa — co z czym się łączy

```
┌─ WEJŚCIE ─────────────────────────────────────────────────────────┐
│  skan/PDF/DOCX ─► pliki.py ─► ocr.py ─► oczyszczanie.py            │
│                                  │                                  │
│                          BRAMKA LUDZKA: podgląd i korekta OCR      │
│                                  ▼                                  │
│                            baza.dodaj_dokument                      │
│                            (język, hash, materiał obrończy?)        │
└─────────────────────────────┬──────────────────────────────────────┘
                              ▼
┌─ WYSZUKIWANIE ────────────────────────────────────────────────────┐
│  wyszukiwarka.dokumenty_trafne   ← BM25 po dokumentach            │
│  wyszukiwarka.wybierz_zdania     ← BM25 po zdaniach, język per dok │
│  zdania.podziel_na_zdania        ← offsety w ORYGINALE             │
└─────────────────────────────┬──────────────────────────────────────┘
                              ▼
┌─ GENERACJA ───────────────────────────────────────────────────────┐
│  KASKADA:  4 dokumenty ─► brak zakotwiczenia? ─► po 1 dokumencie   │
│            (bramka: czy wyróżnik w ogóle jest w aktach)            │
│  schematy.py ─► gramatyka enum ─► model wskazuje NUMER zdania      │
└─────────────────────────────┬──────────────────────────────────────┘
                              ▼
┌─ KONTROLA (6 warstw) ─────────────────────────────────────────────┐
│  1. weryfikator_cytatow   cytat istnieje znak w znak    darmowa    │
│  2. numery zdań           cytat odtwarza KOD            darmowa    │
│  3. wyrozniki             odpowiedź na temat pytania    darmowa    │
│  4. wsparcie              cytat POPIERA twierdzenie     darmowa    │
│  5. kontrola              czyste zapytanie TAK/NIE      ~3 s       │
│  6. glosowanie            samospójność nad numerami     N×         │
└─────────────────────────────┬──────────────────────────────────────┘
                              ▼
┌─ WYJŚCIE ─────────────────────────────────────────────────────────┐
│  odpowiedź + stopień pewności + powód odrzucenia                   │
│  ─► dziennik.py    (liczby i skrót, NIGDY treść)                   │
│  ─► baza.zapisz_audyt (kto, kiedy, co)                             │
│  ─► eksport.py     (DOCX/MD z cytatami, pseudonimizacja)           │
└────────────────────────────────────────────────────────────────────┘
```

### 3.1 Węzły integracji — gdzie systemy się stykają

| Połączenie | Kierunek | Co przepływa | Warunek poprawności |
|---|---|---|---|
| `pliki` → `ocr` → `baza` | jednokierunkowy | tekst + metadane | offsety liczone PO oczyszczeniu, nie przed |
| `konta` → `baza` | przecina wszystko | `uzytkownik_id` | **żadne zapytanie o dokumenty bez niego** |
| `konta` → `audyt` | jednokierunkowy | osoba operacji | materiał sumy kontrolnej wersjonowany |
| `zdania` → `schematy` | jednokierunkowy | numery zdań → `enum` | **muszą pochodzić z tego samego wywołania** |
| `wybor` → `weryfikator` | jednokierunkowy | offsety w oryginale | zbiór dokumentów ten sam po obu stronach |
| `terminy` → `kalendarz` → `skrzynka` | łańcuch | zdarzenie → data → ostrzeżenie | termin niepotwierdzony **nie jest wiążący** |
| `dziennik` → panel IOD | tylko odczyt | liczniki | **zero treści akt** |

⚠️ **Trzy połączenia, na których psuje się cicho:**

1. **`zdania` → `schematy`** — numery muszą pochodzić z tego samego
   wywołania. Rozminięcie zamienia zabezpieczenie w wymuszacz błędu:
   sprawdzone, model wskaże numer nieistniejący, bo tylko taki dozwolony.
2. **`oczyszczanie` → offsety** — oczyszczenie HTML przesuwa wszystkie
   offsety. Dokumenty wgrane przed zmianą mają cytaty w historii, które
   przestaną się zgadzać. Wymaga migracji, nie przełącznika.
3. **`konta` → `audyt`** — dodanie osoby do materiału sumy kontrolnej
   unieważnia łańcuch wstecz. Wersjonowanie wpisu jest warunkiem, nie
   ulepszeniem.

---

## 4. Fazy

Kolejność wynika z zależności, nie z preferencji. Faza E1 blokuje
połowę pozostałych.

### E1 · Tożsamość, role, audyt z osobą

**Dlaczego pierwsze:** bez `uzytkownik_id` nie da się zrobić ścian
etycznych, materiału obrończego, skrzynki ani wiarygodnego audytu.
F-33 jest dziś niespełnione, a T-4 nazywa log dowodem należytej
staranności.

| Zadanie | Łączy się z | Kryterium |
|---|---|---|
| `konta.py` — użytkownicy, `scrypt`, sesje | `baza`, `serwer` | rejestracja → logowanie bez potwierdzenia mailem |
| Trzy role: prawnik · sekretariat · aplikant | wszystkie trasy API | macierz uprawnień w testach, nie w dokumentacji |
| `dostep_do_sprawy` | `baza.tresci_dokumentow` | **żadna funkcja nie zwraca dokumentów bez `uzytkownik_id`** |
| Audyt z osobą + wersjonowanie łańcucha | `baza.zapisz_audyt` | `lancuch_spojny=true` przez granicę migracji |
| WAL + połączenie per wątek | `baza.polacz` | dwie osoby naraz bez „database is locked" |
| Przełączanie profili | `index.html` | zmiana osoby przy jednym komputerze < 5 s |

**Bramka E1:** sprawa prawnika A jest dla prawnika B nieodróżnialna od
nieistniejącej · sekretariat dostaje odmowę na czacie · aplikant nie
potwierdzi terminu · wpis audytu niesie imię i nazwisko.

### E2 · Wejście: pliki, OCR, jakość

**Dlaczego drugie:** dziś treść wkleja się ręcznie, a 11% akt Lacey to
skany bez warstwy tekstowej. To jest praca sekretariatu i największa
dziura funkcjonalna.

| Zadanie | Łączy się z | Kryterium |
|---|---|---|
| `pliki.py` — wgrywanie multipart | `serwer`, `konta` | PDF/DOCX/TXT, limit rozmiaru, typ sprawdzany po zawartości |
| `ocr.py` — Tesseract + `pol.traineddata` | `pliki` | zależność SYSTEMOWA, nie pakiet Pythona |
| Bramka ludzka na korektę OCR | `index.html` | dokument nie wchodzi do indeksu przed akceptacją |
| **Oczyszczanie HTML przy imporcie** | `baza.dodaj_dokument` | zmierzone: 42,5% treści sprawy 3 to znaczniki |
| Filtr jakości zdań w panelu | `zdania.zdanie_uzyteczne` | `n/d` i fragmenty tabel nie trafiają do cytatu |
| CER mierzony na próbce | `eval/` | bramki N-14, N-15 |

⚠️ **Migracja offsetów.** Oczyszczenie zmienia pozycje znaków. Dokumenty
już wgrane mają cytaty zapisane w historii rozmów. Albo migracja
przelicza jedno i drugie, albo oczyszczanie obejmuje wyłącznie nowe
dokumenty — trzeciej możliwości nie ma.

### E3 · Terminy — najwyższy zwrot z gotowej pracy

**Dlaczego:** `SilnikTerminow` jest napisany, przetestowany (14/14)
i **nieużywany**. Przeoczony termin to jedyne miejsce w systemie, gdzie
błąd ma bezpośredni skutek prawny — utratę środka zaskarżenia.

| Zadanie | Łączy się z | Kryterium |
|---|---|---|
| `terminy.py` — spięcie silnika z panelem | `sprawy.silnik_terminow` | pułapka G-030: doręczenie 12.08, nie wydanie 05.08 |
| Rozpoznanie zdarzenia inicjującego | tor szybki | model wskazuje zdarzenie **z cytatem**, nie liczy daty |
| Kalendarz + ostrzeganie z wyprzedzeniem | `skrzynka` | termin **niepotwierdzony** ostrzega głośniej |
| Potwierdzenie przez prawnika | `konta` | rola sekretariatu **nie może** potwierdzić |

**Przepływ przez trzy role:** sekretariat wprowadza doręczenie → model
rozpoznaje zdarzenie → silnik liczy deterministycznie (ADR-0005) →
prawnik potwierdza. Bez ostatniego kroku termin nie jest wiążący.

### E4 · Jakość odpowiedzi do progu bramek

Dziś 68,0% przy progu 85%. Zmierzone kierunki, w kolejności zwrotu:

| Kierunek | Podstawa | Oczekiwanie |
|---|---|---|
| Domknięcie kaskady | 12 dok → 2/9, 1 dok → 8/9 | największy pojedynczy zysk |
| Oczyszczenie HTML | 42,5% wsadu to znaczniki | wolne miejsce w kontekście |
| Gold set do ~150 pytań | dziś 6 | **J-2 dziś niemierzalne** |
| Kontrola wsparcia — ocena | kosztowała 6,2 pkt | wymaga zbioru mierzącego niewierność |
| Hybryda BM25 + wektory | `polacz_rankingi` gotowe, nieużywane | recall 90% → wyżej |

⚠️ **Kontrola wsparcia nie jest odrzucona — jest niezmierzona.** Benchmark
v2 ocenia nachodzenie zakresu i strukturalnie nie potrafi nagrodzić
warstwy, która łapie „prawdziwy cytat, błędne twierdzenie". Potrzebny
zbiór, w którym twierdzenia celowo przeczą prawdziwym cytatom.

### E5 · Praca zespołowa i wyjście

| Zadanie | Łączy się z | Kryterium |
|---|---|---|
| Skrzynka „co się wydarzyło" | `konta`, `terminy`, `zadania` | terminy, ukończone analizy, dokumenty od sekretariatu |
| Trwała kolejka + dwa tory | `zadania.py` | analiza zamówiona wieczorem przeżywa restart |
| `eksport.py` — DOCX/MD z cytatami | `analiza`, `anonimizacja` | cytat z sygnaturą dokumentu i zakresem znaków |
| Pseudonimizacja przed eksportem | F-35 | eksport poza kancelarię bez danych osobowych |
| Ściany etyczne | `dostep`, `konta` | przełamanie wyłącznie decyzją z uzasadnieniem |

### E6 · Materiał obrończy

**Najtrudniejsza pozycja i jedyna, której nie da się zrobić „prawie".**

Art. 178 pkt 1 k.p.k. — tajemnica obrończa **nie podlega uchyleniu**.
T-1 mówi wprost: flagę w bazie zmienia się jednym `UPDATE`, kopia
zapasowa zawiera wszystko niezależnie od flag, zajęcie sprzętu daje
dostęp do całości.

| Zadanie | Kryterium |
|---|---|
| Odrębny magazyn, odrębny klucz | zrzut głównej bazy **nie zawiera** materiału obrończego czytelnie |
| Klucz poza systemem (T-2) | nośnik sprzętowy albo autoryzacja dwuosobowa |
| Procedura wobec żądania organu | **rozstrzyga prawnik kancelarii**, nie inżynier |

### E7 · Operacje

| Zadanie | Kryterium |
|---|---|
| **I-8** — obrazy po `sha256` | `skrypty/pobierz-digesty.sh` + przegląd |
| **O-1** — przechwycenie ruchu | zero pakietów wychodzących w pełnym cyklu |
| Kopie zapasowe + odtworzenie | wykonane, z **udokumentowanym czasem** |
| Runbook incydentu | przećwiczony, nie tylko napisany |
| Szyfrowanie nośnika (N-22) | warunek dla logicznej kontroli dostępu |

### E8 · Zgodność

| | Termin | Zależy od kodu |
|---|---|---|
| K-1 ocena podmiotowa KSC | 15.09.2026 | **nie** |
| K-2 rejestracja KSC | 02.10.2026 | **nie** |
| DPIA + zatwierdzenie IOD | przed rzeczywistymi aktami | nie |
| Ocena AI Act | przed wdrożeniem | nie |
| Szkolenia (KSC + AI Act) | przy wdrożeniu | nie |

---

## 4A · WARSTWA PRODUKTOWA — czym system jest dla prawnika

> Sekcje 1–4 opisują inżynierię. Ta opisuje **produkt**. Bez niej system
> ma dobre bramki i nikt go nie używa.

### 4A.0 Ustalenie, które zmienia priorytety

Badanie asystentów AI w kancelariach wykazało, że **użyteczność
i dopasowanie do kontekstu prawniczego ważą więcej niż surowa trafność
algorytmu**. Kancelarie skracają listę do trzech platform — Harvey (38/50),
CoCounsel (37/50), Legora (35/50) — a różnice w rubryce są mniejsze niż
różnice w tym, jak się z nich korzysta.

**Wniosek dla nas:** trafność 68% w narzędziu, które pokazuje dokładnie,
skąd wziął się każdy cytat, jest w kancelarii warta więcej niż 85%
w narzędziu, które każe wierzyć na słowo. Nie zwalnia to z podnoszenia
trafności — ustawia proporcje.

### 4A.1 Czego brakuje, a jest podstawą codziennej pracy

Dziś panel ma historię rozmowy zapisaną w bazie (`wiadomosci`, z podziałem
na wątek sprawy i wątek dokumentu), ale **nie ma jej w interfejsie**:
nie da się nazwać wątku, wrócić do wczorajszego, ani zobaczyć listy.

Prawnik pracuje sprawą tygodniami. Rozmowa, której nie da się wznowić,
zmusza go do zaczynania od zera przy każdym powrocie.

| Brak | Co to znaczy w praktyce |
|---|---|
| Lista wątków | nie wiadomo, o co już pytano |
| Nazwa wątku | „rozmowa 3" zamiast „rozbieżności w zeznaniach" |
| Wznowienie wątku | powrót po tygodniu = start od zera |
| Wyszukiwanie w historii | „pytałem o to, ale kiedy?" |
| Wątek przypięty do dokumentu | model danych to ma, interfejs nie pokazuje |

### 4A.2 Model danych wątków

```sql
CREATE TABLE watki (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sprawa_id     INTEGER NOT NULL REFERENCES sprawy(id) ON DELETE CASCADE,
    uzytkownik_id INTEGER NOT NULL REFERENCES uzytkownicy(id),
    dokument_id   INTEGER REFERENCES dokumenty(id),   -- NULL = wątek sprawy
    nazwa         TEXT NOT NULL,        -- z pierwszego pytania, edytowalna
    przypiety     INTEGER DEFAULT 0,
    utworzono     TEXT NOT NULL,
    ostatnia_aktywnosc TEXT NOT NULL
);
```

`wiadomosci` dostaje `watek_id`. Migracja: istniejące wiadomości trafiają
do wątku „Rozmowa z <data>" per sprawa i dokument — **żadna nie ginie**.

⚠️ **Wątek należy do użytkownika, nie do sprawy.** Dwóch prawników na tej
samej sprawie ma osobne wątki; wspólny jest materiał, nie rozmowa. To
wynika z F-30 (wiedza konieczna) i z tego, że cudza rozmowa bywa
informacją o strategii procesowej.

### 4A.3 Nawigacja cytatu — przewaga, której konkurencja nie skopiuje

**To jest miejsce, w którym architektura tego systemu daje przewagę
produktową niedostępną dla innych.**

Cytat jest tu **zakresem znaków w dokumencie źródłowym**, zweryfikowanym
maszynowo (ADR-0006, ADR-0007). Nie „źródłem", nie „dokumentem numer 3",
nie „stroną 12” — dokładnym `poczatek:koniec`.

Konkurencja podaje odsyłacz do dokumentu, bo jej cytat nie jest wierny
co do znaku. My możemy:

```
  odpowiedź ──klik na cytat──► dokument otwarty w tym miejscu,
                               fragment PODŚWIETLONY co do znaku
```

To zamienia weryfikację z zadania na odruch. Badania nad UX prawniczym
mówią wprost: interfejs ma **pomagać weryfikować źródła sprawnie**, bo
inaczej prawnik przestaje weryfikować.

Rozwinięcia z tego samego mechanizmu:
- **łańcuch rozumowania klikalny w całości** — wniosek → numery ustaleń
  → cytaty → zakresy w aktach; każde ogniwo prowadzi do miejsca w aktach
- **wyciąg cytatów z wątku** — wszystkie potwierdzone fragmenty w jednym
  widoku, gotowe do pisma

### 4A.4 Pokazywanie odrzuconych — przejrzystość jako funkcja

Panel zbiera dziś powody odrzucenia (`odrzucone` z `powod` i `szczegol`)
i **nie pokazuje ich prawnikowi**.

Konkurencja tego nie robi, bo wygląda źle. Tutaj jest odwrotnie: to jest
dowód, że system pracuje.

```
  ✓ Świadek zeznał, że pojazd był koloru srebrnego.
      [dok. 106, znaki 8580–8976]                    pewność: mocna

  ✗ Świadek rozpoznał kierowcę.
      odrzucone — zdanie mówi, że NIE był w stanie rozpoznać
```

Drugi wiersz jest ważniejszy od pierwszego. Prawnik widzi, że system
**odrzucił twierdzenie, które brzmiało wiarygodnie** — i dopiero to daje
podstawę, by zaufać pierwszemu.

Stopnie pewności pochodzą z warstw kontroli (`wsparcie`, `kontrola`),
które są zbudowane i przetestowane. **Ich wartość jest produktowa, nie
tylko pomiarowa** — pomiar v2 nie potrafi nagrodzić warstwy łapiącej
„prawdziwy cytat, błędne twierdzenie", a prawnik tę informację widzi
i wykorzystuje.

### 4A.5 Ciągłość w czasie — funkcja, której nie ma nikt

`dziennik.py` zapisuje **skrót pytania**. Z tego wynika możliwość, której
nie widziałem w żadnym produkcie tej klasy:

> **„Pytałeś o to 3 tygodnie temu. Wtedy odpowiedź brzmiała inaczej —
> od tamtej pory do sprawy doszły 4 dokumenty."**

W kancelarii akta rosną. Odpowiedź sprzed wpływu opinii biegłego może
być dziś nieaktualna, a prawnik nie ma jak tego zauważyć. System, który
zna skrót pytania i daty dokumentów, ma to za darmo.

Warianty:
- **powtórzone pytanie** — pokaż poprzednią odpowiedź i różnicę
- **wpłynął nowy dokument** — „3 wątki mogą wymagać ponowienia"
- **zmiana modelu** — „odpowiedzi sprzed aktualizacji oznaczone"

Ostatni punkt ma znaczenie zgodnościowe: `models/manifest.md` wymaga
przejścia bramek przy każdej zmianie modelu. Oznaczenie odpowiedzi
wersją modelu czyni to śledzalnym.

### 4A.6 Teczka robocza — od odpowiedzi do pisma

Dziś analiza kończy się na ekranie. Prawnik przepisuje ustalenia ręcznie,
gubiąc po drodze cytaty — czyli to, co system daje najcenniejszego.

```
  wątek ──► zaznacz ustalenia ──► teczka robocza ──► eksport
                                        │
                                        ├─ DOCX z cytatami i sygnaturami
                                        ├─ Markdown do dalszej pracy
                                        └─ pseudonimizacja (F-35)
```

Teczka jest **przekrojem przez wątki**, nie kolejnym wątkiem: prawnik
zbiera ustalenia z pięciu rozmów o tej samej sprawie w jeden materiał
do pisma.

### 4A.7 Zasady interfejsu dla użytkownika nietechnicznego

Odbiorcą jest prawnik, nie inżynier. Sześć reguł, każda z konsekwencją:

**1. Żadnego żargonu modelowego.** Nie „temperatura", „kontekst",
„embedding", „chunk”. Zamiast „num_ctx przekroczony" — „dokument jest
za długi, wskaż fragment".

**2. Liczba dokumentów mówi o czasie i jakości.** `agent.strategia(n)`
liczy to ze zmierzonych wartości:

```
  ☑ 1 dokument      ~5 s    najszybciej i najtrafniej
  ☑ 4 dokumenty    ~13 s
  ☑ 12 dokumentów  ~3 min   zaznaczenie mniejszej liczby
                            da odpowiedź szybciej I TRAFNIEJ
```

Ostatnie zdanie jest **sprzeczne z intuicją użytkownika** i dlatego musi
paść wprost. Zmierzone: 12 dokumentów w jednym wywołaniu → 2/9,
jeden dokument → 8/9. Bez tej informacji prawnik zaznaczy wszystko
„na wszelki wypadek" i dostanie najgorszy możliwy wynik.

**3. Odmowa to odpowiedź, nie awaria.** „W aktach tej sprawy nie ma
podstawy do odpowiedzi" wymaga innej typografii niż błąd połączenia.
Prawnik ma zobaczyć, że system **sprawdził i nie znalazł**.

**4. Postęp z nazwą etapu.** Analiza trwa minuty. „Analizuję dokument
4 z 12: opinia biegłego" mówi więcej niż pasek.

**5. Nic nie ginie po zamknięciu przeglądarki.** Analiza zamówiona
wieczorem czeka rano w skrzynce. Wymaga trwałej kolejki (E5).

**6. Trzy role, trzy różne ekrany startowe.** Sekretariat widzi kolejkę
wgrywania i kalendarz terminów. Prawnik — swoje sprawy i skrzynkę.
Aplikant — sprawy, do których go przypisano. Jeden ekran dla wszystkich
znaczy, że dla nikogo nie jest dobry.

### 4A.8 Zestawienie z rynkiem

| Funkcja | Harvey / CoCounsel / Legora | LQ.AI | Tutaj |
|---|---|---|---|
| Przestrzeń sprawy | ✅ matters / workspace | ✅ projects | ⬜ **E5** |
| Wątki z historią | ✅ | ✅ | ⬜ **4A.2** |
| Cytat → **zakres znaków** | ❌ odsyłacz do dokumentu | częściowo | ✅ **z natury** |
| Pokazane odrzucone | ❌ | ❌ | ⬜ **4A.4** — mamy dane |
| Weryfikacja bez sędziego LLM | ❌ | ❌ etapy 3–4 to sędziowie | ✅ ADR-0006 |
| Opublikowane liczby jakości | ❌ | ❌ brak | ✅ benchmark v2 |
| Powtórzone pytanie w czasie | ❌ | ❌ | ⬜ **4A.5** |
| Praca bez sieci | ❌ | częściowo | ✅ z założenia |
| Polskie akta karne | ❌ | ❌ | ✅ |

**Trzy pozycje, w których jesteśmy jedyni** (cytat co do znaku,
brak sędziego LLM, opublikowane liczby) wynikają z architektury i nie
da się ich dorobić — konkurent musiałby przebudować rdzeń.

**Cztery pozycje, w których jesteśmy w tyle** (przestrzeń, wątki,
odrzucone, ciągłość) to praca interfejsowa na tygodnie, nie na kwartały.

To jest cała teza produktowa: **mamy to, czego nie da się skopiować,
i nie mamy tego, co da się dopisać.**

### 4A.9 Kolejność prac produktowych

| # | Zadanie | Zależy od | Dlaczego tu |
|---|---|---|---|
| P1 | Wątki: lista, nazwa, wznowienie | E1 | bez tego praca sprawą jest niemożliwa |
| P2 | Cytat klikalny → podświetlenie w dokumencie | — | **największa przewaga, dane już są** |
| P3 | Odrzucone + stopnie pewności | E4 | przejrzystość jako dowód rzetelności |
| P4 | Wybór dokumentów z podpowiedzią czasu | — | `agent.strategia` gotowe |
| P5 | Skrzynka „co się wydarzyło" | E1, E5 | praca w różnym czasie |
| P6 | Teczka robocza + eksport | P1 | zamyka drogę do pisma |
| P7 | Ciągłość w czasie | `dziennik` | wyróżnik, którego nie ma nikt |

**P2 przed P3 nie jest przypadkiem.** Klikalny cytat działa na danych,
które system już produkuje — to jest tydzień pracy interfejsowej i
największy skok w postrzeganej wiarygodności.

---

## 5. Macierz zależności — co blokuje co

```
E1 konta ─────┬──► E3 terminy (potwierdzenie przez rolę)
              ├──► E5 skrzynka, ściany etyczne
              ├──► E6 materiał obrończy (autoryzacja)
              └──► audyt z osobą (F-33)

E2 wejście ───┬──► E4 jakość (oczyszczenie = wolny kontekst)
              └──► E3 terminy (data doręczenia ze skanu)

E4 jakość ────────► dopuszczenie do rzeczywistych akt (DPIA)

E7 operacje ──────► wdrożenie produkcyjne

E8 zgodność ──────► NIEZALEŻNE, biegnie równolegle, ma termin ustawowy
```

**Wniosek praktyczny:** E1 i E8 zaczynają się natychmiast i równolegle.
E8 nie wymaga ani jednej linii kodu, a ma jedyne twarde terminy.

---

## 6. Czego ten plan świadomie nie robi

| Odrzucone | Powód |
|---|---|
| Sędzia LLM oceniający wierność | ADR-0006; potwierdzone niezależnie — *„LLM-as-a-Judge is Bad"*, Springer 2026, materiał egzaminu KIO |
| Dostrajanie modelu na aktach | ryzyko utrwalenia danych w wagach; retrieval daje to samo bez tego ryzyka |
| Model chmurowy „do zadań nieczułych" | granica byłaby fikcją — nie ma sposobu zagwarantować, że dane nieczułe nie zawierają czułych |
| Wspólna baza w LAN | użytkownik wybrał instalację per komputer; wyjście do serwera zostaje otwarte i **nie wymaga przepisywania E1** |
| GitHub Actions | repozytorium zawiera model zagrożeń i topologię instancji przetwarzającej akta karne |
| Rozbudowa benchmarku v1 | mierzy wobec jednego wzorca przy 5,9 prawdziwych wystąpieniach — błąd systematyczny, nie szum |

---

## 7. Ryzyka, które trzeba nazwać

| Ryzyko | Skutek | Ograniczenie |
|---|---|---|
| **Q4 na 8 GB VRAM** | DPIA nie dopuszcza do rzeczywistych akt | profil jako przełącznik; zakup GPU niczego nie przepisuje |
| Utrzymanie forka | nieaktualizowany system to ryzyko, nie oszczędność | kilka–kilkanaście h miesięcznie, zapewnione **przed** wdrożeniem |
| Profil chroni przed kolegą, nie przed dyskiem | kontrola logiczna, nie kryptograficzna | pełne szyfrowanie nośnika (N-22) + E6 |
| Instalacja per komputer | brak wspólnych akt między prawnikami | świadomy wybór; wyjście przez serwer w LAN |
| Gold set 6 pytań | **J-2 niemierzalne** | czas prawnika, planować wcześnie |
| Degradacja po zmianie modelu | cicha, w przeciwieństwie do awarii | `dziennik.py` + pełne bramki przy każdej zmianie |

---

## 8. Kolejność startu

Gdyby jutro zaczynać, w tej kolejności:

1. **K-1 ocena podmiotowa KSC** — termin ustawowy, zero kodu
2. **E1 konta i audyt z osobą** — odblokowuje połowę reszty
3. **E2 wejście: pliki i OCR** — praca sekretariatu, 11% akt to skany
4. **E3 terminy** — gotowa praca, najwyższy zwrot, skutek prawny błędu
5. **E4 jakość do progu bramek** — mierzone v2, krótka pętla ~4 min
6. Reszta wg macierzy zależności

**Pozycja 1 przed 2 nie jest pomyłką.** K-1 i K-2 to jedyne rzeczy
w tym dokumencie, których nie da się nadrobić pracą — mają termin
ustawowy i nie zależą od tego, czy kod jest gotowy.
