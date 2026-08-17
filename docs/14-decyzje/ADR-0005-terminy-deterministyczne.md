# ADR-0005 — Terminy procesowe liczone deterministycznie

**Status:** przyjęta · **Data:** 14.08.2026

## Kontekst

Pilnowanie terminów procesowych to jedno z najbardziej wartościowych zastosowań systemu — i jednocześnie najbardziej ryzykowne.

Przeoczony termin oznacza utratę środka zaskarżenia: szkodę dla klienta, zwykle nieodwracalną, oraz odpowiedzialność zawodową prawnika. To jedyny obszar w tym systemie, w którym błąd ma bezpośrednie i mierzalne skutki prawne.

## Rozważane opcje

| Opcja | Ocena |
|---|---|
| **A. Model rozpoznaje zdarzenie, kod liczy termin** ✅ | Wykorzystuje mocne strony obu; arytmetyka testowalna i audytowalna |
| B. Model rozpoznaje i liczy | Model probabilistyczny wykonuje arytmetykę o skutkach prawnych — nieakceptowalne |
| C. Wszystko ręcznie | Bezpieczne, ale system nie wnosi tu żadnej wartości |

## Decyzja

**Opcja A — rozdzielenie odpowiedzialności.**

```
  MODEL          rozpoznaje zdarzenie inicjujące + cytat ze źródła
                 („odpis wyroku z uzasadnieniem doręczono 12.08.2026")
                 → zadanie językowe, do którego model się nadaje
     ▼
  SILNIK REGUŁ   podstawa prawna · długość · sposób liczenia · dni wolne
                 → arytmetyka: kod, testowalny, audytowalny
     ▼
  PRAWNIK        potwierdza. Bez potwierdzenia termin nie jest obowiązujący.
```

## Szczegóły

**Reguły są danymi, nie kodem** (`reguly_terminow.yaml`). Prawnik ma je przejrzeć bez czytania Pythona — a to warunek, żeby ktokolwiek w kancelarii wziął za nie odpowiedzialność.

**Każda reguła wymaga zatwierdzenia** przez prawnika, z podpisem i datą w pliku. Reguła niezatwierdzona działa w trybie „tylko propozycja z ostrzeżeniem".

**Każdy termin przechowuje podstawę prawną i cytat** ze zdarzenia inicjującego — prawnik widzi, skąd wziął się termin, i może to sprawdzić w dokumencie.

**Ostrzeżenie o terminie niepotwierdzonym jest głośniejsze** niż o potwierdzonym. Nierozpoznany termin jest groźniejszy od znanego.

## Konsekwencje

**Pozytywne:** arytmetyka terminu jest testowalna jednostkowo · zmiana przepisu to zmiana danych, nie kodu · reguły podlegają przeglądowi prawniczemu · ryzyko R-5 sprowadzone do poziomu niskiego · pełny ślad audytowy: co, na jakiej podstawie, z jakiego dokumentu.

**Negatywne:** katalog reguł trzeba zbudować i utrzymywać · przy nowelizacji przepisów wymagany przegląd · model może przeoczyć zdarzenie inicjujące — stąd bramka J-8 na poziomie 90% i głośne ostrzeganie o pismach nieprzetworzonych.

## Granica odpowiedzialności

System **wspiera** prowadzenie terminarza. **Nie zwalnia prawnika z obowiązku sprawdzenia terminu w aktach.**

To musi być komunikowane w interfejsie, nie tylko w regulaminie. Narzędzie, któremu użytkownik zaufa bezwarunkowo, jest groźniejsze od braku narzędzia — bo znosi czujność, którą miał wcześniej.

## Powiązania

Agent A-2 w [`../07-agenci.md`](../07-agenci.md) · Model domenowy w [`../08-domena-sprawy.md`](../08-domena-sprawy.md) · Ryzyko R-5 w [`../09-compliance/rodo-dpia.md`](../09-compliance/rodo-dpia.md) · Bramka J-8
