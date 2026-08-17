# ADR-0001 — Fundament: fork OpenContracts z własną warstwą

**Status:** przyjęta · **Data:** 14.08.2026 · **Rewizja:** po M6

## Kontekst

Potrzebny jest system zarządzania dokumentami z anotacjami, wyszukiwaniem i interfejsem przeglądania, na którym osadzimy warstwę agentową i moduł spraw. Zbudowanie tego od zera to miesiące pracy.

OpenContracts (MIT, Django/React/PostgreSQL/Celery) dostarcza rdzeń dokumentowy: parsowanie z zachowaniem układu strony, anotacje, korpusy, wyszukiwanie hybrydowe, ekstrakcję pól, interfejs.

## Rozważane opcje

| Opcja | Zalety | Wady |
|---|---|---|
| **A. Fork + własna warstwa** ✅ | Gotowy rdzeń; pełna kontrola nad zmianami; możliwość fizycznego wycięcia kodu | Utrzymanie całego stosu bazowego |
| B. Fork bez zmian, sama konfiguracja | Najszybsze; łatwy merge z upstreamem | **Izolacja opiera się na konfiguracji, którą można cofnąć jednym wpisem** |
| C. Greenfield | Minimalna powierzchnia ataku; dokładnie to, co potrzebne | Miesiące pracy na odtworzenie DMS i interfejsu; wysokie ryzyko |

## Decyzja

**Opcja A.**

Opcja B odpadła po weryfikacji kodu. Ustalenia U-1 i U-2 pokazały, że proponowana w raporcie źródłowym gwarancja („nie ustawiaj kluczy API") nie działa: przy Ollamie klucz jest podstawiany automatycznie, a poświadczenia mogą mieszkać w bazie danych z regułą „baza wygrywa nad zmienną środowiskową". Konfiguracja nie jest tu granicą bezpieczeństwa.

Opcja C odpadła na koszcie i ryzyku — nie na zasadach.

Zakres modyfikacji upstreamu **celowo zawężony** do: wycięcia SDK chmurowych, MCP i telemetrii · strażnika adresów · zmiany embeddera · TLS bez ACME. Reszta zmian idzie do **własnych aplikacji Django** (`sprawy`, `agenci`, `audyt`, `dostep`, `anonimizacja`), które nie kolidują z upstreamem przy merge'u.

## Konsekwencje

**Pozytywne:** gotowy rdzeń dokumentowy · możliwość usunięcia kodu, nie tylko wyłączenia · własne aplikacje odporne na konflikty przy merge'u.

**Negatywne:** przejęcie odpowiedzialności za bezpieczeństwo całego stosu bazowego · kilka–kilkanaście godzin miesięcznie na utrzymanie · ryzyko cichego cofnięcia zmian przy merge'u.

**Środek zaradczy dla ostatniego punktu — kluczowy:** bramka CI na lockfile. Build pada, jeśli wróci `anthropic`, `google-genai`, `posthog` lub `mcp`. Bez niej najbardziej prawdopodobnym trybem awarii projektu jest merge za pół roku, którego nikt nie zauważy.

## Warunek utrzymania decyzji

**Zapewnione utrzymanie po wdrożeniu jest warunkiem wejścia na produkcję.** Fork bez opiekuna staje się w kancelarii ryzykiem, nie oszczędnością. Jeśli koszt utrzymania okaże się wyraźnie wyższy niż zakładany, decyzja podlega rewizji w punkcie M6.
