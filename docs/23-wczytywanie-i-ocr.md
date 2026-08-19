# 23 — Wczytywanie akt i OCR: co zmierzono i na czym

Dokument opisuje, **na jakich danych** i **w jakiej ilości** sprawdzono
ścieżkę wczytywania dokumentów, oraz gdzie leżą jej granice. Powstał
19.08.2026, przed publikacją repozytorium.

> **Zasada nadrzędna tej ścieżki.** Tekst wydobyty z pliku staje się
> **źródłem cytatów**: weryfikator porównuje z nim cytat znak w znak.
> Błędna ekstrakcja rozsypuje więc cały łańcuch gwarancji po cichu —
> cytat przechodzi weryfikację wobec zepsutego źródła. Dlatego każda
> ścieżka kończy się bramką jakości, a **odmowa jest wynikiem poprawnym**.

---

## 1. Korpus pomiarowy

| Cecha | Wartość |
|---|---|
| Liczba plików | **173 PDF-y** |
| Pochodzenie | katalog `Pobrane` maszyny deweloperskiej — dokumenty rzeczywiste, nie syntetyczne |
| Rodzaje | umowy i NDA, listy intencyjne, oferty handlowe, faktury i wydruki księgowe, dokumentacja techniczna, życiorysy, pisma z podpisem odręcznym |
| Języki | polski i angielski, część dokumentów mieszana |
| Zakres wielkości | 35 kB – 9,1 MB |

⚠️ **Te pliki nie znajdują się w repozytorium i nigdy się w nim nie
znajdą.** To dokumenty prywatne i firmowe osoby prowadzącej projekt;
posłużyły wyłącznie jako materiał pomiarowy na maszynie lokalnej.
W repozytorium zostają **same liczby**, zgodnie z wymaganiem T-6.

Korpus jest przypadkowy i to jest jego zaletą: nie został dobrany pod
możliwości parsera. Zawiera dokładnie to, co trafia do kancelarii —
pisma z pieczątką, skany podpisanych umów i wydruki z systemów
księgowych.

---

## 2. Wynik końcowy

| Kategoria | Plików | Udział |
|---|---:|---:|
| **Odczytane z warstwy tekstowej** | **87** | 50,3% |
| **Odczytane przez OCR** | **16** | 9,2% |
| Odrzucone z wyjaśnieniem | 70 | 40,5% |
| **Razem użytecznych** | **103** | **59,5%** |

OCR: **147 stron**, 39 175 znaków, z czego 1 127 to znaki diakrytyczne
(2,9%), czas łączny **2,9 minuty** — około 1,2 s na stronę.

---

## 3. Droga do tego wyniku — trzy usterki, każda zmierzona

Na starcie pomiaru odczytywało się **75 plików ze 173**. Trzy poprawki
podniosły to do 87 na samej warstwie tekstowej.

### 3.1. Filtr obrazów odrzucał tekst całych stron

Warunek `b"/Image" in cialo` szukał ciągu w **całym obiekcie razem ze
skompresowanym strumieniem**. Zamiarem było pominięcie obrazów; skutkiem
— odrzucenie **całego strumienia treści strony**, gdy tylko gdziekolwiek
trafił się ciąg `/Image`. A trafia się zawsze, gdy strona ma logo,
pieczątkę, podpis albo tło.

Pisma procesowe mają nagłówek kancelarii i pieczęć niemal zawsze, więc
usterka trafiała w przypadek **typowy, nie brzegowy**.

Pierwsza poprawka nie zmieniła nic, bo szukała pary `/Subtype` + `/Image`
w słowniku, a ten niesie `/ProcSet [/PDF /Text /ImageB /ImageC]` — czyli
`/Image` jako przedrostek `/ImageB`. Dopiero dopasowanie **pary
`/Subtype /Image`** zadziałało.

### 3.2. Mapy `/ToUnicode` budowane i nieużywane

PDF nie przechowuje tekstu, tylko numery glifów. Dopiero mapa
`/ToUnicode` mówi, co dany glif znaczy. Wiązanie nazwy zasobu (`/F4`)
z mapą szło przez `re.search(rb"/Font\s*<<(.*?)>>")` — a słownik zasobów
jest **zagnieżdżony**, więc `(.*?)>>` zatrzymywał się na pierwszym `>>`,
zwykle nie na właściwym.

Zmierzone na pliku testowym: **10 map zbudowanych, 10 fontów użytych,
zero powiązań**. Każdy znak szedł ścieżką zapasową cp1252 i wychodził
jako przypadkowy bajt. Wiązanie idzie teraz po całym dokumencie.

### 3.3. Każdy operator pozycjonowania łamał wiersz

`Td` traktowany bezwarunkowo jako nowy wiersz dawał tekst rozsypany na
litery — generatory PDF ustawiają pozycję **osobno dla każdego znaku**.
Nowy wiersz jest wtedy i tylko wtedy, gdy zmienia się współrzędna
pionowa.

Przy okazji zmierzono rozkład przesunięć poziomych (3294 próbki, stopień
pisma 12–13):

| kwantyl | 0,10 | 0,50 | 0,75 | 0,97 |
|---|---:|---:|---:|---:|
| przesunięcie | 3,15 | 6,41 | 7,14 | 10,38 |

Odstępy międzyliterowe i międzywyrazowe **nie rozdzielają się progiem** —
rozkład jest jednomodalny, bo ten generator wstawia spacje jako osobne
glify. Dokładanie spacji progiem 1,2 psuło 6053 znaki na 3524 poprawne
(`C o n t a c t` zamiast `Contact`). Próg jest teraz ułamkiem stopnia
pisma i dokłada spację wyłącznie przy skoku wyraźnie większym niż
szerokość znaku.

---

## 4. OCR — konfiguracja i granice

| Element | Stan |
|---|---|
| Silnik | Tesseract 5.4.0, wywoływany jako **osobny proces** |
| Dane językowe | `models/tessdata/` — `pol`, `eng`, `osd`, przypięte sumą `sha256` w [`models/manifest.md`](../models/manifest.md) |
| Zależności Pythona | **zero** — obrazy wydobywane `zlib` i `struct` z biblioteki standardowej |
| Uprawnienia | nie wymaga administratora: `TESSDATA_PREFIX` wskazuje katalog projektu |

### Polski jest wymagany, angielski nie wystarcza

Zmierzone na zdaniu z polskiego postanowienia:

```
pol:  Sąd Okręgowy … oddalił wniosek obrońcy o dopuszczenie
eng:  Sad Okregowy … oddalit wniosek obroncy 0 dopuszezenie
```

Angielski **„działa"** i zwraca tekst wyglądający poprawnie — bez ani
jednego znaku diakrytycznego, z zerem zamiast litery `o` i przekręconym
`dopuszezenie`. Brak polskiego pakietu jest więc **odmową**, nie
zejściem na angielski.

### Czego OCR tutaj nie zrobi

Obrazy są **wydobywane z PDF-a**, nie renderowane. Skan zapisany jako
PDF ma stronę będącą obrazem, więc wystarczy ten obraz wyjąć
(`/DCTDecode` to gotowy JPEG, `/FlateDecode` składamy w PNG). Renderowanie
wymagałoby silnika (poppler, Ghostscript) — kolejnego programu do
przypięcia i pilnowania.

Skutek: **70 plików pozostaje nieodczytanych.** To PDF-y wektorowe
z warstwą tekstową, której nie da się rozszyfrować bez pełnego rozbioru
kodowań PDF-a — nie ma w nich obrazu do rozpoznania. Panel mówi to
wprost zamiast zwracać pusty dokument.

---

## 5. ⚠️ OCR zmienia charakter głównej gwarancji

Obietnica systemu brzmi: *cytat prowadzi do konkretnego znaku w aktach*.
Przy dokumencie z OCR-u prawdziwe zdanie brzmi inaczej:

> cytat prowadzi do konkretnego znaku **w odczycie skanu**

Przykład z pomiaru — nagłówek listu intencyjnego rozpoznany poprawnie
(`dotyczący utworzenia spółki kapitałowej`), ale data z odręcznego
wypełnienia wyszła jako **`4 9.03.2026`**. W kontekście terminu
procesowego to jest różnica między dochowaniem terminu a jego utratą.

Dlatego:

- dokument wczytany przez OCR dostaje **trwały znacznik** `zrodlo_tekstu = "ocr"`
  w bazie, widoczny na liście dokumentów;
- **każdy cytat** z takiego dokumentu niesie znacznik `z OCR` i ostrzeżenie
  „sprawdź przy oryginale, zwłaszcza sygnatury, kwoty i daty";
- znacznik jest wystawiany **bezwarunkowo**, poza przełącznikami kontroli
  wsparcia — ostrzeżenie gasnące przy zmianie niezwiązanego przełącznika
  byłoby gorsze od jego braku;
- OCR **nie włącza się sam**. Jest ostatnią deską po odrzuceniu przez
  bramkę jakości i wymaga kliknięcia „Rozpoznaj pismo".

Pochodzenie tekstu jest śledzone dla **wszystkich** dróg wejścia:
`wklejony` (wprost do panelu), `plik` (TXT, MD, DOCX, RTF, PDF z warstwą
tekstową) oraz `ocr`.

---

## 6. Powtórzenie pomiaru

Pomiar nie jest częścią przebiegu testów — wymaga katalogu z prawdziwymi
PDF-ami, których w repozytorium nie ma i nie będzie. Testy jednostkowe
(`tests/test_ocr.py`, `tests/test_wczytywanie.py`) sprawdzają natomiast
zachowanie na plikach budowanych w kodzie, w tym **odmowę przy braku
polskiego pakietu** i **oznaczanie pochodzenia**.

Żeby powtórzyć pomiar na własnym zbiorze, wskaż katalog i policz
`wczytaj(nazwa, dane)` oraz `wczytaj(nazwa, dane, ocr_dozwolony=True)`
dla każdego pliku — patrz `panel/wczytywanie.py`.
