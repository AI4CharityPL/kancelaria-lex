# Kopie zapasowe i odtwarzanie

## Cele

| Parametr | Wartość | Znaczenie |
|---|---|---|
| RPO | ≤ 24 h | Maksymalna utrata pracy |
| RTO | ≤ 8 h | Maksymalny czas niedostępności |
| Test odtworzenia | kwartalnie | **Kopia nieprzetestowana nie jest kopią** |
| Retencja kopii | 30 dni dziennych + 12 miesięcznych | |

## Co obejmuje kopia

| Zasób | Uwagi |
|---|---|
| Baza PostgreSQL | Zrzut spójny, wraz z wektorami |
| Magazyn obiektów (MinIO) | Oryginały dokumentów |
| **Magazyn materiału obrończego** | **Osobna kopia, osobny klucz** — patrz niżej |
| Log audytowy | Poza bazą aplikacji; kopia zachowuje łańcuch sum |
| Konfiguracja i compose | Wersjonowane w repozytorium |
| Wagi modeli | **Nie w kopii dziennej** — niezmienne, duże; odtwarzane z paczki offline wg manifestu w `models/` |

Wyłączenie wag z kopii dziennej jest celowe: to kilkanaście gigabajtów niezmiennych danych, które można odtworzyć z paczki instalacyjnej. Kopiowanie ich codziennie wydłużałoby okno i zajmowało nośnik bez korzyści.

## Zasady

1. **Kopia jest szyfrowana**, klucz przechowywany rozdzielnie od nośnika.
2. Nośnik kopii przechowywany poza serwerownią; utrata nośnika jest realnym scenariuszem incydentu.
3. **Materiał obrończy ma odrębną kopię i odrębny klucz** — odtworzenie głównej kopii nie odtwarza materiału obrończego i nie daje do niego dostępu.
4. Kopia nie opuszcza kontroli kancelarii. Żadnej usługi chmurowej — dotyczy jej ta sama zasada co danych produkcyjnych.
5. Test odtworzenia na **osobnej maszynie**, nie na produkcyjnej.

## Klucze — punkt najbardziej zawodny

Najczęstszy sposób, w jaki kopie zapasowe zawodzą, to nie utrata danych, tylko **utrata klucza**.

| Klucz | Przechowywanie | Kopia |
|---|---|---|
| Klucz kopii głównej | Sejf kancelarii + druga lokalizacja | Dwie kopie, rozdzielnie |
| **Klucz materiału obrończego** | Nośnik sprzętowy, autoryzacja dwuosobowa | Kopia w depozycie, procedura dostępu opisana |
| Klucz nośnika | j.w. | j.w. |

Utrata klucza materiału obrończego oznacza **nieodwracalną utratę dostępu** do najważniejszych danych w systemie. Procedura depozytu wymaga zatwierdzenia przez wspólników — jest to decyzja o kompromisie między ryzykiem utraty a ryzykiem ujawnienia.

## Test odtworzenia — procedura kwartalna

1. Czysta maszyna, bez kontaktu z produkcją.
2. Odtworzenie bazy i magazynu obiektów z kopii.
3. Odtworzenie wag modeli z paczki offline, **weryfikacja sum kontrolnych**.
4. Uruchomienie stosu; **testy izolacji** — odtworzone środowisko musi być tak samo odcięte.
5. Weryfikacja: liczba spraw i dokumentów zgodna · **łańcuch sum logu audytowego nieprzerwany** · przebieg dymny (dokument → OCR → indeks → zapytanie z cytatami).
6. Osobno: test odtworzenia materiału obrończego, z procedurą dostępu do klucza.
7. **Pomiar rzeczywistego czasu** — jeśli przekracza RTO, RTO jest fikcją i wymaga korekty albo usprawnienia procedury.
8. Wpis do dziennika; zniszczenie danych z maszyny testowej.

Krok 5 z weryfikacją łańcucha logu audytowego jest istotny: kopia, która zrywa łańcuch, podważa wartość dowodową logu.

## Scenariusze awarii

| Scenariusz | Reakcja |
|---|---|
| Awaria dysku | Odtworzenie z ostatniej kopii dziennej, w granicach RTO |
| Uszkodzenie bazy | Odtworzenie punktowe |
| Błąd ludzki (usunięcie sprawy) | Odtworzenie wybiórcze z kopii |
| Oprogramowanie szantażujące | Odtworzenie z kopii poza siecią; segmentacja ogranicza zasięg |
| Utrata pomieszczenia (pożar, zalanie) | Odtworzenie na nowym sprzęcie z kopii z drugiej lokalizacji |
| **Zajęcie sprzętu** | Materiał obrończy pozostaje nieczytelny bez odrębnego klucza |

Ostatni wiersz jest właściwym uzasadnieniem odrębnego kluczowania — patrz [`09-compliance/tajemnica-zawodowa.md`](../09-compliance/tajemnica-zawodowa.md), wymaganie T-1.

## Dziennik

`infra/dziennik-kopii.md` — data testu, czas odtworzenia, wynik weryfikacji, wykryte problemy. Materiał dowodowy dla art. 32 lit. c i d RODO oraz art. 21 lit. c ustawy o KSC.
