# ADR-0003 — Izolacja w trzech warstwach zamiast konfiguracji

**Status:** przyjęta · **Data:** 14.08.2026

## Kontekst

Raport źródłowy proponował gwarancję opartą na konfiguracji: nie ustawiać kluczy API w `.env`, ustawić dostawcę na Ollamę, ograniczyć egres na firewallu.

Weryfikacja kodu OpenContracts (14.08.2026) wykazała trzy problemy:

- **U-1** — Ollama jedzie przez `OpenAIProvider`, a kod **sam podstawia atrapę klucza** `"ollama"`, gdy klucza brak. Teza „bez klucza ścieżka jest niedostępna" jest fałszywa. Dodatkowo: pakietu `openai` **nie można usunąć**, bo jest transportem do modelu lokalnego.
- **U-2** — poświadczenia mogą być w bazie (`PipelineSettings`), z regułą „baza wygrywa nad zmienną środowiskową". Czysty `.env` nie wystarcza.
- **U-4** — żaden plik compose nie definiuje sieci. „Ograniczenie egresu na poziomie sieci Docker" nie jest przełącznikiem; topologię trzeba napisać od zera.

Do tego SDK Anthropic i Google, PostHog i serwer MCP są **twardymi zależnościami** (U-3) — obecnymi w obrazie niezależnie od konfiguracji.

## Decyzja

Trzy niezależne warstwy. **Każda ma działać samodzielnie, gdy dwie pozostałe zawiodą.**

| | Warstwa | Mechanizm |
|---|---|---|
| **A** | Build | SDK chmurowe, telemetria i MCP usunięte z obrazu. Bramka CI blokuje powrót. |
| **B** | Proces | `base_url` musi należeć do allowlisty — sprawdzane przy starcie **i przy zapisie do bazy**. Naruszenie: proces nie wstaje / zapis odrzucony i zalogowany. |
| **C** | Sieć | Cztery segmenty, trzy `internal: true` — brak trasy do bramy. |

Punktem kontroli jest **adres, nie klucz** — to bezpośrednia konsekwencja U-1.

## Uzasadnienie kluczowych wyborów

**Dlaczego `openai` zostaje, a `anthropic` i `google` wypadają.** Wbrew intuicji z raportu: usunięcie `openai` zepsułoby model lokalny, bo Ollama wystawia API zgodne z OpenAI. Samo jego pozostawienie nie tworzy ryzyka — ryzykiem jest adres, pod który klient uderza. `anthropic` i `google` nie mają żadnego zastosowania lokalnego, więc wypadają bez kosztu.

**Dlaczego twarde zatrzymanie zamiast ostrzeżenia.** System, który przy błędnej konfiguracji działa dalej i loguje ostrzeżenie, będzie działał dalej — ostrzeżeń nikt nie czyta. Przy aktach karnych cena fałszywego alarmu jest nieporównanie niższa niż cena przeoczenia.

**Dlaczego blokada także na zapisie do bazy.** To bezpośrednia odpowiedź na U-2. Bez niej osoba z dostępem do panelu administracyjnego mogłaby skierować model na zewnątrz, nie dotykając żadnego pliku.

**Dlaczego `net_parse` osobno od `net_app`.** LibreOffice w gotenbergu potrafi pobierać zasoby osadzone w konwertowanym pliku. Pismo od strony przeciwnej z linkowanym obrazem staje się wtedy potwierdzeniem odbioru pod kontrolowanym adresem (zagrożenie I-2). Kontrola aplikacyjna jest tu zawodna; działa dopiero brak trasy.

## Konsekwencje

**Pozytywne:** żaden pojedynczy błąd nie prowadzi do wycieku · izolacja jest testowalna wykonywalnie · dowód dla audytu z art. 21 lit. f ustawy o KSC.

**Negatywne:** trudniejszy merge z upstreamem · konfiguracja sieci wymaga uwagi przy każdej nowej usłudze · twarde zatrzymanie może zablokować start przy literówce w adresie.

## Weryfikacja

`tests/izolacja/` — bramki I-1…I-9, plus **test negatywny**: należy potwierdzić, że testy potrafią paść, tymczasowo dodając trasę. Test bezpieczeństwa, który przechodzi zawsze, jest gorszy niż brak testu.

Dowód końcowy: przechwycenie ruchu podczas pełnego przebiegu dokumentu — zero pakietów wychodzących (O-1).
