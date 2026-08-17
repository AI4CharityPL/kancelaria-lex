# Tajemnica zawodowa — wymagania techniczne

> **Zastrzeżenie.** Dokument przekłada obowiązki zawodowe na wymagania techniczne. Wykładnię przepisów rozstrzyga prawnik kancelarii.

---

## Dlaczego to jest ważniejsze od RODO

RODO dopuszcza kompromisy: dane można przetwarzać przy odpowiedniej podstawie, powierzyć procesorowi na podstawie umowy, przekazać poza EOG przy odpowiednich zabezpieczeniach.

**Tajemnica zawodowa takich kompromisów nie zna.** Ujawnienie informacji objętej tajemnicą adwokacką lub radcowską jest naruszeniem obowiązku zawodowego niezależnie od tego, jaką umowę powierzenia podpisano z dostawcą.

To jest właściwe uzasadnienie architektury zamkniętej. RODO samo w sobie nie zabraniałoby korzystania z dostawcy chmurowego przy odpowiedniej umowie. Tajemnica zawodowa — praktycznie zabrania.

---

## Dwa poziomy, dwa reżimy

| | Tajemnica adwokacka / radcowska | **Tajemnica obrończa** |
|---|---|---|
| Zakres | Wszystko, o czym prawnik dowiedział się w związku z pomocą prawną | Fakty poznane przy udzielaniu porady lub prowadzeniu sprawy **jako obrońca** |
| Uchylenie | Wyjątkowo, postanowieniem sądu (art. 180 § 2 k.p.k.) | **Nie podlega uchyleniu** — zakaz przesłuchania obrońcy (art. 178 pkt 1 k.p.k.) |
| Konsekwencja techniczna | Ochrona standardowa podwyższona | **Odrębny magazyn, odrębny klucz, odrębna autoryzacja** |

Różnica jest jakościowa, nie stopniowa. Materiał obrończy jest jedyną kategorią danych w tym systemie, której nie może ujawnić żadna procedura prawna — a zatem jedyną, dla której zabezpieczenie techniczne musi wytrzymać także wobec legalnego żądania wydania systemu.

---

## Wymagania techniczne

### T-1 · Materiał obrończy nie może być rekordem z flagą

Flagę w bazie zmienia się jednym zapytaniem. Kopia zapasowa bazy zawiera wszystko niezależnie od flag. Zajęcie sprzętu daje dostęp do całości.

**Wymaganie:** odrębny magazyn obiektów, szyfrowany kluczem niedostępnym dla procesu obsługującego pozostałe sprawy, za odrębną autoryzacją.

**Skutek:** zrzut głównej bazy — z awarii, kopii zapasowej czy zajęcia sprzętu — nie zawiera materiału obrończego w postaci czytelnej.

### T-2 · Klucz materiału obrończego poza systemem

Klucz nie może leżeć w tym samym miejscu co dane. Docelowo: nośnik sprzętowy (token/HSM) lub przechowywanie rozdzielne z autoryzacją dwuosobową. Utrata klucza oznacza utratę dostępu — kopia klucza wymaga własnej procedury, opisanej w [`10-operacje/backup-i-dr.md`](../10-operacje/backup-i-dr.md).

### T-3 · Zero łączności — bez wyjątków

Trzy warstwy izolacji ([`05-izolacja-i-siec.md`](../05-izolacja-i-siec.md)). Nie ma kategorii „dane mniej wrażliwe, które można wysłać". Sam fakt prowadzenia sprawy jest objęty tajemnicą — metadane też.

### T-4 · Log audytowy jako dowód należytej staranności

W sporze o zachowanie tajemnicy kancelaria musi umieć wykazać, kto miał wgląd w akta. Log podatny na modyfikację nie jest dowodem — stąd łańcuch sum kontrolnych i przechowywanie poza bazą aplikacji.

Log rejestruje dostęp, ale **nie kopiuje treści akt** — inaczej sam stałby się drugim zbiorem objętym tajemnicą.

### T-5 · Ściany etyczne

Konflikt interesów jest naruszeniem zawodowym niezależnie od intencji. Kontrola przy nadaniu dostępu i przy przypisaniu prowadzącego; przełamanie ściany możliwe wyłącznie decyzją administratora, z uzasadnieniem i wpisem audytowym.

### T-6 · Prace deweloperskie na korpusie syntetycznym

Prawnik nie omawia szczegółów sprawy z osobą postronną. Ta sama zasada dotyczy narzędzi: rzeczywiste akta nie trafiają do repozytorium, do środowiska testowego ani do kontekstu narzędzi zewnętrznych.

Stąd `eval/korpus-syntetyczny/` — fikcyjne akta w polskiej konwencji procesowej, zbudowane tak, by odtwarzać strukturę i trudności realnych dokumentów bez odtwarzania realnych danych.

### T-7 · Zgłoszenie incydentu bez ujawnienia treści

Obowiązki zgłoszeniowe (KSC 24 h / 72 h, RODO 72 h) kolidują z tajemnicą. Zgłoszenie musi opisywać charakter i zakres zdarzenia **bez treści objętej tajemnicą**.

Granicę należy ustalić **przed** wystąpieniem incydentu — zadanie K-6 w [`ksc-nis2-mapowanie.md`](ksc-nis2-mapowanie.md). W trakcie incydentu nie ma czasu na taką analizę.

---

## Konsekwencje dla decyzji projektowych

| Decyzja | Uzasadnienie tajemnicą |
|---|---|
| Brak jakiegokolwiek dostawcy chmurowego | Ujawnienie niezależne od umowy powierzenia |
| Usunięcie serwera MCP | Zewnętrzny klient agentowy = kanał ujawnienia |
| Brak dostrajania modelu na aktach | Wagi mogłyby utrwalić treść objętą tajemnicą |
| `gotenberg` bez trasy sieciowej | Pobranie zasobu osadzonego w piśmie potwierdza posiadanie dokumentu |
| Port 5555 zamknięty | Nazwy zadań ujawniają metadane spraw |
| Odrębny magazyn materiału obrończego | Art. 178 pkt 1 k.p.k. — brak trybu uchylenia |
| Korpus syntetyczny w pracach | Akta nie opuszczają kancelarii nawet na potrzeby budowy systemu |

## Do rozstrzygnięcia przez prawnika kancelarii

1. Czy oznaczenie materiału jako obrończy następuje ręcznie przy wgraniu, czy wynika z rodzaju sprawy?
2. Kto może nadać i zdjąć oznaczenie materiału obrończego?
3. Jak wygląda procedura wobec żądania wydania danych organowi — z uwzględnieniem odmiennego reżimu obu tajemnic?
4. Granica treści zgłoszenia incydentu (T-7).
5. Czy dopuszczalne jest przechowywanie akt różnych klientów w jednej instancji, czy potrzebna jest separacja głębsza niż logiczna?
