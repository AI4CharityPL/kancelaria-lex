# Ocena skutków dla ochrony danych (DPIA) — art. 35 RODO

> **Zastrzeżenie.** Szkielet DPIA przygotowany od strony technicznej. Ocena wymaga uzupełnienia i zatwierdzenia przez administratora danych oraz konsultacji z inspektorem ochrony danych. Nie jest opinią prawną.

---

## DPIA jest obowiązkowa

Nie „warto rozważyć". Przesłanki art. 35 ust. 3 RODO są spełnione wielokrotnie:

| Przesłanka | Wystąpienie |
|---|---|
| Przetwarzanie na dużą skalę szczególnych kategorii danych (art. 9) | Akta zawierają dane o zdrowiu, życiu seksualnym, poglądach, przynależności |
| Dane dotyczące wyroków i czynów zabronionych (art. 10) | Istota spraw karnych |
| Systematyczna ocena na podstawie zautomatyzowanego przetwarzania | Klasyfikacja pism, wykrywanie rozbieżności, propozycje terminów |
| Nowa technologia | Lokalne modele językowe w analizie akt |
| Dane osób w sytuacji zależności / szczególnie narażonych | Oskarżeni, pokrzywdzeni, świadkowie, małoletni |

Do tego dochodzi to, czego RODO nie reguluje, a co jest tu ważniejsze: **tajemnica zawodowa**, w tym nieuchylalna tajemnica obrończa.

---

## 1. Opis przetwarzania

**Cel:** wsparcie prawników w analizie akt i prowadzeniu spraw — wyszukiwanie, chronologia, propozycje terminów, wykrywanie rozbieżności.

**Zakres danych:** dane identyfikacyjne stron i uczestników, dane z art. 9, dane z art. 10, treść dokumentów procesowych, metadane spraw.

**Kategorie osób:** klienci, strony przeciwne, świadkowie, pokrzywdzeni, biegli, pełnomocnicy, funkcjonariusze.

**Podstawy prawne:** wykonanie umowy o pomoc prawną (art. 6 ust. 1 lit. b) · obowiązek prawny (art. 6 ust. 1 lit. c) · prawnie uzasadniony interes (art. 6 ust. 1 lit. f); dla art. 9 — ustalenie, dochodzenie lub obrona roszczeń (art. 9 ust. 2 lit. f); dla art. 10 — przetwarzanie pod nadzorem władz publicznych lub na podstawie przepisów krajowych (**do potwierdzenia z IOD, w powiązaniu z prawem o adwokaturze / o radcach prawnych**).

**Odbiorcy: brak.** System jest zamknięty. Nie występuje powierzenie przetwarzania dostawcy chmurowemu — to główny efekt architektury.

**Transfery poza EOG: brak**, konstrukcyjnie wykluczone (trzy warstwy izolacji).

**Retencja:** domyślnie 10 lat, konfigurowalnie, z możliwością wstrzymania usunięcia.

---

## 2. Ocena niezbędności i proporcjonalności

| Pytanie | Odpowiedź |
|---|---|
| Czy cel da się osiągnąć mniej inwazyjnie? | System nie zwiększa zakresu danych — kancelaria i tak posiada te akta z mocy prowadzenia sprawy. Zmienia się sposób przetwarzania, nie zakres. |
| Czy zakres jest minimalny? | Tak — brak wzbogacania z zewnątrz, brak profilowania osób, brak danych spoza akt sprawy. |
| Czy przetwarzanie automatyczne wywołuje skutki prawne wobec osób? | **Nie.** Wyjście systemu to materiał roboczy dla prawnika. Żadna decyzja nie zapada automatycznie — art. 22 RODO nie ma zastosowania. |
| Czy dane trafiają do trenowania modeli? | **Nie.** Dostrajanie na aktach zostało świadomie odrzucone — [`06-stos-ai.md`](../06-stos-ai.md). Wagi modelu są niezmienne. |

Ostatni punkt jest istotny: brak dostrajania oznacza, że **dane osobowe nie utrwalają się w wagach modelu**. Usunięcie dokumentu usuwa dane naprawdę, bez problemu „modelu, który pamięta".

---

## 3. Ryzyka dla praw i wolności

| # | Ryzyko | Prawdop. | Skutek | Środki | Poziom po |
|---|---|---|---|---|---|
| R-1 | Wyciek akt do zewnętrznego dostawcy modelu | Bardzo niskie | **Krytyczny** | Trzy warstwy izolacji, testowane wykonywalnie | Bardzo niskie |
| R-2 | Ujawnienie materiału obrończego | Bardzo niskie | **Krytyczny** | Odrębny magazyn, odrębny klucz, odrębna autoryzacja | Bardzo niskie |
| R-3 | Dostęp osoby nieuprawnionej wewnątrz kancelarii | Średnie | Wysoki | Dostęp imienny, wiedza konieczna, ściany etyczne, MFA, log audytowy | Niskie |
| R-4 | Błędna analiza wpływa na obronę | Średnie | Wysoki | Wymuszone cytowanie z weryfikacją maszynową, obowiązkowa weryfikacja przez prawnika, bramki jakości | Średnie ⚠️ |
| R-5 | Przeoczony termin z winy systemu | Niskie | Wysoki | Silnik deterministyczny, potwierdzenie prawnika, ostrzeganie wielokrotne | Niskie |
| R-6 | Utrata danych | Niskie | Wysoki | Kopie szyfrowane, **testowane** odtworzenie | Niskie |
| R-7 | Manipulacja przez dokument strony przeciwnej | Średnie | Średni | Brak narzędzi sieciowych, weryfikacja cytatów, testy czerwonego zespołu | Niskie |
| R-8 | Utrwalenie danych w wagach modelu | **Wykluczone** | — | Brak dostrajania | — |

### R-4 pozostaje na poziomie średnim — świadomie

To jedyne ryzyko, którego nie sprowadzamy do niskiego, i uczciwość wymaga to powiedzieć wprost.

Weryfikacja cytatów potwierdza, że przytoczony fragment **istnieje w aktach i nie został zmyślony**. Nie potwierdza, że **wniosek wyciągnięty z tego fragmentu jest trafny**. Model może poprawnie zacytować i błędnie zinterpretować — a w profilu rozwojowym (kwantyzacja Q4) ryzyko to jest wyższe.

Środek zaradczy nie jest techniczny, tylko organizacyjny: **każda analiza podlega weryfikacji przez prawnika**, a system jest przedstawiany użytkownikom jako narzędzie robocze, nie źródło ustaleń. Interfejs musi to komunikować, nie tylko regulamin.

---

## 4. Prawa osób

| Prawo | Realizacja | Uwagi |
|---|---|---|
| Dostęp (art. 15) | Przez kancelarię, na zasadach ogólnych | Ograniczone tajemnicą zawodową i prawami osób trzecich |
| Sprostowanie (art. 16) | Możliwe | Dokument procesowy pozostaje niezmieniony jako dowód; korekta w warstwie metadanych |
| Usunięcie (art. 17) | **Zwykle wyłączone** | Art. 17 ust. 3 lit. b i e — obowiązek prawny oraz ustalenie/dochodzenie/obrona roszczeń. **Każdy przypadek wymaga oceny**; system musi umieć wstrzymać usunięcie |
| Ograniczenie (art. 18) | Możliwe | Oznaczenie sprawy |
| Przenoszenie (art. 20) | Nie ma zastosowania | Podstawą nie jest zgoda ani wyłącznie umowa z osobą, której dane dotyczą |
| Sprzeciw (art. 21) | Ocena indywidualna | Przeważający interes w postaci prowadzenia obrony |
| Decyzje automatyczne (art. 22) | **Nie ma zastosowania** | Brak decyzji automatycznych |

**Napięcie do rozstrzygnięcia:** osoba, której dane znalazły się w aktach jako świadek lub pokrzywdzony, może żądać usunięcia. Zwykle przeważy obowiązek przechowywania akt i prawo do obrony — ale odpowiedź „nie usuwamy nigdy" jest nieprawidłowa. Procedura oceny wymaga opracowania przez IOD.

---

## 5. Wynik

**Ryzyko szczątkowe: akceptowalne**, z zastrzeżeniem R-4.

**Uprzednie konsultacje z organem nadzorczym (art. 36 RODO) — wstępnie niewymagane**, ponieważ zastosowane środki sprowadzają ryzyka R-1 i R-2 do poziomu bardzo niskiego. Ocenę potwierdza IOD.

Warto zauważyć, że architektura zamknięta **zmniejsza** profil ryzyka względem stanu obecnego, jeśli kancelaria korzystała dotąd z jakichkolwiek narzędzi chmurowych. Główny efekt DPIA nie polega na tym, że projekt wprowadza nowe ryzyka — tylko że usuwa istniejące.

## Warunki dopuszczenia do przetwarzania danych rzeczywistych

DPIA obowiązuje **warunkowo**. Warunki muszą być spełnione łącznie:

1. Bramki z [`11-testy-i-bramki.md`](../11-testy-i-bramki.md) zaliczone, w tym testy izolacji i przechwycenie ruchu.
2. Profil produkcyjny modelu (Q8 lub wyższy) — **profil rozwojowy Q4 nie jest dopuszczony do akt rzeczywistych**.
3. Log audytowy działa i jest odporny na manipulację.
4. Materiał obrończy ma odrębny magazyn i odrębny klucz.
5. Kopia zapasowa odtworzona testowo co najmniej raz.
6. Użytkownicy przeszkoleni, w tym w zakresie obowiązku weryfikacji (R-4).

## Przegląd

Przy każdej zmianie modelu, zakresu danych lub architektury; poza tym raz w roku.

| Pole | Wartość |
|---|---|
| Administrator | _do uzupełnienia_ |
| IOD | _do uzupełnienia_ |
| Data sporządzenia | 14.08.2026 |
| Data zatwierdzenia | _oczekuje_ |
