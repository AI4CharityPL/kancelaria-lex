# Korpus syntetyczny

**Wszystkie dokumenty w tym katalogu są fikcyjne.** Osoby, sprawy, sygnatury i zdarzenia zostały wymyślone na potrzeby testów.

## Dlaczego korpus syntetyczny

Prawnik nie omawia szczegółów sprawy z osobą postronną. Ta sama zasada dotyczy narzędzi: rzeczywiste akta nie trafiają do repozytorium, do środowiska testowego ani do kontekstu narzędzi zewnętrznych (wymaganie T-6 w [`../../docs/09-compliance/tajemnica-zawodowa.md`](../../docs/09-compliance/tajemnica-zawodowa.md)).

Korpus ma odtwarzać **strukturę i trudności** realnych dokumentów, nie realne dane.

## Zasady tworzenia

| Zasada | Powód |
|---|---|
| Nazwiska z listy fikcyjnej, nigdy z prawdziwych spraw | Oczywisty |
| Sygnatury w prawidłowym formacie, ale nieistniejące numery | Testuje walidację wzorca |
| Daty spójne wewnętrznie | Testuje silnik terminów |
| **Celowe rozbieżności między dokumentami** | Testuje agenta A-5 |
| **Celowe braki informacji** | Testuje odmowę odpowiedzi (bramka J-3) |
| Skany o różnej jakości | Testuje CER (bramki J-5, J-6) |
| Warianty z wstrzykniętym poleceniem | Osobno w [`../../tests/injection/`](../../tests/injection/) |

## Zawartość

| Plik | Rodzaj | Testuje |
|---|---|---|
| `01-protokol-przesluchania-kowalski.txt` | protokół przesłuchania świadka | ekstrakcja, cytowanie |
| `02-protokol-przesluchania-nowak.txt` | protokół — **rozbieżny z 01** | agent rozbieżności A-5 |
| `03-postanowienie-doreczenie.txt` | postanowienie z datą doręczenia | silnik terminów A-2 |
| `04-akt-oskarzenia.txt` | akt oskarżenia | klasyfikacja, metadane |

Dokumenty są krótkie celowo — mają testować mechanikę, nie wydajność. Korpus wydajnościowy (setki stron) powstaje osobno w Fazie 7.

## Gold set

Pytania i zweryfikowane odpowiedzi: [`../gold-set/`](../gold-set/).

⚠️ Odpowiedzi w gold secie są weryfikowane **przez człowieka**. Świadomie nie używamy modelu jako sędziego — sędzia oparty na LLM przepuszcza halucynacje (ADR-0006).
