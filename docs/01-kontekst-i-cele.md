# 01 — Kontekst i cele

## Problem

Kancelaria prowadzi sprawy, w których materiał dowodowy i korespondencja procesowa są objęte tajemnicą zawodową. Część spraw to **niepubliczne postępowania karne** — akta zawierają dane z art. 9 RODO (m.in. o zdrowiu, życiu seksualnym, poglądach) oraz art. 10 RODO (wyroki skazujące i czyny zabronione), a także materiał objęty **tajemnicą obrończą**, której nie może uchylić nawet sąd.

Jednocześnie objętość akt rośnie szybciej niż czas prawników. Typowa sprawa karna to setki stron: aktów oskarżenia, protokołów przesłuchań, opinii biegłych, postanowień. Ręczne budowanie chronologii, wyszukiwanie sprzeczności w zeznaniach i pilnowanie terminów procesowych to praca, którą da się częściowo zautomatyzować — ale wyłącznie narzędziem, które nigdy nie wypuści treści akt poza kancelarię.

## Wymóg twardy

**Zero łączności z zewnętrznymi dostawcami modeli.** Cały łańcuch — OCR, parsowanie, embedding, generowanie odpowiedzi — działa na sprzęcie kancelarii, na modelach pobranych raz i uruchamianych lokalnie.

To nie jest preferencja architektoniczna, tylko warunek zgodności z tajemnicą zawodową. Wysłanie fragmentu akt do zewnętrznego API jest ujawnieniem informacji objętej tajemnicą — niezależnie od tego, jakie zapewnienia składa dostawca w regulaminie.

**Instancja samodzielna.** System nie jest przyłączalny do ChatGPT, Claude Code ani żadnego zewnętrznego klienta agentowego. Fork usuwa serwer MCP — nie wyłącza go konfiguracją, lecz usuwa z routingu i z zależności.

## Cele

| # | Cel | Miara sukcesu |
|---|---|---|
| C1 | Akta nie opuszczają infrastruktury kancelarii | Zero pakietów wychodzących w przechwyceniu podczas pełnego przebiegu dokumentu |
| C2 | Skrócenie czasu na zapoznanie się z aktami | Czas do pierwszej użytecznej chronologii sprawy < 15 min od wgrania |
| C3 | Odpowiedzi weryfikowalne, nie „wiarygodnie brzmiące" | Każde twierdzenie wskazuje istniejący fragment źródła, sprawdzony maszynowo |
| C4 | Zero przeoczonych terminów procesowych z winy systemu | Terminy liczy silnik deterministyczny; model nigdy ich nie wylicza |
| C5 | Wykazalna zgodność z RODO i art. 21 ustawy o KSC | Komplet dokumentacji + log audytowy odporny na manipulację |

## Czego ten system NIE robi

Rozgraniczenie jest równie ważne jak zakres:

- **Nie udziela porad prawnych.** Generuje materiał roboczy dla prawnika. Każda analiza wymaga weryfikacji przez osobę odpowiedzialną zawodowo.
- **Nie zastępuje sprawdzenia terminu w aktach.** Proponuje termin i wskazuje podstawę; potwierdza prawnik.
- **Nie jest systemem do rozliczeń ani fakturowania.** Poza zakresem tej fazy.
- **Nie orzeka o kwalifikacji prawnej czynu.**

## Odbiorcy

| Rola | Co robi w systemie |
|---|---|
| Adwokat / radca prowadzący | Zadaje pytania do akt, przegląda chronologię, potwierdza terminy |
| Aplikant / asystent | Wgrywa dokumenty, weryfikuje wynik OCR, opisuje metadane |
| Administrator kancelarii | Nadaje dostępy, prowadzi rejestr spraw, pilnuje ścian etycznych |
| Inspektor ochrony danych | Czyta log audytowy, prowadzi rejestr czynności, obsługuje incydenty |

## Założenia i ograniczenia przyjęte świadomie

1. **Lokalny model jest słabszy od najlepszych modeli komercyjnych.** Akceptujemy to jako cenę poufności. Odpowiedź kompensujemy konstrukcją: wymuszone cytowanie i mechaniczna weryfikacja pokrycia obniżają koszt słabszego modelu bardziej niż zmiana modelu na mocniejszy.
2. **Lokalny OCR jest słabszy na kserokopiach i piśmie odręcznym.** Wchodzi ręczna weryfikacja próbki oraz mierzony CER jako bramka.
3. **Odcięcie od sieci utrudnia łatanie.** Wymaga świadomej procedury aktualizacji zamiast automatów — patrz [`10-operacje/runbook-aktualizacje.md`](10-operacje/runbook-aktualizacje.md).
4. **Utrzymanie forka dużej aplikacji Django to realny koszt.** Decyzja i uzasadnienie: [`14-decyzje/ADR-0001-fundament.md`](14-decyzje/ADR-0001-fundament.md).

## Dokument źródłowy

Projekt wychodzi od wewnętrznego raportu z 13.08.2026, przygotowanego przed rozpoczęciem prac. Kierunek raportu jest zachowany. Weryfikacja kodu źródłowego OpenContracts wykazała jednak, że opisany tam mechanizm gwarancji jest niewystarczający — korekty zebrane w [`05-izolacja-i-siec.md`](05-izolacja-i-siec.md).

> Sam raport nie wchodzi do repozytorium publicznego: był dokumentem prywatnym, przygotowanym dla konkretnej osoby, i nie niesie niczego, czego nie ma w tej dokumentacji. Wszystkie jego ustalenia zostały przeniesione do dokumentów `01`–`22`.
