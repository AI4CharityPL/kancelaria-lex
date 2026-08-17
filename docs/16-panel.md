# 16 — Panel spraw sądowych

```bash
python panel/serwer.py
```

Adres: **http://127.0.0.1:8713** · dwa okna: **Sprawy** i **Przepisy prawne**

---

## Głęboka analiza — pipeline wieloetapowy

Pierwsza wersja panelu wrzucała całą treść sprawy do jednego zapytania i zwracała jedno zdanie z cytatem. To była wyszukiwarka, nie analiza — i przy większej liczbie dokumentów w ogóle się nie mieściła w kontekście.

Obecny przebieg:

```
  1. DEKOMPOZYCJA      model rozbija pytanie na 2–4 wątki analityczne
  2. WYBÓR DOKUMENTÓW  BM25 wskazuje, które dokumenty w ogóle warto czytać
  3. MAPOWANIE         osobne wywołanie NA KAŻDY trafny dokument —
                       wydobycie faktów z cytatami
  4. PRZEPISY          retrieval po korpusie przepisów (odrębna przestrzeń)
  5. SYNTEZA           wnioski · rozbieżności · luki · podstawa prawna
  6. WERYFIKACJA       mechaniczne sprawdzenie każdego cytatu wobec źródła
```

Wynik zawiera: **ustalenia** (numerowane, z cytatami) · **wnioski** (ze wskazaniem, z których ustaleń wynikają) · **rozbieżności** · **luki w aktach** · **podstawę prawną** · **odrzucone** twierdzenia.

### Zakotwiczenie wniosków

Ustalenie faktyczne **musi** mieć zweryfikowany cytat. Wniosek cytatu nie ma — bo jest rozumowaniem, nie faktem. Zamiast tego wskazuje **numery ustaleń**, z których wynika.

Wniosek oparty na ustaleniu, które przepadło na weryfikacji, jest odrzucany razem z nim. Rozumowanie staje się śledzalne do zdania w aktach — co częściowo domyka ograniczenie zapisane wprost w ADR-0006 (weryfikacja cytatu nie potwierdza trafności wniosku).

---

## Skalowanie do stu dokumentów

**Liczba wywołań modelu nie rośnie z rozmiarem akt.** BM25 wybiera do 12 najtrafniejszych dokumentów (`MAKS_DOKUMENTOW_DO_ANALIZY`), więc sprawa na 100 dokumentów kosztuje tyle samo co sprawa na 15 — reszta jest pomijana jako nietrafna, a panel pokazuje ile.

Mechanika: dokumenty dzielone na fragmenty ~1400 znaków z zakładką, **z zachowaniem offsetów w oryginale**. Ranking BM25 z obsługą polskiej fleksji. Do modelu trafiają tylko trafne fragmenty, w ramach budżetu kontekstu.

Offsety są tu warunkiem poprawności: weryfikator porównuje zakres znaków z treścią dokumentu **źródłowego**. Gdyby fragmenty miały własną numerację, każdy cytat trafiałby w próżnię.

### Pomiar rzeczywisty (profil rozwojowy, Q4, 8 GB VRAM)

| Zakres | Czas |
|---|---|
| 2 dokumenty (dekompozycja + 2 mapowania + synteza) | **545 s** |
| Szacunkowo pełne 12 dokumentów | ~15–25 min |

To jest wolne i takie zostanie na tym sprzęcie — jedno wywołanie modelu to 40–90 s. Profil produkcyjny (Q8, GPU 24–48 GB) skraca to wielokrotnie. Panel pokazuje postęp etapami, więc widać, na którym dokumencie stoi praca.

---

## Przepisy prawne — odrębne okno, odrębna przestrzeń cytatów

Przepisy **nie należą do żadnej sprawy**. Są jawne i wspólne, więc trzymanie ich razem z aktami mieszałoby materiał objęty tajemnicą z tekstem z dziennika ustaw.

Powód ważniejszy: **rozdzielenie przestrzeni cytatów**. Ustalenie faktyczne cytuje akta, podstawa prawna cytuje przepis. Gdyby oba żyły w jednym zbiorze, model mógłby „potwierdzić" zdanie o prawie protokołem przesłuchania, a weryfikator by to przepuścił — cytat formalnie istniałby w zbiorze.

Weryfikator ustaleń nie widzi przepisów; weryfikator podstawy prawnej nie widzi akt. Pomyłka jest niemożliwa konstrukcyjnie, nie „niedozwolona".

⚠️ **Treści przepisów wprowadza kancelaria z oficjalnego źródła.** System celowo nie zawiera żadnego tekstu ustawy — narzędzie do zwalczania halucynacji nie może startować z przepisami odtworzonymi z pamięci modelu. Pola `zrodlo` i `zweryfikowal` służą do odnotowania pochodzenia; przepis bez weryfikacji jest oznaczony w interfejsie.

---

## Zamknięcie zakresu w obrębie sprawy

Warunek postawiony na początku: dokumenty i dane trafiają wyłącznie do wybranej sprawy, a pamięć rozmowy jest zamknięta w jej obrębie.

```
  wybór sprawy → baza.tresci_dokumentow(sprawa_id [, dokument_id])
                       ← JEDYNE wejście do treści akt w panelu
                 ┌─────────────┴─────────────┐
          kontekst dla modelu        zbiór dla weryfikatora
                 (ten sam zawężony słownik)
```

Wzmocnienia w warstwie danych: nie istnieje funkcja zwracająca dokumenty lub wiadomości bez `sprawa_id` · `pobierz_dokument` wymaga zgodności sprawy — dokument z innej sprawy jest nieodróżnialny od nieistniejącego · `dodaj_dokument` odrzuca nieistniejącą sprawę · wątek dokumentu jest odrębny od wątku sprawy.

**Weryfikacja na żywym modelu** (dwie sprawy w jednej instalacji, pytania zadane w „II K 147/26"):

| Pytanie | Wynik |
|---|---|
| Fakt obecny **wyłącznie w drugiej sprawie** (przyznanie się) | ✓ odmowa |
| Numer rejestracyjny — **wyłącznie w drugiej sprawie** | ✓ odmowa |
| Fakt z tej sprawy | ✓ odpowiedź z cytatami |

Dowód w kodzie: `tests/test_panel_izolacja_spraw.py` (13 testów).

---

## Dwie pułapki, które kosztowały ten pipeline

Warte zapisania, bo obie dawały **ciche zero** zamiast błędu.

**1. Etap mapowania nie może odpowiadać na pytanie.** Pierwszy szablon brzmiał „wypisz ustalenia istotne dla pytania", a pytaniem było „czy zeznania świadków są spójne?". Model dostawał jeden protokół i słusznie zwracał pustą listę — pojedyncze zeznanie nie mówi nic o spójności *między* świadkami. Analiza kończyła się zerem ustaleń przy dokumentach pełnych faktów.

Mapowanie ma **wydobywać fakty**. Porównanie należy do syntezy, która widzi wszystkie dokumenty naraz. Po przeformułowaniu: z tych samych dwóch protokołów wyszło **11 ustaleń** zamiast zera.

**2. Model pisze po polsku.** Szablon prosił o klucz `"watki"`, model zwracał `"wątki"`. Sztywny odczyt dawał pustą listę bez śladu błędu. Parsowanie normalizuje teraz nazwy kluczy (bez ogonków, casefold, spacje i myślniki na podkreślenie) i przyjmuje warianty nazw pól.

Przy okazji: **NFD nie rozkłada `ł`** — to odrębna litera, nie `l` ze znakiem diakrytycznym. Bez jawnej podmiany połowa polskich form czasownikowych trafiała na inne rdzenie. Testy: `tests/test_analiza_parsowanie.py`, `tests/test_wyszukiwarka.py`.

---

## Czego panel nadal NIE ma

| Brak | Konsekwencja |
|---|---|
| **Logowania i kont** | Nasłuch wyłącznie na `127.0.0.1`. Udostępnienie w LAN wymaga reverse proxy z TLS z własnego CA i uwierzytelnianiem |
| OCR i wgrywania plików | Treść wkleja się tekstem; OCR wchodzi z pełnym stosem (Docling + Tesseract) |
| Wyszukiwania wektorowego | Jest BM25; miejsce na hybrydę przygotowane (`polacz_rankingi`, RRF) — ADR-0004 |
| Ścian etycznych | Model danych je przewiduje; egzekwowanie wymaga warstwy kont |
| Odrębnego klucza materiału obrończego | Znacznik widoczny, ale odrębny magazyn i klucz to Faza 5 (wymaganie T-1) |
| Silnika terminów w interfejsie | Zaimplementowany i przetestowany, niepodpięty do panelu |

**Panel działa na profilu rozwojowym.** Warunki dopuszczenia do rzeczywistych akt bez zmian — [`09-compliance/rodo-dpia.md`](09-compliance/rodo-dpia.md).

---

## Interfejs programistyczny

| Metoda | Ścieżka | Działanie |
|---|---|---|
| GET/POST | `/api/sprawy` | Lista spraw · nowa sprawa |
| GET/POST | `/api/sprawy/{id}/dokumenty` | Dokumenty sprawy · dodanie |
| GET/DELETE | `/api/sprawy/{id}/dokumenty/{did}` | Treść · usunięcie (wymaga zgodności sprawy) |
| **POST** | **`/api/sprawy/{id}/analiza`** | **Uruchamia analizę, zwraca `zadanie_id` (202)** |
| **GET** | **`/api/zadania/{zadanie_id}`** | **Postęp: etap, zrobione/wszystkie, wynik** |
| GET/POST | `/api/czat`, `/api/sprawy/{id}/czat` | Historia wątku · szybkie pytanie |
| GET/POST/DELETE | `/api/przepisy[/{id}]` | Korpus przepisów |
| GET | `/api/audyt` | Wpisy + stan łańcucha sum kontrolnych |

Analiza jest **zadaniem w tle** — POST wraca natychmiast, panel odpytuje o postęp. Wcześniej żądanie szło synchronicznie i przycisk gasł na minutę bez żadnej informacji; nie dało się odróżnić pracy od zawieszenia.

## Zależności

**Wyłącznie biblioteka standardowa Pythona.** BM25 i tokenizacja napisane od zera — żadnych nowych pakietów w łańcuchu dostaw (art. 21 ust. 2 lit. d ustawy o KSC). Wymaga Ollamy z modelem `bielik-lex-dev`.
