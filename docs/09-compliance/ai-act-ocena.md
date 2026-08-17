# AI Act — ocena wstępna

> **Zastrzeżenie.** Ocena wstępna od strony technicznej, do potwierdzenia przez prawnika. Rozporządzenie UE 2024/1689 wchodzi w życie etapami, a praktyka stosowania dopiero się kształtuje — stan na 14.08.2026, wymaga sprawdzenia aktualności.

---

## Rola kancelarii: podmiot stosujący (deployer)

Kancelaria wdraża system na własny użytek wewnętrzny. Nie wprowadza go do obrotu ani nie udostępnia pod własną marką — więc co do zasady **nie jest dostawcą (provider)**, tylko podmiotem stosującym.

⚠️ **Uwaga na przekroczenie granicy.** Gdyby kancelaria zaczęła udostępniać system innym kancelariom lub klientom — choćby nieodpłatnie — mogłaby stać się dostawcą, z istotnie szerszym zakresem obowiązków. Ma to znaczenie, jeśli projekt kiedykolwiek miałby zostać skomercjalizowany lub udostępniony.

---

## Czy to system wysokiego ryzyka?

**Wstępnie: nie.**

Załącznik III pkt 8 lit. a obejmuje systemy przeznaczone do stosowania **przez organ wymiaru sprawiedliwości lub w jego imieniu** przy badaniu i wykładni faktów i prawa oraz stosowaniu prawa do konkretnego stanu faktycznego.

Kancelaria nie jest organem wymiaru sprawiedliwości ani nie działa w jego imieniu — jest pełnomocnikiem strony. Narzędzie wspiera pracę własną prawnika, nie orzekanie.

**Argumenty wzmacniające tę ocenę:**

| Cecha systemu | Znaczenie |
|---|---|
| Wyjście to materiał roboczy, nie decyzja | Brak automatycznego skutku prawnego |
| Obowiązkowa weryfikacja przez prawnika | Człowiek nie jest formalnością, lecz warunkiem użycia |
| Brak oceny osób, brak profilowania | Poza zakresem innych pozycji Załącznika III |
| Brak dostrajania na danych osobowych | Brak ryzyk związanych z uczeniem |

**Do rozstrzygnięcia przez prawnika:** czy sposób faktycznego użycia nie zbliża systemu do zakresu Załącznika III — np. gdyby analizy trafiały bezpośrednio do pism procesowych bez rzeczywistej weryfikacji. **Kwalifikację determinuje faktyczny sposób użycia, nie deklaracja w dokumentacji.**

---

## Obowiązki, które stosują się mimo braku wysokiego ryzyka

### 1. Kompetencje w zakresie AI (art. 4) — stosuje się

Podmioty stosujące zapewniają odpowiedni poziom kompetencji personelu obsługującego systemy AI, adekwatny do wiedzy, doświadczenia i kontekstu użycia.

**To obowiązek, nie zalecenie.** Realizacja: program szkoleń obejmujący ograniczenia modeli językowych, skłonność do halucynacji, znaczenie kwantyzacji, sposób czytania cytatów i granice weryfikacji maszynowej (co potwierdza, a czego nie — patrz R-4 w DPIA).

Szkolenie łączy się z obowiązkiem szkoleniowym z nowelizacji KSC — jeden program, dwa obowiązki.

### 2. Przejrzystość wobec osób

Osoby, których dane są przetwarzane, powinny wiedzieć o wykorzystaniu narzędzia AI — realizowane przez klauzule informacyjne RODO (zadanie P-4).

### 3. Praktyki zakazane (art. 5) — nie występują

Weryfikacja negatywna: brak systemu punktowej oceny społecznej, brak rozpoznawania emocji, brak identyfikacji biometrycznej, brak przewidywania popełnienia przestępstwa na podstawie profilowania osoby.

⚠️ Ostatni punkt wymaga uwagi w projektowaniu. Agent rozbieżności (A-5) **wskazuje niezgodności między relacjami i zawsze podaje cytaty** — nie ocenia wiarygodności osoby ani nie przewiduje jej zachowania. Ta granica musi zostać utrzymana także w przyszłym rozwoju systemu; przesunięcie w stronę „oceny wiarygodności świadka" zmieniłoby kwalifikację prawną narzędzia.

---

## Modele ogólnego przeznaczenia (GPAI)

Bielik jest modelem otwartym, pobieranym i uruchamianym lokalnie. Obowiązki dostawcy GPAI ciążą na twórcy modelu (SpeakLeash), nie na kancelarii.

Kancelaria pozostaje podmiotem stosującym, **o ile nie dostraja modelu**. Brak dostrajania jest tu decyzją projektową o podwójnym skutku: eliminuje ryzyko utrwalenia danych w wagach (RODO) i nie przesuwa kancelarii w stronę roli dostawcy (AI Act).

---

## Wniosek

| Pytanie | Odpowiedź wstępna |
|---|---|
| Rola kancelarii | Podmiot stosujący |
| Wysokie ryzyko (Zał. III) | Prawdopodobnie nie |
| Praktyki zakazane | Nie występują |
| Art. 4 — kompetencje AI | **Stosuje się — obowiązek szkoleniowy** |
| Obowiązki dostawcy GPAI | Nie dotyczą |
| Ocena zgodności, oznakowanie CE, rejestracja | Nie dotyczą przy powyższej kwalifikacji |

## Zadania

| # | Zadanie | Termin |
|---|---|---|
| AI-1 | Potwierdzenie kwalifikacji przez prawnika | przed pilotażem |
| AI-2 | Program szkoleń (wspólny z KSC) | przed pilotażem |
| AI-3 | Zapis granicy: system nie ocenia wiarygodności osób | wpisane w [`07-agenci.md`](../07-agenci.md) ✅ |
| AI-4 | Ponowna ocena przy każdym rozszerzeniu funkcji | ciągłe |
| AI-5 | Ponowna ocena, gdyby system miał być udostępniony poza kancelarię | warunkowe |
