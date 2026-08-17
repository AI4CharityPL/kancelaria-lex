# Runbook — incydent bezpieczeństwa

> Terminy biegną od **stwierdzenia** incydentu. Zegar startuje wcześniej, niż się wydaje.

## Zegary

| Obowiązek | Termin | Adresat |
|---|---|---|
| Wczesne ostrzeżenie (KSC) | **24 h** | CSIRT właściwy |
| Zgłoszenie właściwe (KSC) | **72 h** | CSIRT właściwy |
| Zgłoszenie naruszenia (RODO art. 33) | **72 h** | UODO |
| Zawiadomienie osób (RODO art. 34) | bez zbędnej zwłoki | osoby, których dane dotyczą |
| Sprawozdanie końcowe (KSC) | miesiąc | CSIRT właściwy |

Obowiązki KSC dotyczą kancelarii **tylko jeśli podlega ustawie** — patrz ocena podmiotowa K-1. Obowiązki RODO stosują się niezależnie.

## ⚠️ Reguła nadrzędna: zgłoszenie bez ujawnienia tajemnicy

Zgłoszenie opisuje **charakter i zakres** zdarzenia — nie treść akt.

| Wolno | Nie wolno |
|---|---|
| „Nieuprawniony dostęp do dokumentów jednej sprawy karnej" | Nazwisk stron, sygnatury, treści dokumentów |
| „Około 40 dokumentów, kategorie danych: art. 9 i art. 10 RODO" | Wyciągów z akt, opisu czynu |
| „Wektor: przejęte konto użytkownika" | — |

Granicę należy ustalić **przed** incydentem (zadanie K-6). W trakcie nie ma na to czasu.

---

## Etap 1 — wykrycie i ocena *(0–4 h)*

**Sygnały:** złamany łańcuch sum kontrolnych w logu audytowym · nieudana próba połączenia wychodzącego · odrzucona próba zapisu `base_url` spoza allowlisty · nietypowy wzorzec dostępu do akt · niezgodność sumy kontrolnej wag · zgłoszenie użytkownika.

**Czynności:**
1. Powiadomienie osoby odpowiedzialnej i IOD.
2. **Zabezpieczenie dowodów przed jakąkolwiek naprawą** — kopia logu audytowego, logów kontenerów, stanu sieci. Naprawa niszczy ślady.
3. Wstępna ocena: co, kiedy, jaki zakres, czy trwa.
4. **Uruchomienie zegara** — zapis godziny stwierdzenia.

**Decyzja:** czy to incydent podlegający zgłoszeniu? Przy wątpliwości — traktuj jak podlegający i weryfikuj dalej. Termin nie czeka na rozstrzygnięcie.

## Etap 2 — powstrzymanie *(0–24 h)*

| Scenariusz | Działanie |
|---|---|
| Przejęte konto | Zablokowanie konta, unieważnienie sesji, reset MFA |
| Nieuprawniony dostęp wewnętrzny | Odebranie uprawnień, zabezpieczenie logu, powiadomienie wspólników |
| Podejrzenie kompromitacji kontenera | Zatrzymanie usługi; segmentacja ogranicza zasięg |
| **Podejrzenie połączenia wychodzącego** | Odłączenie od LAN, przechwycenie ruchu, analiza — patrz niżej |
| Utrata nośnika kopii zapasowej | Ocena, czy kopia była szyfrowana i gdzie był klucz |
| Kompromitacja materiału obrończego | **Ścieżka najwyższego priorytetu** — natychmiast wspólnicy i prawnik |

**Wczesne ostrzeżenie w 24 h**, jeśli obowiązek zgłoszeniowy istnieje. Ostrzeżenie może być niepełne — na tym polega jego rola.

### Podejrzenie połączenia wychodzącego

To scenariusz, który architektura ma czynić niemożliwym. Jeśli wystąpi, oznacza awarię wszystkich trzech warstw naraz i wymaga pełnej rekonstrukcji:

1. Odłączenie fizyczne.
2. Weryfikacja warstwy A: czy w obrazie pojawiły się zakazane pakiety?
3. Weryfikacja warstwy B: czy zmieniono `base_url`? Log audytowy odnotowuje każdą próbę.
4. Weryfikacja warstwy C: czy zmieniono topologię sieci?
5. Analiza przechwyconego ruchu: dokąd, ile, co.
6. Ustalenie, czy doszło do ujawnienia treści objętej tajemnicą.

## Etap 3 — zgłoszenie *(do 72 h)*

Zgłoszenie właściwe: charakter incydentu, kategorie i przybliżona liczba osób, kategorie i przybliżona liczba wpisów, prawdopodobne konsekwencje, podjęte i planowane środki, dane kontaktowe IOD.

**Weryfikacja treści zgłoszenia przez prawnika pod kątem tajemnicy zawodowej — obowiązkowa, przed wysłaniem.**

Zawiadomienie osób (art. 34), jeśli wysokie ryzyko dla praw i wolności. Przy aktach karnych próg wysokiego ryzyka jest osiągany łatwo — dane z art. 9 i 10 z założenia.

## Etap 4 — usunięcie i przywrócenie

Usunięcie przyczyny · przywrócenie z czystej kopii, jeśli integralność jest wątpliwa · **testy izolacji przed przywróceniem do pracy** · obserwacja.

## Etap 5 — wnioski *(do 30 dni)*

Sprawozdanie końcowe. Analiza przyczyny źródłowej. Aktualizacja modelu zagrożeń i rejestru ryzyk. **Dodanie testu, który wykryłby ten incydent wcześniej** — jeśli się nie da, to jest ustalenie samo w sobie.

---

## Kontakty

| Rola | Osoba | Telefon |
|---|---|---|
| Odpowiedzialny za system | _do uzupełnienia_ | |
| IOD | _do uzupełnienia_ | |
| Wspólnik dyżurny | _do uzupełnienia_ | |
| CSIRT właściwy | _do ustalenia po K-1_ | |
| UODO | — | |

⚠️ **Lista kontaktów w wersji papierowej, poza systemem.** Incydent może obejmować niedostępność systemu, w którym trzymamy kontakty.

## Ćwiczenie

Co najmniej raz w roku ćwiczenie na scenariuszu teoretycznym — bez ćwiczenia runbook jest dokumentem, a nie zdolnością. Zalecany scenariusz pierwszy: nieuprawniony dostęp wewnętrzny do akt sprawy karnej, jako najbardziej prawdopodobny w architekturze zamkniętej.
