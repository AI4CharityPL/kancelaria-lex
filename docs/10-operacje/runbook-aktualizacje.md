# Runbook — aktualizacje w środowisku odciętym

## Problem

Odcięcie od internetu chroni akta, ale odcina też łatki bezpieczeństwa. Brak procedury oznacza system, który po roku stoi na komponentach z publicznie znanymi podatnościami — i wtedy izolacja jest jedynym, co go broni.

Odpowiedzią jest **świadome okno serwisowe** zamiast automatycznych aktualizacji w tle.

## Zasady

1. Środowisko produkcyjne **nigdy** nie pobiera niczego z internetu — także w trakcie aktualizacji.
2. Paczka jest budowana w środowisku przygotowawczym, weryfikowana i wnoszona ręcznie.
3. **Zasada dwóch osób** — kto buduje paczkę, nie wnosi jej sam.
4. Każda aktualizacja jest odwracalna. Brak sprawdzonej ścieżki powrotu = brak aktualizacji.

## Role

| Rola | Zadanie |
|---|---|
| Inżynier przygotowujący | Buduje paczkę, generuje SBOM i sumy kontrolne |
| Inżynier wdrażający | Weryfikuje sumy, wnosi, wdraża — **osoba inna niż powyżej** |
| Zatwierdzający | Wspólnik lub administrator — zgoda na okno serwisowe |

---

## Procedura

### Etap 1 — przygotowanie *(strefa z dostępem do sieci)*

1. Przegląd podatności komponentów względem obecnego SBOM.
2. Decyzja o zakresie: co aktualizujemy i dlaczego. Aktualizacja „bo jest nowa wersja" nie jest uzasadnieniem — uzasadnieniem jest podatność albo potrzebna funkcja.
3. Pobranie obrazów **po sumie `sha256`**, nie po tagu.
4. Pobranie wag modeli, jeśli w zakresie, wraz z **weryfikacją licencji** (licencja wag bywa inna niż licencja kodu — przypadek Suryi).
5. Build obrazów aplikacji z **bramką CI na lockfile** — build pada przy `anthropic`, `google-genai`, `posthog`, `mcp`.
6. Uruchomienie pełnego zestawu testów: izolacja, czerwony zespół, bramki jakościowe.
7. Wygenerowanie SBOM (CycloneDX) i manifestu sum kontrolnych.
8. Podpisanie manifestu.

**Warunek przejścia dalej: wszystkie testy zaliczone.** Paczka z niezaliczonym testem izolacji nie opuszcza etapu 1.

### Etap 2 — przeniesienie

9. Zapis paczki na nośnik przeznaczony wyłącznie do tego celu.
10. Skan antywirusowy na stacji pośredniej.
11. Przekazanie nośnika inżynierowi wdrażającemu — **osobie innej niż przygotowujący**.
12. Weryfikacja podpisu manifestu i sum kontrolnych **przed** wniesieniem do strefy zamkniętej.

### Etap 3 — wdrożenie *(okno serwisowe)*

13. Zgoda zatwierdzającego; powiadomienie użytkowników.
14. **Kopia zapasowa przed zmianą** — pełna, zweryfikowana.
15. Ponowna weryfikacja sum po stronie docelowej.
16. Import obrazów do lokalnego lustra rejestru.
17. Wdrożenie; migracje bazy.
18. **Testy izolacji po stronie produkcyjnej** — to nie jest powtórka etapu 1, bo topologia sieci jest tu inna.
19. Przebieg dymny: wgranie dokumentu → OCR → indeksowanie → zapytanie z cytatami.
20. Wpis do dziennika zmian: co, kiedy, kto, sumy kontrolne, wynik testów.

### Etap 4 — po wdrożeniu

21. Obserwacja przez 24 h.
22. Aktualizacja SBOM i rejestru wersji w `models/`.
23. Wycofanie, jeśli cokolwiek zawiodło.

---

## Wycofanie

Warunki wymuszające wycofanie — **bez dyskusji**:

- niezaliczony test izolacji po wdrożeniu,
- niezgodność sumy kontrolnej wag modelu,
- błąd migracji bazy,
- spadek jakości poniżej progów bramek.

Procedura: zatrzymanie usług → przywrócenie poprzednich obrazów z lustra → odtworzenie bazy z kopii z kroku 14 → testy izolacji → wpis do dziennika.

Poprzednia wersja obrazów zostaje w lustrze **co najmniej do zakończenia obserwacji** z kroku 21.

## Częstotliwość

| Rodzaj | Okno |
|---|---|
| Krytyczna podatność w komponencie wystawionym | Niezwłocznie, okno nadzwyczajne |
| Podatności wysokie | Do 30 dni |
| Rutynowe aktualizacje | Kwartalnie |
| Aktualizacja modelu językowego | Wyłącznie po przejściu **pełnych bramek jakościowych** — nowszy model nie znaczy lepszy dla polskich akt |

## Dziennik zmian

`infra/dziennik-zmian.md` — data, zakres, sumy kontrolne, wynik testów, osoby, wynik obserwacji. To materiał dowodowy dla audytu z art. 21 lit. e ustawy o KSC.
