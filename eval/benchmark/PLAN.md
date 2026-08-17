# Plan rozbudowy benchmarku / Benchmark roadmap

Stan: **wymiary 1–4 działają**, 5–12 zaplanowane.
Status: **dimensions 1–4 implemented**, 5–12 planned.

Każdy wymiar ma podaną miarę, sposób wyznaczenia prawdy wzorcowej i to,
co konkretnie psuje się, gdy wymiaru się nie mierzy.

---

## Działa / Implemented

| # | Wymiar | Miara | Prawda wzorcowa |
|---|---|---|---|
| 1 | **Wierność cytatu** | trafność zakotwiczona, pokrycie wzorca | zakres znaków w źródle |
| 2 | **Odmowa przy braku pokrycia** | J-3 | bliźniak sprawdzony wyszukiwaniem |
| 3 | **Rozróżnialność par** | miara naczelna | para dopasowana |
| 4 | **Szczelność między sprawami** | próg zerowy | kotwica obecna w A, nieobecna w B |

---

## Zaplanowane / Planned

### 5. Krzywa degradacji przy szumie OCR

Moduł `szum.py` jest gotowy — brakuje spięcia z przebiegiem.

Ten sam zbiór par, źródło zaszumione na poziomach CER **0 · 1 · 3 · 5 · 10%**,
realistycznymi klasami pomyłek (utrata ogonków, zlewanie glifów, mylenie
cyfr z literami). Wynikiem jest krzywa, nie punkt.

**Po co:** bramki N-14 i N-15 stawiają progi CER, ale próg CER nie mówi,
ile jakości traci system. Kancelaria kupująca skaner musi wiedzieć, czy
różnica 2% a 5% CER kosztuje 3% czy 40% trafności.

**Osobno raportowana klasa „cyfrowe":** w piśmie procesowym `II K 147/26`
i `II K l47/26` to dwie różne sprawy, a `14 dni` i `l4 dni` to różnica
między zachowanym a utraconym terminem. Pomyłka cyfrowa zmienia sens,
nie pisownię, więc uśrednianie jej z resztą zaciera to, co najważniejsze.

### 6. Igła w stogu siana — pozycja i rozmiar korpusu

Ten sam fakt zadawany przy korpusie 10 · 50 · 100 · 320 dokumentów.
Miara: czy dokument źródłowy trafia do dwunastki wybranej przez BM25
(`recall@12`), rozbite według pozycji dokumentu i głębokości faktu.

**Po co:** `MAKS_DOKUMENTOW_DO_ANALIZY = 12` jest twardym odcięciem.
Nie wiemy, ile ustaleń przepada, bo dokument nie wszedł do dwunastki —
a to jest strata niewidoczna dla użytkownika: system nie mówi „nie
przeczytałem", tylko „nie znalazłem".

### 7. Determinizm

Ten sam przypadek N razy przy `temperature=0.1` i ustalonym `seed`.
Miary: rozrzut liczby ustaleń, stabilność zakresu cytatu, udział
przypadków dających identyczny wynik.

**Po co:** wynik niepowtarzalny nie nadaje się na dowód należytej
staranności (T-4). Prawnik, który dwa razy zada to samo pytanie
i dostanie dwie różne odpowiedzi, przestanie ufać obu.

### 8. Parytet językowy — pełny

Częściowo działa (rozbicie PL/EN w raporcie). Do dołożenia: te same
**przetłumaczone** pytania na dwujęzycznej parze dokumentów, żeby
oddzielić trudność korpusu od zdolności modelu.

**Po co:** rozjazd językowy jest tu zjawiskiem zmierzonym, nie
hipotetycznym — model polski na angielskich aktach parafrazował i dał
9% trafności wobec 82% na polskich.

### 9. Macierz modeli

Ten sam zbiór przypadków × {bielik-lex-map, bielik-lex-dev, llama-lex-map,
qwen2.5-7b} × {szablon wydobywający, odpowiadający}.

**Po co:** ablacja z 14.08.2026 pokazała, że tor szybki chodził na
najgorszej z czterech kombinacji — zero ustaleń tam, gdzie każda inna
dawała 6–8. Taka pomyłka nie ma prawa przeżyć w konfiguracji dłużej
niż jeden przebieg.

### 10. Odporność na wstrzyknięcia — ilościowo

`tests/injection/` sprawdza konstrukcję (agent nie ma narzędzi sieciowych).
Brakuje pomiaru: polecenia wstrzyknięte w treść akt, wariantowane
(jawne, biała czcionka, metadane PDF, warstwa pod obrazem, podszycie
pod komunikat systemowy), na obu językach.

**Próg 100%** — jak w `docs/11-testy-i-bramki.md`.

### 11. Koszt kontekstu — ile zjadają znaczniki

Zmierzone: **42,5% treści sprawy 3 to znaczniki HTML** (`<p>`, `<td colspan>`,
`<span class="anon-block">`). Przy budżecie 9 000 znaków na mapowanie
oznacza to ~3 800 znaków znaczników zamiast treści akt.

Do zrobienia: ten sam przebieg na korpusie surowym i oczyszczonym,
różnica w trafności jako liczba.

**Po co:** to jest wada ścieżki wgrywania dokumentu, a nie modelu.
Naprawa jest tania (oczyszczenie przy imporcie), więc warto wiedzieć,
ile jest warta.

### 12. Regresja między wydaniami

Porównanie przebiegów po identyfikatorach przypadków: które konkretnie
przypadki przestały działać po zmianie. Nie sam spadek średniej —
lista pozycji.

**Po co:** degradacja jakości jest cicha, w przeciwieństwie do awarii
(`docs/11-testy-i-bramki.md`). Średnia potrafi stać w miejscu, gdy
system psuje jedną kategorię i poprawia drugą.

---

## Uwaga metodologiczna

Ten benchmark mierzy **wierność cytatu i odmowę** — nie mierzy poprawności
merytorycznej. Do tego służy gold set weryfikowany przez człowieka
(`eval/gold-set/`, bramka J-2, próg ≥ 85%).

Rozdzielenie jest celowe. Wierność cytatu jest własnością binarną
i mierzalną maszynowo na tysiącach przypadków. Poprawność merytoryczna
jest oceną prawniczą i nie da się jej zautomatyzować bez sędziego LLM,
którego ten projekt świadomie odrzuca.

**Benchmark, który udaje, że mierzy jedno i drugie, mierzy naprawdę
tylko to pierwsze — i myli użytkownika co do tego, czego dowiódł.**
