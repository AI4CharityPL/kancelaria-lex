# 22 — Wyniki zmierzone: najlepsze i docelowe

Zestawienie wszystkiego, co zmierzono do **16.08.2026**. Dokument służy dwóm
rzeczom naraz: pokazaniu, co system potrafi w najlepszym układzie, oraz
zapisaniu, czego jeszcze nie osiąga — bo tabela wyłącznie z dobrymi liczbami
przestaje być pomiarem, a staje się materiałem reklamowym.

> **Jak czytać te liczby.** „Poprawnych łącznie" = trafienia w pytaniach
> z odpowiedzią **plus** słuszne odmowy w pytaniach bez pokrycia. To jedyna
> miara odporna na obie degeneracje: „zawsze odpowiadaj" i „zawsze odmawiaj"
> dostają w niej zero.

---

## 1. Wyniki najlepsze — do czego system jest zdolny

| Miara | Najlepszy zmierzony wynik | Warunki |
|---|---|---|
| **Cytaty niezgodne ze źródłem** | **0** | każdy pomiar, bez wyjątku |
| **Trafność przy jednym dokumencie** | **8 / 8** | sprawa 4, wskazany jeden dokument, ~5 s |
| **Poprawna odmowa (J-3)** | **8 / 8** | ten sam zestaw |
| **Fałszywe odpowiedzi** | **0** | ten sam zestaw |
| **Recall retrievalu** | **96–100%** | zdanie wzorcowe dotarło do modelu |
| **Mediana czasu** | **~5 s** | jeden dokument |
| **Danych wysłanych na zewnątrz** | **0 bajtów** | wszystkie przebiegi |

**Zero w pierwszym wierszu jest tu najważniejsze i nie jest kwestią
szczęścia.** Model wskazuje wyłącznie NUMER zdania, a treść cytatu odtwarza
kod prosto z dokumentu (ADR-0007). Cytat nie jest odrzucany na weryfikacji —
jest **niewyrażalny**. Dla porównania: badanie Uniwersytetu Stanforda wykazało
**17–34% zmyślonych powołań** w wiodących komercyjnych narzędziach prawniczych.

### Zaznacz mniej, dostaniesz więcej

Zmierzone na dziewięciu pytaniach, przy których system wcześniej odmawiał:

| Zaznaczone dokumenty | Trafienia | Średni czas |
|---|---|---|
| **1 dokument** | **8 / 9** ★ | ~5 s |
| 4 dokumenty | 4 / 9 | 13,4 s |
| cała sprawa (12 dok.) | 2 / 9 | 18,7 s |

Czterokrotna różnica trafności przy tym samym modelu. Przyczyną jest
zjawisko „lost in the middle": im więcej materiału niezwiązanego z pytaniem,
tym gorzej model odnajduje właściwe zdanie.

---

## 2. Konfiguracja wysyłkowa i pełne porównanie

Wszystkie warianty zmierzone **jednym przebiegiem** w trybie cienia
(100 przypadków, pełny korpus, 16.08.2026, po naprawie ekstraktora
wyróżników) — różnice między nimi są więc skutkiem warstw, a nie różnicy
warunków:

| Wariant | Trafność | J-3 | Fałszywe odp. | **Poprawnych** |
|---|---:|---:|---:|---:|
| bez kontroli | 80% | 76% | 12 | 78 |
| sama mechanika | 72% | 78% | 11 | 75 |
| **sam kontroler — WYSYŁKA** | **78%** | **82%** | **9** | **80** ★ |
| obie kontrole | 70% | 84% | 8 | 77 |
| NL-do-formatu, bez kontroli | 58% | 86% | 7 | 72 |
| NL-do-formatu, obie kontrole | 48% | 90% | 5 | 69 |

**Wniosek, który widać w każdym wierszu:** J-3 kupuje się wyłącznie za
trafność. Ostatni wiersz osiąga cel 90% i jest jednocześnie najgorszą
konfiguracją — traci połowę poprawnych odpowiedzi. To jest dowód, że problem
leży **przed** generacją, nie po niej.

### ✅ POTWIERDZENIE KOŃCOWE — pełny przebieg 16.08.2026, 21:43

Konfiguracja wysyłkowa, 100 przypadków, **bez cienia** (kontroler odrzuca
naprawdę). To jest raport, na którym stoją bramki.

| Miara | Cień przewidywał | **Pomiar rzeczywisty** |
|---|---:|---:|
| Trafność | 78% | **80,0%** |
| J-3 odmowa poprawna | 82% | **82,0%** |
| Fałszywe odpowiedzi | 9 | **9** |
| Recall retrievalu | — | 96,0% |
| Fałszywe odmowy | — | 4 |
| Błędne odpowiedzi | — | 6 |

**J-3 i liczba fałszywych odpowiedzi zgodne co do jednego.** Metoda cienia —
liczenie obu układów jednym przebiegiem — jest więc wiarygodna i można na
niej opierać kolejne decyzje bez podwójnych przebiegów.

Rozkład etapów: `{odpowiedz: 55, zakotwiczenie: 41, kontrola: 4}`. Cztery
przypadki zatrzymane przez kontroler, z czego dwa słusznie, a dwa kosztowały
poprawną odpowiedź — dokładnie ta wymiana, którą wybrano świadomie.

**Wszystkie bramki jakości: zielone.** Z ostrzeżeniem o niedomkniętym celu
J-3 (90%), które pojawia się przy każdym przebiegu poniżej celu.

### Potwierdzenie pośrednie (60 przypadków)

Cień to wyliczenie kontrfaktyczne, więc konfigurację wysyłkową sprawdzono
osobnym przebiegiem **z kontrolerem włączonym na serio**. Porównanie na
**identycznych 60 przypadkach** (podzbiór powyższych 100):

| | Trafność | J-3 | Fałszywe | Poprawnych |
|---|---:|---:|---:|---:|
| bez kontroli | 73,3% | 70,0% | 9 | 43 |
| **kontroler — pomiar rzeczywisty** | 70,0% | **76,7%** | **7** | **44** |

Kontroler oddaje jedno trafienie i zyskuje dwie słuszne odmowy. **Kierunek
zgodny z przewidywaniem cienia — wybór potwierdzony.**

> ⚠️ Ten sam kod daje 80% trafności na pełnych 100 przypadkach i 73,3% na
> tym 60-elementowym podzbiorze. **Siedem punktów różnicy pochodzi wyłącznie
> z doboru pytań.** Dlatego progi bramek ocenia się teraz wyłącznie na pełnym
> zbiorze (`MIN_PRZYPADKOW = 100`) — porównywanie wyniku z podzbioru
> z progiem kalibrowanym na całości daje fałszywy alarm.

---

## 3. Droga, którą przeszły te liczby

| Data | Zmiana | Trafność | J-3 |
|---|---|---:|---:|
| 14.08 | stan wyjściowy | 76% | 66% |
| 15.08 | naprawy językowe (stopsłowa, model per język) | 82% | 76% |
| 16.08 | naprawa ekstraktora wyróżników | 80% | 76% |
| 16.08 | + kontroler modelem | 78% | **82%** |

**Naprawa ekstraktora wyróżników** była największą pojedynczą poprawą
jakościową, choć w trafności ledwo widoczną. Wzorzec `_OKRES_PL` czytał
„13 stycznia 2025 **roku**" jako czas trwania 2025 lat, tworząc twardy wymóg
nie do spełnienia. Skutek: **2585 fałszywych wyróżników** w samej sprawie 3,
a szkodliwe odrzucenia cytatów spadły po naprawie z **14 na 1**.

---

## 4. Czego system NIE osiąga

Ta sekcja jest równie ważna jak trzy poprzednie.

| Pozycja | Stan | Cel |
|---|---|---|
| **J-3 poprawna odmowa** | **82%** (potwierdzone) | **90%** — nieosiągnięty (RY-16) |
| Fałszywe odpowiedzi | **9** na 50 pytań bez pokrycia | 0 |
| Trafność | **80%** (potwierdzone) | wyżej |
| Luka recall → trafność | 96% vs 80% | 16 punktów do odzyskania |

**Luka 16 punktów jest najciekawszą otwartą pozycją.** Zdanie z odpowiedzią
DOCIERA do modelu w 96 przypadkach na 100, a mimo to w 16 z nich model
wskazuje inne. To nie jest problem wyszukiwania — to problem wyboru.

**Środek zaradczy na J-3 (J2.2, niewdrożony):** ocena odpowiadalności zanim
model zacznie odpowiadać. Podstawa: *Sufficient Context* (ICLR 2025) — RAG
paradoksalnie OBNIŻA skłonność do odmowy, bo dołożony kontekst podnosi
pewność modelu.

### Hipotezy sprawdzone i ODRZUCONE

Zapisane, żeby nikt nie próbował ich po raz drugi bez powodu:

| Hipoteza | Wynik pomiaru |
|---|---|
| NL-do-formatu (arXiv 2408.02442) podniesie trafność | **Odrzucona.** 58% wobec 80%; 17 przypadków bez wskazania żadnego zdania. Gubi krok konwersji, nie krok generowania. |
| Nadgorliwe okresy angielskie psują wynik | **Odrzucona** — okresy są w angielskim 10× rzadsze niż w polskim; winny był wzorzec POLSKI. |
| Kontroler modelem jest bezczynny | **Odrzucona.** Wyglądał tak wyłącznie dlatego, że zepsuty ekstraktor zalewał warstwę mechaniczną fałszywymi odrzuceniami. |
| Rozmiar kontekstu (8192) ogranicza jakość | **Odrzucona** — Llama 3.1 8B ma na RULER 94,6% przy 16K; pracujemy w mocnej strefie. |

### Ścieżki niezbadane

- **q6_k zamiast q4_k_m** — producent modelu ostrzega wprost: „quantised models show reduced response quality and possible hallucinations". Mamy q4, najbardziej agresywny z czterech dostępnych.
- **Bielik-11B zamiast Minitron-7B** — nasz model jest przyciętą wersją 11B i odzyskuje ~90% jakości bazowej. 11B leży pobrany i nieużywany.
- **Rozszerzenie zbioru wzorcowego** — przy 6 pytaniach miara J-2 pozostaje niemierzalna.

---

## 5. Warunki powtórzenia pomiaru

```bash
# pełny pomiar — jedyny, który ocenia bramki (100 przypadków)
python -m eval.benchmark.przebieg2 --sprawa 3 --sprawa 4 --par 25

# szybka diagnostyka — pomijana przez bramki, ~25 min
python -m eval.benchmark.przebieg2 --sprawa 3 --sprawa 4 --par 8

# oba układy kontroli jednym przebiegiem
python -m eval.benchmark.przebieg2 --sprawa 3 --sprawa 4 --par 25 --cien
```

Sprzęt: 8 GB VRAM, Ollama `NUM_PARALLEL=1`. Modele: `bielik-lex-map`
(Bielik-Minitron-7B-v3.0, Q4_K_M) dla polskiego, `llama-lex-map`
(Llama 3.1 8B, Q4_K_M) dla angielskiego.

⚠️ **Obciążenie maszyny wpływa na wynik czasowy, nie na jakościowy.**
16.08.2026 jeden przypadek liczył się 10,4 godziny, bo maszynę zajmowały
inne procesy — stąd `BUDZET_ESKALACJI_S = 900`.
