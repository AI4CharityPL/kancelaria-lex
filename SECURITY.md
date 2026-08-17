# Bezpieczeństwo

## Czym ten projekt jest, a czym nie jest

`kancelaria-lex` przetwarza materiał objęty tajemnicą zawodową — w tym akta
niepublicznych spraw karnych. Model zagrożeń jest więc inny niż w typowej
aplikacji webowej: **przeciwnikiem jest nie tylko atakujący z sieci, lecz także
przypadkowy wyciek treści do dostawcy chmurowego** oraz zajęcie sprzętu.

Cała argumentacja projektu opiera się na dwóch własnościach:

1. **Nic nie wychodzi poza urządzenie** — trzy niezależne warstwy izolacji
   (`docs/05-izolacja-i-siec.md`).
2. **Cytat nie może być zmyślony** — model wskazuje numer zdania, treść
   odtwarza kod ze źródła (`docs/14-decyzje/ADR-0007-*`).

**Modyfikacja kodu może usunąć dokładnie te dwie własności.** Wersja
zmodyfikowana przez osoby trzecie nie jest objęta żadnym z zapewnień
w `README.md`.

## Zgłaszanie podatności

Podatności zgłaszaj **prywatnie**, przez „Report a vulnerability" w zakładce
Security repozytorium — nie przez publiczne zgłoszenie w Issues.

W zgłoszeniu **nie umieszczaj treści akt ani żadnych danych rzeczywistych.**
Jeżeli błąd da się pokazać wyłącznie na danych, opisz go na korpusie
syntetycznym z `eval/korpus-syntetyczny/` albo na materiale publicznym.

Czas reakcji: projekt jest prowadzony w ramach wolontariatu, więc nie
deklarujemy SLA. Zgłoszenia dotyczące izolacji sieciowej i weryfikacji
cytatów traktujemy priorytetowo.

## Zakres szczególnie istotny

Zgłoszenia w tych obszarach są najważniejsze — dotyczą własności, na których
opiera się cały projekt:

| Obszar | Dlaczego krytyczny |
|---|---|
| Dowolna ścieżka wysyłająca dane poza urządzenie | Podważa własność nr 1 |
| Sposób na przepuszczenie cytatu niezgodnego ze źródłem | Podważa własność nr 2 |
| Wyjście poza zakres sprawy (cytat z akt innej sprawy) | Ściany etyczne, art. 21 ust. 2 lit. i KSC |
| Wstrzyknięcie instrukcji przez treść dokumentu | Treść akt jest danymi, nigdy poleceniem |
| Odczyt sesji lub podniesienie uprawnień | Rozdzielenie profili i autorstwo wpisów |
| Wyciek treści do logu, dziennika lub audytu | T-4: log rejestruje dostęp, nie kopiuje treści |

## Znane ograniczenia — zgłoszone, nie ukryte

Poniższe są **znane i udokumentowane**. Zgłoszenie ich nie jest podatnością,
ale informacja o sposobie ich wykorzystania — już tak.

- **MFA jest dostępne, ale nie domyślne.** `panel/profile.py` realizuje
  login i hasło (scrypt, sesja po stronie serwera, dławienie serii prób),
  a `panel/totp.py` — drugi składnik TOTP zgodny z RFC 6238 z jednorazowymi
  kodami zapasowymi. **Dopóki użytkownik go nie włączy, logowanie pozostaje
  jednoskładnikowe** i art. 21 ust. 2 lit. j nie jest spełniony.
  Drugi składnik jest też pozorny, gdy aplikacja TOTP stoi na tym samym
  komputerze co panel — tego żaden kod nie sprawdzi.
- **Panel nasłuchuje wyłącznie na `127.0.0.1` i nie ma własnego TLS-a.**
  Udostępnienie w sieci kancelarii wymaga reverse proxy z TLS z własnego CA —
  panel nie jest przeznaczony do wystawienia bez tej warstwy
  (`docs/10-operacje/runbook-wdrozenie.md`).
- **Szyfrowanie nośnika należy do kancelarii.** Baza `panel/dane/panel.sqlite3`
  nie jest szyfrowana w spoczynku przez aplikację. Przy zajęciu
  niezaszyfrowanego dysku akta są czytelne.
- **Kwantyzacja Q4** obniża jakość modelu i zwiększa skłonność do halucynacji.
  Dopuszczalna w profilu rozwojowym, niedopuszczalna przy aktach karnych —
  `docs/12-sprzet-i-koszty.md`.
- **J-3 = 82% przy celu 90%.** System odpowiada na część pytań, na które akta
  nie dają podstawy. Cytat jest wtedy prawdziwy, ale nie popiera tezy.
  Dlatego **cytat trzeba kliknąć i sprawdzić** — `docs/22-wyniki-docelowe.md`,
  RY-16 w `docs/15-rejestr-ryzyk.md`.

## Zasada dotycząca danych w repozytorium

**Rzeczywiste akta nigdy nie trafiają do repozytorium** (wymaganie T-6,
`docs/09-compliance/tajemnica-zawodowa.md`). Dotyczy to także zgłoszeń
błędów, testów odtwarzających problem i zrzutów ekranu.

Jeżeli zauważysz, że do repozytorium trafiły dane rzeczywiste — zgłoś to
prywatną ścieżką powyżej, traktując to jako incydent, a nie jako zwykły błąd.
