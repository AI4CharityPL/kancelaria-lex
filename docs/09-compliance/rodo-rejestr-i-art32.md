# RODO — rejestr czynności i środki z art. 32

> **Zastrzeżenie.** Szkielet do uzupełnienia i zatwierdzenia przez administratora danych oraz IOD.

---

## Rejestr czynności przetwarzania (art. 30)

Wpis do istniejącego rejestru kancelarii — system nie tworzy nowej czynności przetwarzania, tylko nowy **sposób** przetwarzania akt, które kancelaria i tak posiada.

| Pole | Treść |
|---|---|
| Nazwa czynności | Analiza akt spraw z wykorzystaniem lokalnego systemu wspomagającego |
| Administrator | _do uzupełnienia_ |
| IOD | _do uzupełnienia_ |
| Cele | Wsparcie w analizie akt, prowadzenie terminarza procesowego, wyszukiwanie w dokumentach |
| Kategorie osób | Klienci, strony przeciwne, świadkowie, pokrzywdzeni, biegli, pełnomocnicy, funkcjonariusze |
| Kategorie danych | Identyfikacyjne, kontaktowe, **art. 9**, **art. 10**, treść dokumentów procesowych |
| Odbiorcy | **Brak** — system zamknięty, bez powierzenia przetwarzania |
| Transfery poza EOG | **Brak** — wykluczone konstrukcyjnie |
| Termin usunięcia | Zgodnie z zasadami przechowywania akt, domyślnie 10 lat |
| Ogólny opis środków | Patrz sekcja art. 32 poniżej |

**Pozycja „odbiorcy: brak" jest głównym efektem tego projektu.** Każde narzędzie chmurowe wymagałoby tu wpisu i umowy powierzenia, a przy tajemnicy zawodowej — także rozstrzygnięcia, czy powierzenie jest w ogóle dopuszczalne.

---

## Środki techniczne i organizacyjne (art. 32)

### a) Pseudonimizacja i szyfrowanie

| Środek | Realizacja |
|---|---|
| Szyfrowanie w spoczynku | Pełne szyfrowanie nośnika + klucz danych per sprawa |
| **Materiał obrończy** | Odrębny magazyn, odrębny klucz, odrębna autoryzacja |
| Szyfrowanie w tranzycie | mTLS między segmentami, własne CA (bez ACME) |
| Kopie zapasowe | Szyfrowane, klucz przechowywany rozdzielnie |
| Pseudonimizacja | Przed eksportem i przed użyciem materiału w ewaluacji |

### b) Poufność, integralność, dostępność, odporność

| Wymiar | Środki |
|---|---|
| Poufność | Trzy warstwy izolacji · dostęp imienny · wiedza konieczna · MFA · ściany etyczne |
| Integralność | Log audytowy z łańcuchem sum kontrolnych · sumy kontrolne wag modeli · obrazy przypięte po `sha256` |
| Dostępność | Kopie zapasowe, RPO ≤ 24 h, RTO ≤ 8 h |
| Odporność | Segmentacja ograniczająca zasięg naruszenia · limity zasobów · brak roota w kontenerach |

### c) Przywracanie dostępności

Kopie codzienne, szyfrowane, poza systemem produkcyjnym. **Odtworzenie testowane kwartalnie** — kopia nieprzetestowana nie jest kopią. Szczegóły: [`10-operacje/backup-i-dr.md`](../10-operacje/backup-i-dr.md).

### d) Regularne testowanie i ocena skuteczności

Tu system wychodzi ponad typową praktykę: skuteczność środków izolacji jest **testowana wykonywalnie przy każdym buildzie**, a nie oceniana okresowym przeglądem dokumentacji.

| Test | Częstotliwość |
|---|---|
| Testy izolacji (`tests/izolacja/`) | Każdy build |
| Przechwycenie ruchu podczas pełnego przebiegu | Przed każdym wydaniem |
| Testy czerwonego zespołu (`tests/injection/`) | Każdy build |
| Bramki jakościowe (gold set) | Przy zmianie modelu lub retrievalu |
| Test odtworzenia z kopii | Kwartalnie |
| Przegląd uprawnień | Kwartalnie |
| Przegląd rejestru ryzyk | Półrocznie |

---

## Retencja i prawo do usunięcia — napięcie do rozstrzygnięcia

Osoba, której dane trafiły do akt jako świadek lub pokrzywdzony, może żądać usunięcia (art. 17 RODO).

**Zwykle przeważy obowiązek przechowywania** — art. 17 ust. 3 lit. b (obowiązek prawny) i lit. e (ustalenie, dochodzenie lub obrona roszczeń), a ponadto tajemnica zawodowa i zasady przechowywania akt.

Ale odpowiedź „nie usuwamy nigdy" jest nieprawidłowa. Wymagania dla systemu:

1. Możliwość **wstrzymania usunięcia** (legal hold) niezależnie od upływu terminu retencji.
2. Rejestr żądań usunięcia wraz z uzasadnieniem decyzji.
3. Automatyczne usunięcie po terminie **nie może** dotyczyć akt objętych wstrzymaniem.
4. Usunięcie jest skuteczne — brak dostrajania modelu oznacza, że dane nie utrwalają się w wagach.

Procedurę oceny opracowuje IOD.

---

## Naruszenia ochrony danych

Zgłoszenie do UODO w 72 h (art. 33), zawiadomienie osób przy wysokim ryzyku (art. 34).

⚠️ Kolizja z tajemnicą zawodową — zgłoszenie nie może ujawniać treści objętej tajemnicą. Wspólna ścieżka z obowiązkiem KSC: [`10-operacje/runbook-incydent.md`](../10-operacje/runbook-incydent.md).

Uwaga praktyczna: w architekturze zamkniętej najbardziej prawdopodobne naruszenie to **nie** wyciek na zewnątrz, lecz dostęp osoby nieuprawnionej wewnątrz kancelarii (ryzyko R-3) albo utrata nośnika kopii zapasowej. Runbook musi obejmować przede wszystkim te scenariusze.

---

## Zadania

| # | Zadanie | Odpowiedzialny |
|---|---|---|
| P-1 | Uzupełnienie rejestru czynności o tę pozycję | IOD |
| P-2 | Zatwierdzenie DPIA | Administrator + IOD |
| P-3 | Procedura oceny żądań usunięcia | IOD |
| P-4 | Aktualizacja klauzul informacyjnych | prawnik |
| P-5 | Szkolenie użytkowników — w tym obowiązek weryfikacji analiz (R-4) | IOD + zespół projektu |
| P-6 | Przegląd umów powierzenia — sprawdzenie, czy narzędzia chmurowe używane dotąd wymagają wypowiedzenia | prawnik |
