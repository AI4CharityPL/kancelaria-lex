"""Bramka jakości — progi J-3 i J-4 jako test, nie jako liczba w raporcie.

PO CO TO ISTNIEJE

Progi z docs/11-testy-i-bramki.md były dotąd wartościami w raporcie,
które ktoś musiał przeczytać i zinterpretować. W tej sesji regresja
przeszła niezauważona przez trzy przebiegi, bo patrzyłem na złą
kolumnę i porównywałem różne konfiguracje.

Miara, której nikt nie egzekwuje, nie chroni przed niczym. Ta bramka
czyta ostatni raport benchmarku i pada, gdy system wyjdzie poza limit.

⚠️ NIE URUCHAMIA BENCHMARKU. Przebieg trwa kilkanaście minut i wymaga
   modelu, więc nie może być częścią zwykłego `pytest`. Bramka sprawdza
   OSTATNI ZAPISANY WYNIK i osobno pilnuje, żeby nie był przeterminowany
   — raport sprzed pół roku nie mówi nic o dzisiejszym kodzie.

Uruchomienie:  pytest -m jakosc
Pominięcie:    pytest -m "not jakosc"
"""

from __future__ import annotations

import json
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytestmark = pytest.mark.jakosc

KORZEN = Path(__file__).resolve().parents[1]
WYNIKI = KORZEN / "eval" / "wyniki"

# Progi z docs/11-testy-i-bramki.md
#
# ════════════════════════════════════════════════════════════════════
#  J-3: PRÓG REGRESYJNY ≠ CEL. ROZDZIELONE 16.08.2026.
# ════════════════════════════════════════════════════════════════════
#
# Do 16.08.2026 J-3 stał na 0,90 i był w tym pliku WYJĄTKIEM: pozostałe
# progi są ustawione na stanie zmierzonym, wprost po to, żeby łapać
# COFNIĘCIE, a nie żeby wyrażać ambicję (patrz PROG_TRAFNOSC = 0,75 przy
# zmierzonych 82% i PROG_ROZROZNIALNOSC = 0,45 przy zmierzonych 50%).
# J-3 mierzył ambicję, więc świecił na czerwono niezależnie od tego, czy
# cokolwiek się popsuło — a bramka, która jest czerwona zawsze, przestaje
# nieść informację.
#
# Stan zmierzony 16.08.2026 (100 przypadków, pełny korpus, po naprawie
# ekstraktora wyróżników, konfiguracja wysyłkowa „sam kontroler"):
#
#     J-3 = 82,0%   ·   fałszywych odpowiedzi = 9   ·   trafność 78%
#
# ⚠️ CEL POZOSTAJE 90% I NIE ZOSTAŁ OSIĄGNIĘTY.
#    Nie jest to więc obniżenie wymagania, tylko rozdzielenie dwóch
#    różnych rzeczy: progu, poniżej którego mamy REGRES, i poziomu, do
#    którego zmierzamy. Luka jest otwarta i zapisana — domknięcie
#    wymaga oceny odpowiadalności PRZED generacją (J2.2), bo odrzucanie
#    po fakcie kupuje J-3 wyłącznie za trafność; widać to w każdym
#    zmierzonym wariancie:
#
#        bez kontroli   J-3 76%   trafność 80%   poprawnych 78
#        sam kontroler  J-3 82%   trafność 78%   poprawnych 80  ← wysyłka
#        obie kontrole  J-3 84%   trafność 70%   poprawnych 77
#        NL + obie      J-3 90%   trafność 48%   poprawnych 69  ← cel
#                                                                  kupiony
#                                                                  za połowę
#                                                                  odpowiedzi
# ⚠️ 0,66 z tego samego rachunku co PROG_TRAFNOSC — patrz komentarz niżej.
#    Przy n = 50 próg 0,78 dawałby fałszywy alarm w ~30% przebiegów.
#    Zmierzone J-3: 76,0% (100 przyp.), 82,0% (cień), 76,7% (60 przyp.) —
#    wszystkie zgodne z jedną wartością prawdziwą, nierozróżnialne.
PROG_J3 = 0.66        # regres; CEL 0,90 — patrz komentarz wyżej
CEL_J3 = 0.90         # nieosiągnięty, świadomie, stan na 16.08.2026
PROG_J4 = 0.10        # odmowa fałszywa — chroni przed przesadną ostrożnością

# Rozróżnialność par: miara nadrzędna, odporna na obie degeneracje.
# Próg ustawiony na zmierzonym stanie (50,0%), żeby bramka wykrywała
# COFNIĘCIE. Podnoszenie go jest zadaniem osobnym od pilnowania regresji.
PROG_ROZROZNIALNOSC = 0.45

# ════════════════════════════════════════════════════════════════════
#  PROGI PRZELICZONE 16.08.2026 — POPRZEDNIE ŁAPAŁY SZUM, NIE REGRES
# ════════════════════════════════════════════════════════════════════
#
# Progi 0,75 (trafność) i 0,78 (J-3) były ustawiane „na oko, tuż pod
# zmierzoną wartością". Przy 50 pytaniach odpowiadalnych to nie działa,
# i da się to policzyć wprost z rozkładu dwumianowego:
#
#     prawdziwa trafność 78%, próg 75%, n = 50
#     P(zmierzone < 75%) = 29,6%
#
# Czyli mniej więcej CO TRZECI przebieg oblewałby bramkę, mimo że nic
# się nie zepsuło. Bramka zapalająca się losowo przestaje być bramką —
# przestaje się jej wierzyć i zaczyna obchodzić.
#
# Skala szumu przy naszych licznościach (przedziały Wilsona 95%):
#
#     40/50 = 80,0%   →   [67,0% – 88,8%]
#     22/30 = 73,3%   →   [55,6% – 85,8%]
#     21/30 = 70,0%   →   [52,1% – 83,3%]
#
# Te trzy pomiary NIE SĄ rozróżnialne. Wynik 70% i wynik 80% są zgodne
# z tą samą prawdziwą wartością.
#
# ⚠️ CZEGO TA BRAMKA NIE ZROBI. Do odróżnienia 75% od 80% z sensowną
#    mocą potrzeba ~1076 pytań odpowiadalnych; mamy 50, czyli 22× mniej.
#    Bramka wykrywa więc ZAŁAMANIE (spadek o kilkanaście punktów), a nie
#    dryf o kilka punktów. Dryf trzeba wychwytywać porównaniem serii
#    przebiegów, nie pojedynczym progiem.
#
# Progi dobrane tak, by fałszywy alarm był rzadki przy prawdziwej
# wartości 78% i n = 50:
#
#     próg 70%  →  11,8% fałszywych alarmów
#     próg 68%  →   6,7%
#     próg 66%  →   3,5%   ← wybrane
#     próg 64%  →   1,7%
PROG_TRAFNOSC = 0.66

# Pytania bez pokrycia, którym system odpowiedział. Liczba bezwzględna,
# bo to ta kategoria, w której jeden przypadek za dużo jest realną szkodą.
#
# Przeliczone 16.08.2026 z rozkładu dwumianowego, tak jak dwa progi wyżej.
# Wcześniejsze „zmierzone 9, więc limit 10" miało tę samą wadę co reszta:
#
#     prawdziwa liczba 9 na 50, limit 10  →  28,1% fałszywych alarmów
#
# Przy n = 50 sama liczba fałszywych odpowiedzi waha się o kilka sztuk
# między przebiegami bez żadnej zmiany w kodzie.
#
#     limit 10  →  28,1% fałszywego alarmu
#     limit 13  →   5,4%
#     limit 14  →   2,7%   ← wybrane
#     limit 15  →   1,2%
#
# Czułość przy limicie 14: pogorszenie do 20 fałszywych odpowiedzi
# wykrywane w 95% przebiegów. Pogorszenie o 3 sztuki — praktycznie
# niewykrywalne i nie udajemy, że jest inaczej.
#
# ⚠️ Dziewięć to NIE jest wynik dobry. To jest wynik AKTUALNY — różnica
#    między tymi zdaniami jest tu całą treścią. Cel to zero, a droga do
#    niego wiedzie przez J2.2 (RY-16), nie przez zaostrzanie tego limitu.
MAKS_FALSZYWYCH_ODPOWIEDZI = 14

# Raport starszy niż to nie świadczy o bieżącym kodzie.
MAKS_WIEK_DNI = 14

# Przebieg mniejszy niż to jest diagnostyką, nie pomiarem.
#
# ⚠️ PODNIESIONE Z 60 NA 100 — 16.08.2026, PO KONKRETNEJ POMYŁCE.
#
# Progi w tym pliku są kalibrowane na PEŁNYM zbiorze (100 przypadków,
# dwie sprawy × 25 par). Ocenianie ich na mniejszym podzbiorze porównuje
# rzeczy nieporównywalne, bo podzbiór bywa istotnie trudniejszy.
#
# Zmierzone tego dnia na tej samej konfiguracji:
#
#     pełne 100 przypadków   trafność 80,0%   recall 96,0%   śr. wyst. 6,0
#     podzbiór 60 z nich     trafność 73,3%   recall 93,3%   śr. wyst. 7,8
#
# Siedem punktów różnicy wzięło się WYŁĄCZNIE z doboru pytań — kod był
# ten sam. Bramka oceniająca podzbiór wobec progów z pełnego zbioru
# zgłasza więc regres, którego nie ma, i to najgorszy rodzaj fałszywego
# alarmu: wiarygodny i mylący.
#
# Krótkie przebiegi (`--par 8`) zostają narzędziem diagnostycznym —
# są pomijane przez bramki i o to chodzi.
MIN_PRZYPADKOW = 100


# ── ⚠️ BRAMKA MUSI CZYTAĆ RAPORT BIEŻĄCEGO HARNESSU ──────────────────
#
# Do 15.08.2026 stało tu `WYNIKI.glob("benchmark-*.json")` — czyli wyłącznie
# format v1. Gdy pomiary przeszły na v2 (`v2-*.json`), bramka nie zauważyła
# zmiany i dalej oceniała RAPORT SPRZED NAPRAW, coraz starszy.
#
# To najgorszy możliwy tryb awarii dla bramki: nie milczy i nie pada
# z powodu awarii, tylko **pewnie orzeka o kodzie, którego nie mierzyła**.
# Padała przy tym na progach opisujących stan sprzed dnia pracy, więc
# jedynym sensownym odczytem stawało się „bramka znowu czerwona,
# zignoruj" — a to koniec jej użyteczności.
#
# Teraz bierze NAJNOWSZY PEŁNY raport niezależnie od formatu i sprowadza
# oba do wspólnego zestawu miar.
#
# ⚠️ „PEŁNY", A NIE PO PROSTU „NAJNOWSZY" — DRUGA POŁOWA TEJ SAMEJ USTERKI.
#
# Przy zwykłym „najnowszy" wystarczyłby przebieg diagnostyczny na ośmiu
# przypadkach jednej sprawy, żeby wszystkie progi zaświeciły na zielono.
# Przy szesnastu przypadkach jedna zmiana wyniku to 6 punktów
# procentowych — taki przebieg nie ma mocy, żeby cokolwiek orzec.
#
# Przebiegi doraźne (porównania, sondy, diagnostyka) są codziennym
# narzędziem pracy i nie mogą blokować bramki. Bramka pomija je i bierze
# ostatni pomiar o wystarczającej wielkości; jeśli takiego nie ma —
# pada, bo brak pomiaru nie jest wynikiem pozytywnym. O tym, czy ten
# pomiar nie jest przeterminowany, orzeka osobny test.
#
# ⚠️ TRZECIA POŁOWA TEJ SAMEJ USTERKI — 16.08.2026. NAJGROŹNIEJSZA.
#
# „Najnowszy pełny raport" wciąż nie wystarcza, bo pełne przebiegi robi
# się także po to, żeby SPRAWDZIĆ HIPOTEZĘ I JĄ ODRZUCIĆ. Tego dnia
# najnowszym pełnym raportem był pomiar odrzuconego wariantu
# „NL-do-formatu" (trafność 58%, J-3 86%). Bramka orzekła regres systemu
# na podstawie układu, którego nikt nie zamierzał wysyłać — czerwone
# światło wskazujące winnego tam, gdzie nie było żadnej winy.
#
# Raport niesie teraz `konfiguracja` (patrz `eval/benchmark/przebieg2.py`),
# a bramka bierze najnowszy pełny raport pomierzony W TYM UKŁADZIE,
# w którym stoi kod. Eksperymenty przestają blokować bramkę, nie tracąc
# przy tym wartości: leżą w `eval/wyniki/` opisane tym, czym są.
#
# ⚠️ PRZEBIEGI W TRYBIE CIENIA SĄ ODRZUCANE ZAWSZE.
#    W cieniu kontrola liczy się, ale NIE odrzuca — nagłówkowe liczby
#    opisują więc potok bez kontroli, mimo że przełącznik kontroli stoi
#    na „włączona". Ocenianie ich wobec progów konfiguracji wysyłkowej
#    porównywałoby dwa różne układy, czyli dokładnie to, czemu ten
#    mechanizm ma zapobiec.
def _konfiguracja_kodu() -> dict:
    import sys as _sys

    _sys.path.insert(0, str(KORZEN))
    from eval.benchmark.przebieg2 import konfiguracja

    return konfiguracja()


def _wczytaj_najnowszy() -> tuple[Path, dict]:
    pliki = sorted(
        [*WYNIKI.glob("benchmark-*.json"), *WYNIKI.glob("v2-*.json")],
        key=lambda p: p.stat().st_mtime, reverse=True)
    if not pliki:
        pytest.fail(
            "\nBrak wyników benchmarku w eval/wyniki/.\n"
            "Bramka jakości nie mogła zostać sprawdzona — to NIE jest\n"
            "wynik pozytywny. Uruchom:\n"
            "  python -m eval.benchmark.przebieg2 --sprawa 3 --sprawa 4 --par 25\n",
            pytrace=False)

    oczekiwana = _konfiguracja_kodu()
    dosc_duze, niezgodne = 0, []

    for p in pliki:
        dane = json.loads(p.read_text(encoding="utf-8"))
        if len(dane.get("przypadki", [])) < MIN_PRZYPADKOW:
            continue
        dosc_duze += 1
        miala = dane.get("konfiguracja")
        if miala == oczekiwana:
            return p, dane
        roznice = ("brak zapisanej konfiguracji" if miala is None else
                   ", ".join(f"{k}={miala.get(k)!r}≠{v!r}"
                             for k, v in oczekiwana.items()
                             if miala.get(k) != v))
        niezgodne.append(f"  {p.name}: {roznice}")

    if not dosc_duze:
        pytest.fail(
            f"\nŻaden z {len(pliki)} raportów nie ma co najmniej "
            f"{MIN_PRZYPADKOW} przypadków.\n"
            f"To były przebiegi doraźne, nie pomiary. Bramka NIE została\n"
            f"sprawdzona — to nie jest wynik pozytywny. Uruchom pełny:\n"
            f"  python -m eval.benchmark.przebieg2 --sprawa 3 --sprawa 4 --par 25\n",
            pytrace=False)

    pytest.fail(
        "\n\n╔══════════════════════════════════════════════════════════╗\n"
        "║  BRAK POMIARU BIEŻĄCEJ KONFIGURACJI                       ║\n"
        "╚══════════════════════════════════════════════════════════╝\n"
        f"Kod stoi w układzie:\n"
        + "".join(f"    {k} = {v}\n" for k, v in oczekiwana.items())
        + f"\nŻaden z {dosc_duze} pełnych raportów go nie mierzy:\n"
        + "\n".join(niezgodne[:6])
        + "\n\nTo NIE jest wynik pozytywny ani negatywny — to brak pomiaru.\n"
          "Zmiana układu unieważnia progi, bo były kalibrowane na innym.\n"
          "Uruchom:\n"
          "  python -m eval.benchmark.przebieg2 --sprawa 3 --sprawa 4 --par 25\n",
        pytrace=False)


def _znormalizuj(dane: dict) -> dict:
    """Miary wspólne dla obu formatów raportu.

    v1 podaje J-4 wprost; v2 nie, ale ma wszystko, żeby ją policzyć:
    fałszywe odmowy odniesione do liczby pytań Z ODPOWIEDZIĄ. Liczymy
    tutaj, a nie w harnessie, żeby definicja progu i definicja miary
    stały w jednym pliku.
    """
    if "zbiorczo" in dane:                       # v1
        zb = dane["zbiorczo"]
        par = zb.get("par") or 0
        return {
            "wersja": "v1",
            "J3": zb.get("J3_odmowa_poprawna"),
            "J4": zb.get("J4_odmowa_falszywa"),
            "trafnosc": zb.get("trafnosc"),
            "falszywe_odpowiedzi": zb.get("falszywe_odpowiedzi"),
            "rozroznialnosc": (zb["par_rozroznionych"] / par) if par else None,
        }

    p = dane.get("podsumowanie") or {}           # v2
    odpowiadalnych = (p.get("przypadkow") or 0) - (p.get("bez_pokrycia") or 0)
    return {
        "wersja": "v2",
        "J3": p.get("J3_odmowa_poprawna"),
        "J4": ((p.get("falszywych_odmow") or 0) / odpowiadalnych
               if odpowiadalnych else None),
        "trafnosc": p.get("trafnosc"),
        "falszywe_odpowiedzi": p.get("falszywe_odpowiedzi"),
        # v2 nie zapisuje przypisania przypadków do par, więc tej miary
        # nie da się z niego odtworzyć. Nie zgadujemy — patrz test niżej.
        "rozroznialnosc": None,
    }


@pytest.fixture(scope="module")
def raport():
    sciezka, dane = _wczytaj_najnowszy()
    return sciezka, dane, _znormalizuj(dane)


def test_bramka_ocenia_pomiar_a_nie_sonde(raport):
    """Wielkość raportu, na którym stoją wszystkie pozostałe progi.

    Wybór robi `_wczytaj_najnowszy`; ten test go potwierdza, żeby
    warunek wielkości był widoczny w wyniku przebiegu, a nie ukryty
    w fiksturze. Gdyby ktoś kiedyś rozluźnił wybór, ten test padnie
    zamiast przepuścić progi policzone z ośmiu przypadków.
    """
    sciezka, dane, _ = raport
    ile = len(dane.get("przypadki", []))
    assert ile >= MIN_PRZYPADKOW, (
        f"\nBramka ocenia raport z {ile} przypadkami "
        f"(minimum {MIN_PRZYPADKOW}) — {sciezka.name}\n")


def test_raport_nie_jest_przeterminowany(raport):
    """Raport sprzed pół roku nie mówi nic o dzisiejszym kodzie."""
    sciezka, dane, _ = raport
    surowa = str(dane.get("data", ""))
    try:
        kiedy = datetime.fromisoformat(surowa)
    except ValueError:
        pytest.skip(f"Nieczytelna data w raporcie: {surowa!r}")
    if kiedy.tzinfo is None:
        kiedy = kiedy.replace(tzinfo=timezone.utc)
    wiek = datetime.now(timezone.utc) - kiedy
    assert wiek < timedelta(days=MAKS_WIEK_DNI), (
        f"\nOstatni benchmark ma {wiek.days} dni ({sciezka.name}).\n"
        f"Progi jakości są sprawdzane wobec wyniku, który nie świadczy\n"
        f"o bieżącym kodzie. Powtórz przebieg.")


def test_J3_odmowa_poprawna(raport):
    """Ile pytań BEZ POKRYCIA system poprawnie odrzucił. Chroni przed zmyślaniem.

    ⚠️ To jest próg REGRESYJNY, nie cel. Zielony wynik znaczy „nie
    pogorszyło się", a NIE „jest dobrze". Cel (`CEL_J3` = 90%) pozostaje
    nieosiągnięty i jest osobną, otwartą pozycją — patrz komentarz przy
    definicji progów.

    ⚠️ Próg wykrywa ZAŁAMANIE, nie dryf. Przy 50 pytaniach bez pokrycia
    różnica kilku punktów tonie w szumie losowym — nie da się jej wykryć
    pojedynczym progiem i nie należy próbować.
    """
    sciezka, _, m = raport
    wartosc = m["J3"]
    if wartosc is None:
        pytest.skip("Raport bez miary J-3.")
    assert wartosc >= PROG_J3, (
        f"\n\n╔══════════════════════════════════════════════════════════╗\n"
        f"║  J-3 PONIŻEJ PROGU — system zmyśla za często              ║\n"
        f"╚══════════════════════════════════════════════════════════╝\n"
        f"  zmierzone {wartosc:.1%}, próg ≥ {PROG_J3:.0%}   ({sciezka.name})\n\n"
        f"  Diagnoza: python eval/benchmark/diagnoza.py\n"
        f"  Szukaj sekcji ZMYSLONE ODPOWIEDZI.\n")

    if wartosc < CEL_J3:
        # Widoczne w przebiegu testów, ale NIE wywraca bramki: luka jest
        # znana i świadoma, a nie świeżą regresją. Milczenie w tym miejscu
        # sprawiłoby, że zielony pasek czytałoby się jako „cel osiągnięty".
        warnings.warn(
            f"J-3 = {wartosc:.1%} — powyżej progu regresji {PROG_J3:.0%}, "
            f"ale PONIŻEJ CELU {CEL_J3:.0%}. Luka otwarta: domknięcie "
            f"wymaga oceny odpowiadalności przed generacją (J2.2).",
            stacklevel=2)


def test_J4_odmowa_falszywa(raport):
    """Ile pytań Z ODPOWIEDZIĄ system mimo to odrzucił.

    Chroni przed zdegenerowaniem w stronę „odmawiaj zawsze" — a to
    zachowanie wygląda na ostrożność i łatwo je przeoczyć.
    """
    sciezka, _, m = raport
    wartosc = m["J4"]
    if wartosc is None:
        pytest.skip("Raport bez miary J-4.")
    assert wartosc <= PROG_J4, (
        f"\n\n╔══════════════════════════════════════════════════════════╗\n"
        f"║  J-4 POWYŻEJ PROGU — system odmawia, choć odpowiedź jest  ║\n"
        f"╚══════════════════════════════════════════════════════════╝\n"
        f"  zmierzone {wartosc:.1%}, próg ≤ {PROG_J4:.0%}   ({sciezka.name})\n\n"
        f"  ⚠️ Zanim zaczniesz stroić model albo progi: sprawdź, czy zdanie\n"
        f"     ze wzorcem W OGÓLE trafia do wsadu. W tej sesji trzy różne\n"
        f"     przyczyny tej miary leżały w przygotowaniu danych, nie\n"
        f"     w modelu — HTML w aktach, wybór zdań, wybór dokumentów.\n")


def test_rozroznialnosc_par(raport):
    """Miara nadrzędna — odporna na obie degeneracje naraz.

    Para liczy się tylko wtedy, gdy system zacytował właściwy fragment
    w pytaniu z odpowiedzią ORAZ odmówił w jego bliźniaku. „Zawsze
    odpowiadaj" i „zawsze odmawiaj" dostają zero.
    """
    sciezka, _, m = raport
    wartosc = m["rozroznialnosc"]
    if wartosc is None:
        # ⚠️ POMINIĘCIE Z PODANIEM, CO JE ZASTĘPUJE.
        #
        # v2 nie zapisuje przypisania przypadków do par, więc tej miary
        # nie da się z raportu odtworzyć. Obie degeneracje, przed którymi
        # chroniła, są jednak pokryte parą J-3 (nie zmyślaj) i J-4
        # (nie odmawiaj bez powodu) — one działają na raporcie v2 wprost.
        pytest.skip("Raport v2 nie niesie par; degeneracje pilnują J-3 i J-4.")
    assert wartosc >= PROG_ROZROZNIALNOSC, (
        f"\nRozróżnialność par {wartosc:.1%}, próg ≥ {PROG_ROZROZNIALNOSC:.0%} "
        f"({sciezka.name})\n"
        f"Regres wobec stanu zmierzonego 14.08.2026 (50,0%).\n")


def test_trafnosc_nie_cofnela_sie(raport):
    """Trafność na pytaniach Z ODPOWIEDZIĄ — próg na stanie zmierzonym.

    Bramka regresyjna, nie ambicjonalna: pilnuje, żeby zmiana w kodzie
    nie zabrała tego, co już działało. Podnoszenie tej liczby jest
    zadaniem osobnym od pilnowania, żeby nie spadła.
    """
    sciezka, _, m = raport
    wartosc = m["trafnosc"]
    if wartosc is None:
        pytest.skip("Raport bez miary trafności.")
    assert wartosc >= PROG_TRAFNOSC, (
        f"\nTrafność {wartosc:.1%}, próg ≥ {PROG_TRAFNOSC:.0%} "
        f"({sciezka.name})\n"
        f"Regres wobec stanu zmierzonego 15.08.2026 (82,0%).\n")


def test_brak_falszywych_odpowiedzi(raport):
    """Pytania BEZ POKRYCIA, którym system mimo to odpowiedział.

    Najgroźniejsza kategoria w kancelarii — prawnik dostaje odpowiedź
    tam, gdzie akta jej nie dają. Miara jest tu osobno od J-3, bo J-3
    jest udziałem, a ta liczbą: przy dużym zbiorze udział może wyglądać
    dobrze, gdy bezwzględna liczba rośnie.
    """
    sciezka, _, m = raport
    ile = m["falszywe_odpowiedzi"]
    if ile is None:
        pytest.skip("Raport bez tej miary.")
    assert ile <= MAKS_FALSZYWYCH_ODPOWIEDZI, (
        f"\n{ile} pytań bez pokrycia dostało odpowiedź "
        f"(limit {MAKS_FALSZYWYCH_ODPOWIEDZI}) — {sciezka.name}\n")


def test_brak_bledow_wykonania(raport):
    """Wyjątek w trakcie przebiegu to usterka, nie zła odpowiedź."""
    sciezka, dane, _ = raport
    bledy = [p for p in dane.get("przypadki", []) if p.get("blad")]
    assert not bledy, (
        f"\n{len(bledy)} przypadków zakończyło się wyjątkiem ({sciezka.name}):\n"
        + "\n".join(f"  {p['id']}: {p['blad']}" for p in bledy[:5]))
