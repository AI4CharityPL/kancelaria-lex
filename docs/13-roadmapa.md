# 13 — Roadmapa

## Dwie równoległe ścieżki

Ścieżka zgodności **nie czeka** na ścieżkę techniczną. Termin rejestracyjny KSC biegnie niezależnie od tego, czy system w ogóle powstanie.

```
  ZGODNOŚĆ   K-1 ocena ──► K-2 rejestracja ──► K-3 umowy ──► K-4 szkolenia
             15.09           02.10 ⚠️            31.10          31.12
             ─────────────────────────────────────────────────────────►

  TECHNIKA   F0 ──► F1-2 ──► F3-4 ──► F5 ──► F6 ──► F7 ──► F8 ──► pilotaż
             docs   izolacja  PoC AI  sprawy compl. bramki E2E
             ─────────────────────────────────────────────────────────►
```

---

## Ścieżka zgodności — terminy zewnętrzne

| # | Zadanie | Termin | Odpowiedzialny |
|---|---|---|---|
| K-1 | Ocena podmiotowa KSC | 15.09.2026 | prawnik + wspólnicy |
| **K-2** | **Rejestracja w wykazie, jeśli podlega** | **02.10.2026** ⚠️ | wspólnicy |
| K-3 | Przegląd umów pod kątem łańcucha dostaw | 31.10.2026 | prawnik |
| K-4 | Szkolenie kierownictwa (KSC + art. 4 AI Act) | 31.12.2026 | wspólnicy |
| K-6 | Granica treści zgłoszenia incydentu | przed pilotażem | prawnik |
| P-2 | Zatwierdzenie DPIA | przed pilotażem | administrator + IOD |
| K-5 | Środki art. 21 wdrożone | 02.04.2027 | zespół |

**K-1 i K-2 zaczynają się teraz.** Nie wymagają ani jednej linii kodu.

---

## Ścieżka techniczna

| Faza | Zakres | Stan | Wynik |
|---|---|---|---|
| **0** | Dokumentacja, decyzje, struktura | ✅ | Komplet `docs/`, ADR-y |
| **1** | Wycięcie ścieżek chmurowych z builda | 🔨 | Patche + bramka CI |
| **2** | Segmentacja sieci, łańcuch dostaw | 🔨 | Compose z 4 sieciami + testy izolacji |
| **3** | Lokalny stos AI | 🔨 | Bielik + embedder PL + OCR, pomiary |
| **4** | Warstwa agentowa | 🔨 | Weryfikator cytatów, agent pytań |
| **5** | Moduł „Sprawy" | ⬜ | Model domenowy, silnik terminów |
| **6** | Bezpieczeństwo i audyt | ⬜ | Log z łańcuchem sum, magazyn obrończy, ściany etyczne |
| **7** | Ewaluacja | ⬜ | Gold set, wyniki bramek |
| **8** | E2E offline | ⬜ | Przechwycenie ruchu — dowód O-1 |
| **9** | Pilotaż | ⬜ | Wybrane sprawy, wąska grupa |

### Kolejność nie jest przypadkowa

Fazy 1–2 idą **przed** stosem AI, mimo że model jest atrakcyjniejszy do zbudowania. Powód: uruchomienie modelu w środowisku bez izolacji tworzy nawyk pracy, który potem trudno cofnąć, a testy izolacji dopisywane po fakcie zwykle sprawdzają to, co już działa, zamiast tego, co powinno być zablokowane.

Faza 6 (bezpieczeństwo) przed 7 (ewaluacja), bo ewaluacja na systemie bez logu audytowego nie daje śladu, który dałoby się później przedstawić.

---

## Kamienie milowe

| Kamień | Kryterium — wykonywalne, nie opisowe |
|---|---|
| **M1 — izolacja dowiedziona** | `pytest tests/izolacja/` zielone; test negatywny potwierdza, że testy potrafią paść |
| **M2 — stos AI działa** | Dokument z korpusu syntetycznego: OCR → indeks → odpowiedź z cytatami |
| **M3 — cytaty weryfikowalne** | Weryfikator odrzuca zmyślony cytat w teście |
| **M4 — terminy deterministyczne** | Silnik reguł przechodzi testy; propozycja modelu wymaga potwierdzenia |
| **M5 — poufność wdrożona** | Materiał obrończy nieczytelny w zrzucie głównej bazy (O-4) |
| **M6 — bramki jakościowe** | J-1…J-8 zaliczone **na profilu produkcyjnym** |
| **M7 — dowód końcowy** | Przechwycenie ruchu: zero pakietów wychodzących (O-1) |
| **M8 — dopuszczenie** | Pełna lista warunków z DPIA odhaczona |

**Dopiero M8 otwiera drogę do rzeczywistych akt.**

---

## Punkty decyzyjne

| Kiedy | Decyzja | Podstawa |
|---|---|---|
| Po M2 | Czy jakość Bielika wystarcza? | Pomiary z PoC; alternatywą inny model otwarty |
| Po M2 | Czy `multilingual-e5-base` wystarcza? | Jakość retrievalu; alternatywą `bge-m3` (zmiana schematu) |
| Po M6 | Wybór wariantu sprzętowego | Rzeczywiste pomiary przepustowości, nie szacunki |
| Po M6 | Czy fork się broni? | Koszt utrzymania w praktyce vs. założenia ADR-0001 |
| Przed M8 | Zakres pilotażu | Które sprawy, ilu prawników |

Punkt czwarty jest szczery: jeśli utrzymanie forka okaże się wyraźnie kosztowniejsze niż zakładano, ADR-0001 podlega rewizji. Decyzja architektoniczna nie jest nieodwołalna — nieodwołalny jest tylko wyciek danych.

---

## Ryzyka harmonogramowe

| Ryzyko | Reakcja |
|---|---|
| Termin K-2 zderza się z pracami technicznymi | Ścieżki rozdzielone; K-1/K-2 nie wymagają zespołu technicznego |
| Bramki jakościowe niezaliczone na Q4 | Oczekiwane — bramki mierzy się na profilu produkcyjnym |
| Upstream zmienił się względem ustaleń U-1…U-8 | Weryfikacja przed forkiem jest krokiem obowiązkowym, nie formalnością |
| Zatwierdzanie reguł terminów wchodzi na ścieżkę krytyczną | Wymaga czasu prawnika — zaplanować wcześnie, to nie jest zadanie inżynierskie |
| Brak zapewnionego utrzymania po wdrożeniu | **Warunek wejścia na produkcję**, nie kwestia do rozstrzygnięcia później |
