# KSC / NIS2 — ocena podmiotowa i mapowanie środków

> **Zastrzeżenie.** Dokument techniczno-organizacyjny, nie opinia prawna. Kwalifikację podmiotową i wykładnię przepisów rozstrzyga prawnik kancelarii. Stan prawny na 14.08.2026 — sprawdzić aktualność przed użyciem.

---

## ⏰ Termin, który biegnie teraz

Nowelizacja ustawy o krajowym systemie cyberbezpieczeństwa (wdrożenie dyrektywy NIS2):

| Data | Zdarzenie |
|---|---|
| 19.02.2026 | Podpis Prezydenta |
| 02.03.2026 | Publikacja w Dzienniku Ustaw |
| 03.04.2026 | **Wejście w życie** |
| **02.10.2026** | **Termin samoidentyfikacji i wpisu do wykazu** ⚠️ |
| 02.04.2027 | Termin wdrożenia środków zarządzania ryzykiem |
| 03.04.2028 | Termin pierwszego audytu dla podmiotów kluczowych |

**Do terminu rejestracyjnego pozostało około 7 tygodni** (stan na 14.08.2026).

Nowelizacja rozszerza zakres z ok. 400 podmiotów do ok. 42 000. Obowiązuje **model samoidentyfikacji** — podmiot sam ocenia, czy podlega, i sam się rejestruje. Brak wpisu nie jest neutralny.

**To zadanie jest niezależne od budowy systemu.** Nie czeka na Fazę 6 ani na PoC — jest pierwszą czynnością obszaru zgodności i wymaga decyzji kancelarii, nie kodu.

---

## Czy kancelaria podlega ustawie?

**Kancelaria nie staje się podmiotem kluczowym ani ważnym z samego faktu bycia kancelarią.** Usługi prawne nie figurują wprost w wykazach sektorowych dyrektywy.

Kwalifikacja wymaga analizy kilku elementów łącznie:

| Element | Pytanie do rozstrzygnięcia |
|---|---|
| Rzeczywisty model działalności | Czy kancelaria świadczy usługi wykraczające poza pomoc prawną — np. zarządzane usługi ICT? |
| Sektor | Czy któraś z linii działalności trafia do wykazu? |
| Progi wielkości | Zatrudnienie i obroty względem progów ustawowych |
| Podmioty powiązane | Czy powiązania kapitałowe zmieniają kwalifikację? |
| Rola w łańcuchu dostaw | Czy kancelaria jest dostawcą podmiotu kluczowego? |

**Prawdopodobny wynik dla typowej kancelarii: nie podlega bezpośrednio.** Ale to musi zostać *ustalone i udokumentowane*, a nie założone — model samoidentyfikacji przenosi ciężar oceny na podmiot.

### Realny wektor: łańcuch dostaw

Nawet gdy kancelaria nie podlega bezpośrednio, art. 21 ust. 2 lit. d dyrektywy nakazuje podmiotom kluczowym i ważnym uwzględniać bezpieczeństwo **relacji z bezpośrednimi dostawcami i usługodawcami**.

Kancelaria obsługująca bank, szpital, operatora energetycznego czy dostawcę usług cyfrowych będzie otrzymywać wymagania bezpieczeństwa **kontraktowo** — ankiety, klauzule, audyty. To dzieje się niezależnie od własnej kwalifikacji.

Wniosek praktyczny: **budujemy do poziomu art. 21 niezależnie od wyniku oceny podmiotowej.** Jeśli obowiązek nie powstanie — mamy przewagę w rozmowach z klientami korporacyjnymi. Jeśli powstanie — jesteśmy gotowi.

---

## Mapowanie art. 21 → środki w tym systemie

| Wymóg art. 21 ust. 2 | Realizacja | Gdzie |
|---|---|---|
| **a)** analiza ryzyka i polityki bezpieczeństwa systemów | Model zagrożeń STRIDE, rejestr ryzyk jako dokument żywy | [`04-model-zagrozen.md`](../04-model-zagrozen.md), [`15-rejestr-ryzyk.md`](../15-rejestr-ryzyk.md) |
| **b)** obsługa incydentów | Runbook z terminami 24 h / 72 h, role, ścieżka decyzyjna | [`10-operacje/runbook-incydent.md`](../10-operacje/runbook-incydent.md) |
| **c)** ciągłość działania, kopie zapasowe, zarządzanie kryzysowe | RPO ≤ 24 h, RTO ≤ 8 h, **testowane** odtworzenie kwartalnie | [`10-operacje/backup-i-dr.md`](../10-operacje/backup-i-dr.md) |
| **d)** bezpieczeństwo łańcucha dostaw | Obrazy przypięte po `sha256`, lokalne lustro, SBOM, weryfikacja przed wniesieniem | [`05-izolacja-i-siec.md`](../05-izolacja-i-siec.md) |
| **e)** bezpieczeństwo nabywania, rozwoju i utrzymania systemów; ujawnianie podatności | Bramka CI na lockfile, SBOM, okno serwisowe na łatki, przegląd podatności | [`10-operacje/runbook-aktualizacje.md`](../10-operacje/runbook-aktualizacje.md) |
| **f)** ocena skuteczności środków | **Testy izolacji jako bramka wykonywalna** + bramki jakościowe | [`11-testy-i-bramki.md`](../11-testy-i-bramki.md) |
| **g)** cyberhigiena i szkolenia | Program szkoleń; **obowiązek szkolenia kierownictwa** wynikający z nowelizacji | plan Fazy 9 |
| **h)** kryptografia i szyfrowanie | Szyfrowanie nośnika, klucz per sprawa, odrębny klucz materiału obrończego, mTLS | [`rodo-rejestr-i-art32.md`](rodo-rejestr-i-art32.md) |
| **i)** bezpieczeństwo zasobów ludzkich, kontrola dostępu, zarządzanie aktywami | Dostęp imienny, zasada wiedzy koniecznej, ściany etyczne, rejestr aktywów | [`08-domena-sprawy.md`](../08-domena-sprawy.md) |
| **j)** MFA lub uwierzytelnianie ciągłe, bezpieczna łączność | MFA obowiązkowe (N-36), mTLS między segmentami, własne CA | [`05-izolacja-i-siec.md`](../05-izolacja-i-siec.md) |

**Wymóg f) jest tu spełniony mocniej niż typowo.** „Ocena skuteczności środków" zwykle oznacza okresowy przegląd dokumentacji. Tutaj skuteczność izolacji jest sprawdzana wykonywalnym testem przy każdym buildzie, a dowodem końcowym jest przechwycenie ruchu sieciowego. To materiał do przedstawienia audytorowi.

---

## Odpowiedzialność kierownictwa

Nowelizacja wprowadza **odpowiedzialność kierownictwa podmiotu** za realizację zadań z zakresu cyberbezpieczeństwa, wraz z sankcjami, oraz obowiązek odbycia szkolenia.

Dla kancelarii oznacza to, że temat nie może zostać w całości scedowany na dostawcę IT — wspólnicy odpowiadają osobiście, a szkolenie jest obowiązkiem, nie zaleceniem.

---

## Zgłaszanie incydentów

Przy obowiązku zgłoszeniowym obowiązuje ścieżka etapowa: **wczesne ostrzeżenie w 24 h**, **zgłoszenie właściwe w 72 h**, sprawozdanie końcowe w terminie miesięcznym.

⚠️ **Kolizja z tajemnicą zawodową.** Zgłoszenie incydentu nie może ujawnić treści objętej tajemnicą adwokacką ani obrończą. Runbook musi określać, co dokładnie trafia do zgłoszenia — zakres i charakter zdarzenia, bez treści akt. Ten punkt wymaga rozstrzygnięcia przez prawnika przed wystąpieniem pierwszego incydentu, nie w jego trakcie.

---

## Zadania — obszar KSC

| # | Zadanie | Termin | Odpowiedzialny |
|---|---|---|---|
| K-1 | **Ocena podmiotowa: czy kancelaria podlega** | do 15.09.2026 | prawnik + wspólnicy |
| K-2 | **Rejestracja w wykazie, jeśli podlega** | **do 02.10.2026** | wspólnicy |
| K-3 | Przegląd umów z klientami pod kątem wymagań łańcucha dostaw | do 31.10.2026 | prawnik |
| K-4 | Szkolenie kierownictwa | do 31.12.2026 | wspólnicy |
| K-5 | Wdrożenie środków art. 21 | do 02.04.2027 | zespół projektu |
| K-6 | Rozstrzygnięcie kolizji zgłoszenie/tajemnica | przed pilotażem | prawnik |
| K-7 | Pierwszy audyt (jeśli podmiot kluczowy) | do 03.04.2028 | audytor zewnętrzny |

**K-1 i K-2 nie zależą od tego projektu i nie powinny na niego czekać.**

## Źródła do weryfikacji

Tekst nowelizacji (Dz.U. 2026 poz. 252) · FAQ Ministerstwa Cyfryzacji · wykaz podmiotów kluczowych i ważnych · dyrektywa UE 2022/2555, art. 21. Aktualność sprawdzić przed każdą decyzją — przepisy i wytyczne są w fazie wdrożeniowej.
