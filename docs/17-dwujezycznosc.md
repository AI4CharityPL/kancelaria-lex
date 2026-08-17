# 17 — Dwujęzyczność: rozpoznanie języka i dobór silnika

Każdy wgrywany dokument dostaje automatycznie rozpoznany język, a etap mapowania jest kierowany do modelu właściwego dla tego języka.

---

## Rozpoznanie języka — dlaczego nie modelem

Rozpoznanie polski/angielski jest zadaniem rozstrzygniętym i deterministycznym. Model kosztowałby sekundy na dokument (przy 400 dokumentach — kilkanaście minut), zajmowałby VRAM i bywałby niepewny. Liczenie słów funkcyjnych i znaków diakrytycznych daje odpowiedź w mikrosekundach, zawsze tak samo, bez GPU.

To ta sama zasada, co przy terminach procesowych (ADR-0005): **tam, gdzie wystarczy reguła, model jest gorszym narzędziem.**

Dla przypadków granicznych (dokument bardzo krótki, mieszany, sam tabelaryczny) wynik to `nieznany` z podaną pewnością — decyzję podejmuje warstwa wyżej. Zapasowo przyjmowany jest polski, bo instalacja jest polska.

Sygnały: znaki diakrytyczne `ąćęłńóśźż` (obecność niemal rozstrzygająca, brak nie dowodzi niczego — skany po OCR gubią ogonki) oraz częstość słów funkcyjnych i terminów procesowych obu języków.

### Skuteczność na realnych aktach

| Korpus | Dokumentów | Rozpoznanie | Średnia pewność |
|---|---|---|---|
| USA v. Lacey (PDF, angielski) | 402 | **397 en**, 4 pl, 1 nieznany | 0,87 |
| Orzeczenia SAOS (polski) | 320 | **320 pl** | 0,99 |
| Korpus syntetyczny | 3 | 3 pl | 0,99 |

98,8% na angielskim, 100% na polskim. Język rozpoznawany jest **raz, przy wgraniu**, i zapisywany w bazie — nie liczy się go przy każdej analizie.

---

## Dobór silnika

| Język | Model | Uzasadnienie |
|---|---|---|
| polski | `bielik-lex-map` (Bielik-minitron-7B Q4) | Trenowany pod polski; 38 tok/s, mieści się w całości w VRAM |
| angielski | `llama-lex-map` (Llama 3.1 8B Q4) | W przeglądzie rynku wskazywana jako najpewniejsza przy wymogu ścisłego schematu JSON; dobra na terminologii prawniczej |

Dokumenty są **grupowane po języku przed mapowaniem**. To nie kosmetyka: przy 8 GB VRAM mieści się jeden model naraz, więc każda zmiana języka to wyładowanie jednego i wczytanie drugiego. Grupowanie ogranicza to do jednej zamiany zamiast kilkunastu.

Szablon promptu też jest dobierany do języka — angielski dokument dostaje instrukcję po angielsku.

---

## Co naprawdę psuło cytaty z PDF-ów

Pierwsza diagnoza brzmiała: „model polski parafrazuje angielski tekst". Była **niepełna**.

Wszystkie odrzucenia miały powód `zakres 0-0` — fragment **nie został w ogóle odnaleziony** w źródle. Przyczyna leżała w moim kodzie: offsety wyznaczało zwykłe `zrodlo.find(fragment)`, czyli dokładne dopasowanie ciągu.

Tekst wyciągnięty z PDF wygląda tak:

```
Attorney for Defendant: Paul Cambria, \nRetained \nDefendant: ☒ Present ☐ Not Present
```

Łamania wierszy w środku zdań, znaki układu strony. Model cytuje zdanie tak, jak je czyta — a `find()` nie znajdował dokładnego ciągu i **poprawny cytat przepadał**.

Weryfikator miał tolerancję na białe znaki od początku. Nigdy nie dostawał szansy jej użyć: odsiew następował o krok wcześniej.

**Poprawka:** `znajdz_fragment()` szuka z tą samą normalizacją, której używa weryfikator, i mapuje pozycje z powrotem na oryginał — cytat wskazuje prawdziwe miejsce w dokumencie, nie w przetworzonej kopii. Granice tolerancji nie ruszone: zmieniona liczba, usunięta negacja czy parafraza nadal przepadają (`tests/test_znajdz_fragment.py`).

---

## Wyniki — udział obu poprawek

Akta USA v. Lacey, 402 dokumenty z PDF-ów, to samo pytanie:

| Konfiguracja | Ustaleń | Odrzuconych | Trafność |
|---|---|---|---|
| Bielik (polski) + dokładne `find()` | 6 | 62 | 9% |
| Llama (angielski) + dokładne `find()` | 14 | 133 | 10% |
| **Llama + szukanie tolerancyjne** | **111** | **38** | **74%** |

Korpus polski, 320 orzeczeń (czysty tekst z API, nie z PDF):

| Konfiguracja | Ustaleń | Odrzuconych | Trafność |
|---|---|---|---|
| Bielik + dokładne `find()` | 28 | 6 | 82% |
| Bielik + szukanie tolerancyjne | 29 | 7 | 81% |

**Interpretacja.** Polski nie zmienił się, bo pochodzi z czystego tekstu — nie miał czego naprawiać. Angielski skoczył 8×, bo pochodzi z PDF-ów. Główną przyczyną był więc **sposób wyciągania tekstu, nie język** — choć dobór modelu też pomógł (6 → 14 ustaleń jeszcze przed poprawką szukania).

Wniosek na przyszłość: przy ocenie jakości modelu trzeba najpierw wykluczyć, że problem leży w przygotowaniu danych. Inaczej wymienia się model, gdy zawodzi parser.

---

## Czasy

| Korpus | Dokumentów | Czas analizy |
|---|---|---|
| Polski (SAOS) | 320 | 261 s |
| Angielski (Lacey) | 402 | 414 s |

Llama 3.1 8B jest wolniejsza od Bielika-minitron (większy model, ciaśniej w VRAM), stąd dłuższy czas przy podobnej liczbie dokumentów.

---

## Konfiguracja

`panel/jezyk.py` — słownik `MODELE`; `panel/analiza.py` — `MODEL_SYNTEZY`.

Modelfile'e: `models/Modelfile.bielik-map`, `models/Modelfile.llama-map`.

```bash
ollama create bielik-lex-map -f models/Modelfile.bielik-map
```

```bash
ollama create llama-lex-map -f models/Modelfile.llama-map
```
