"""Benchmark v2 — przypisanie etapu i wielokrotna prawda wzorcowa.

════════════════════════════════════════════════════════════════════════
 PO CO V2 — TRZY WADY V1, KAŻDA POTWIERDZONA POMIAREM
════════════════════════════════════════════════════════════════════════

V1 mierzy dobrze WYNIK. Nie mierzy PRZYCZYNY — i to go dyskwalifikuje
w momencie, w którym wynik się pogarsza.

**W-1 · Brak przypisania etapu.** V1 zapisuje `odmowil=True` i nic
więcej. Odmowa może pochodzić z sześciu różnych miejsc: zdanie nie
weszło do retrievalu · model go nie wskazał · weryfikator odrzucił
cytat · zakotwiczenie w pytaniu · wsparcie mechaniczne · kontrola
niezależna.

Skutek zmierzony 14.08.2026: J-4 skoczyła z 12,5% na 56,2% i przez
TRZY pełne przebiegi nie dało się ustalić, która warstwa ją podniosła.
Postawiono dwie hipotezy, obie sprawdzone w izolacji, obie błędne —
bo narzędzie nie odpowiadało na pytanie „gdzie to umarło".

**W-2 · Jedna prawda wzorcowa zamiast wszystkich.** `miary.ocen`
porównuje cytat do JEDNEGO zdania wzorcowego. Tymczasem ten sam fakt
bywa w aktach w kilku miejscach: data „23 lipca 1974" stoi w dok. 232,
a w dok. 319 ten sam wyrok przywołano jako „23.07.1974 r., V KR 212/74".
Cytat z dok. 319 jest **poprawny**, a v1 liczy go jako błąd.

Miara, która karze za znalezienie prawdziwego wystąpienia, tworzy
fałszywy sygnał i kieruje strojenie w złą stronę.

**W-3 · Obciążenie przeżywalnością w pomiarze kontroli.**
`eval/zmierz_kontrole.py` bada wyłącznie przypadki, w których potok
zwrócił cytaty — czyli te, które kontrolę PRZESZŁY. Odrzucone nie
trafiają do próbki w ogóle. Narzędzie pokazywało „kontrola nie odrzuca
niczego" dokładnie wtedy, gdy podejrzewano ją o odrzucanie połowy
odpowiedzi.

════════════════════════════════════════════════════════════════════════
 CO V2 BIERZE Z ISTNIEJĄCYCH BENCHMARKÓW
════════════════════════════════════════════════════════════════════════

**LegalBench-RAG** — ocenia etap wyszukiwania W IZOLACJI od generacji.
Stąd `recall_zdania`: czy zdanie wzorcowe w ogóle dotarło do modelu.
Bez tego „model nie znalazł" i „modelowi nie pokazano" są nieodróżnialne.

**Badania nad atrybucją (ALCE i pokrewne)** — cytat oceniany wobec
WSZYSTKICH fragmentów popierających, nie wobec jednego wybranego.
Stąd wielokrotna prawda wzorcowa (W-2).

**Harvey LAB** — zasada „all-pass": zadanie zalicza się tylko wtedy,
gdy przechodzą wszystkie wymagane kryteria. Stąd `pelny_sukces`
odrębny od miar cząstkowych.

Czego NIE bierzemy: **rubryk ocenianych sędzią LLM** (LRAGE). Prawda
wzorcowa pozostaje zakresem znaków, zgodnie z ADR-0006.

════════════════════════════════════════════════════════════════════════

⚠️ V2 NIE WYMAGA NOWYCH DANYCH ANI ZMIAN W POTOKU.
   Działa na tych samych sprawach 3 i 4, tym samym generatorze par
   i na tym, co `agent.odpowiedz` JUŻ zwraca. Etap rozpoznaje po
   powodach odrzucenia, które potok i tak zapisuje.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

KORZEN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KORZEN / "panel"))

from .generator import Korpus, Przypadek  # noqa: E402


# ── etapy potoku ─────────────────────────────────────────────────────

class Etap(str, Enum):
    """Gdzie przypadek został rozstrzygnięty.

    Kolejność odpowiada przepływowi — pierwszy etap, który zatrzymał
    przypadek, jest tym przypisanym.
    """
    RETRIEVAL = "retrieval"            # zdania wzorcowego nie pokazano modelowi
    GENERACJA = "generacja"            # model nie wskazał żadnego zdania
    WERYFIKACJA = "weryfikacja"        # cytat nie przeszedł sprawdzenia znaków
    ZAKOTWICZENIE = "zakotwiczenie"    # odpowiedź nie na temat pytania
    WSPARCIE = "wsparcie"              # cytat nie popiera twierdzenia (mechanicznie)
    KONTROLA = "kontrola"              # kontroler niezależny powiedział NIE
    GLOSOWANIE = "glosowanie"          # nie przeszło progu samospójności
    ODPOWIEDZ = "odpowiedz"            # doszło do końca — jest odpowiedź


# Rozpoznanie etapu po powodzie odrzucenia, który potok już zapisuje.
# Dzięki temu v2 nie wymaga instrumentacji `agent.odpowiedz`.
POWOD_ETAP: dict[str, Etap] = {
    "odrzucony_brak_dokumentu": Etap.WERYFIKACJA,
    "odrzucony_zakres_poza_tekstem": Etap.WERYFIKACJA,
    "odrzucony_tresc_niezgodna": Etap.WERYFIKACJA,
    "odrzucony_brak_cytatu": Etap.WERYFIKACJA,
    "odrzucony_numer_zdania_poza_zakresem": Etap.WERYFIKACJA,
    "odrzucony_niezakotwiczony_w_pytaniu": Etap.ZAKOTWICZENIE,
    "odrzucony_brak_wsparcia_w_cytacie": Etap.WSPARCIE,
    "odrzucony_kontrola_niezalezna": Etap.KONTROLA,
}


# ── wielokrotna prawda wzorcowa ──────────────────────────────────────

@dataclass(frozen=True)
class Wystapienie:
    """Jedno miejsce w aktach, w którym kotwica faktycznie stoi."""
    dokument_id: str
    poczatek: int
    koniec: int


def wszystkie_wystapienia(korpus: Korpus, przypadek: Przypadek,
                          margines: int = 400) -> list[Wystapienie]:
    """WSZYSTKIE miejsca, w których kotwica występuje — nie tylko wzorcowe.

    ⚠️ To jest naprawa W-2. Cytat wskazujący inne prawdziwe wystąpienie
    tej samej kotwicy jest POPRAWNY. V1 liczył go jako błąd, bo znał
    tylko jedno zdanie wzorcowe.

    Porównanie po wartości wyróżnika, nie po ciągu znaków: „23.07.1974"
    i „23 lipca 1974 r." wskazują to samo orzeczenie i oba się liczą.
    """
    from wyrozniki import wyrozniki as _wyr

    szukane = _wyr(przypadek.kotwica).zlozone
    wynik: list[Wystapienie] = []

    for doc_id, tresc in korpus.dokumenty.items():
        # Ścieżka szybka — dosłowne wystąpienie.
        for m in re.finditer(re.escape(przypadek.kotwica), tresc):
            wynik.append(Wystapienie(
                doc_id, max(0, m.start() - margines // 4),
                min(len(tresc), m.end() + margines)))

        # Ścieżka po wartości — inny zapis tej samej daty czy kwoty.
        if not szukane:
            continue
        for m in re.finditer(r"[^\n.!?]{20,400}", tresc):
            if szukane & _wyr(m.group(0)).zlozone:
                wynik.append(Wystapienie(doc_id, m.start(), m.end()))

    return wynik


# ── ocena ────────────────────────────────────────────────────────────

@dataclass
class OcenaV2:
    przypadek_id: str
    kategoria: str
    jezyk: str
    etap: Etap
    poprawny: bool
    trafiony: bool = False
    zdanie_dotarlo: bool = False          # recall retrievalu, w izolacji
    liczba_wystapien: int = 0             # ile prawdziwych miejsc istnieje
    czas_s: float = 0.0
    szczegol: str = ""

    # ── tryb cienia: co zrobiłaby kontrola, gdyby odrzucała ──────────
    # Wypełniane tylko przy `agent.KONTROLA_CIEN`. `None` znaczy
    # „nie mierzono", a nie „kontrola nic by nie zmieniła" — te dwie
    # rzeczy muszą być rozróżnialne w raporcie.
    kontrola_cien: bool = False           # czy pomiar w ogóle się odbył
    odpowiedzialby_z_kontrola: bool = False
    trafiony_z_kontrola: bool = False
    twierdzen_odrzuconych: int = 0

    # ── rozdzielenie warstw ──────────────────────────────────────────
    # `ws` = sama warstwa mechaniczna (wsparcie.py, darmowa)
    # `km` = sam kontroler modelem (kontrola.py, ~8 s na twierdzenie)
    odpowiedzialby_ws: bool = False
    trafiony_ws: bool = False
    odrzuconych_ws: int = 0
    odpowiedzialby_km: bool = False
    trafiony_km: bool = False
    odrzuconych_km: int = 0
    cien_szczegoly: list[dict] = field(default_factory=list)


def _nachodzi(a1: int, a2: int, b1: int, b2: int) -> int:
    return max(0, min(a2, b2) - max(a1, b1))


def rozpoznaj_etap(odpowiedz: dict, zdanie_dotarlo: bool) -> tuple[Etap, str]:
    """Pierwszy etap, który zatrzymał przypadek.

    Kolejność sprawdzania odpowiada przepływowi potoku, więc przy kilku
    odrzuceniach przypisujemy NAJWCZEŚNIEJSZY — to on jest przyczyną.
    """
    if odpowiedz.get("blad"):
        return Etap.GENERACJA, str(odpowiedz["blad"])[:120]

    if odpowiedz.get("cytaty"):
        return Etap.ODPOWIEDZ, ""

    if not zdanie_dotarlo:
        return Etap.RETRIEVAL, "zdania wzorcowego nie pokazano modelowi"

    odrzucone = odpowiedz.get("odrzucone") or []
    if not odrzucone:
        return Etap.GENERACJA, "model nie wskazał żadnego zdania"

    kolejnosc = [Etap.WERYFIKACJA, Etap.ZAKOTWICZENIE, Etap.WSPARCIE,
                 Etap.KONTROLA, Etap.GLOSOWANIE]
    znalezione: dict[Etap, str] = {}
    for o in odrzucone:
        powod = str(o.get("powod", ""))
        etap = POWOD_ETAP.get(powod)
        if etap is None and o.get("powod_glosowania"):
            etap = Etap.GLOSOWANIE
        if etap is not None:
            znalezione.setdefault(etap, str(o.get("szczegol", ""))[:120])

    for etap in kolejnosc:
        if etap in znalezione:
            return etap, znalezione[etap]

    return Etap.GENERACJA, "odrzucone bez rozpoznanego powodu"


def ocen(przypadek: Przypadek, odpowiedz: dict,
         wystapienia: list[Wystapienie], zdanie_dotarlo: bool,
         min_pokrycie: float = 0.30) -> OcenaV2:
    """Ocena wobec WSZYSTKICH prawdziwych wystąpień kotwicy."""
    etap, szczegol = rozpoznaj_etap(odpowiedz, zdanie_dotarlo)
    cytaty = odpowiedz.get("cytaty") or []

    def _trafia(lista: list) -> bool:
        """Czy którykolwiek z podanych cytatów pokrywa prawdziwe wystąpienie.

        Wydzielone, bo tryb cienia liczy to samo na czterech różnych
        podzbiorach cytatów. Trzy kopie tej pętli już raz rozjechały się
        w tym pliku o `min_pokrycie`.
        """
        if not (przypadek.odpowiadalny and lista and wystapienia):
            return False
        for c in lista:
            for w in wystapienia:
                if str(c.get("dokument_id")) != w.dokument_id:
                    continue
                dlugosc = max(1, w.koniec - w.poczatek)
                if _nachodzi(w.poczatek, w.koniec,
                             int(c.get("poczatek", 0)),
                             int(c.get("koniec", 0))) / dlugosc >= min_pokrycie:
                    return True
        return False

    trafiony = _trafia(cytaty)

    if przypadek.odpowiadalny:
        poprawny = trafiony
    else:
        poprawny = not cytaty

    # ── tryb cienia ──────────────────────────────────────────────────
    #
    # Kontrola tylko ODRZUCA — nigdy nie tworzy odpowiedzi. Wystarczy
    # więc odjąć oznaczone cytaty i policzyć wynik jeszcze raz na tym,
    # co by zostało. Odpowiedź zamienia się w odmowę dopiero wtedy, gdy
    # odpadną WSZYSTKIE cytaty, a nie gdy odpadnie którykolwiek.
    #
    # ⚠️ ROZDZIELENIE WARSTW — POMIAR Z 15.08.2026 GO WYMUSIŁ.
    # Cień liczony łącznie pokazał, że kontrola zatrzymuje 9 fałszywych
    # odpowiedzi kosztem 13 trafień, ale NIE mówił, która z dwóch warstw
    # za to odpowiada. To są zupełnie różne rzeczy: `wsparcie.py` jest
    # darmowe i deterministyczne (da się stroić progiem), a kontroler
    # modelem kosztuje ~8 s na twierdzenie i stroi się wyłącznie
    # promptem. Bez rozdzielenia decyzja o wyłączeniu którejś z nich
    # byłaby zgadywaniem.
    mierzono = any("_kontrola_cien" in c for c in cytaty)
    przezyly = [c for c in cytaty if not c.get("_kontrola_cien")]
    przezyly_ws = [c for c in cytaty
                   if c.get("_kontrola_cien") != "wsparcie_brak"]
    przezyly_km = [c for c in cytaty
                   if c.get("_kontrola_cien") != "kontrola_falsz"]

    return OcenaV2(
        przypadek_id=przypadek.id, kategoria=przypadek.kategoria,
        jezyk=przypadek.jezyk, etap=etap, poprawny=poprawny,
        trafiony=trafiony, zdanie_dotarlo=zdanie_dotarlo,
        liczba_wystapien=len(wystapienia),
        czas_s=float(odpowiedz.get("_czas_s", 0.0)), szczegol=szczegol,
        kontrola_cien=mierzono,
        odpowiedzialby_z_kontrola=bool(przezyly),
        trafiony_z_kontrola=_trafia(przezyly),
        twierdzen_odrzuconych=len(cytaty) - len(przezyly),
        odpowiedzialby_ws=bool(przezyly_ws),
        trafiony_ws=_trafia(przezyly_ws),
        odrzuconych_ws=len(cytaty) - len(przezyly_ws),
        odpowiedzialby_km=bool(przezyly_km),
        trafiony_km=_trafia(przezyly_km),
        odrzuconych_km=len(cytaty) - len(przezyly_km),
        # Szczegół każdego ODRZUCONEGO cytatu: z jakiego powodu odpadł
        # i czy trafiał w prawdziwe wystąpienie. Dopiero to pozwala
        # odróżnić „warstwa słusznie odrzuciła bzdurę" od „warstwa
        # skasowała dobrą odpowiedź", a przy tym drugim — czy przyczyna
        # jest strojona progiem, czy nie.
        cien_szczegoly=[
            {"przyczyna": str(c.get("przyczyna")
                              or c.get("_kontrola_cien") or "?"),
             "pokrycie": c.get("pokrycie"),
             "brakujace": c.get("brakujace") or [],
             "trafia": _trafia([c])}
            for c in cytaty if c.get("_kontrola_cien")
        ],
    )


# ── agregacja z rozbiciem na etapy ───────────────────────────────────

@dataclass
class PodsumowanieV2:
    przypadkow: int = 0
    poprawnych: int = 0
    etapy: dict[str, int] = field(default_factory=dict)
    etapy_falszywych_odmow: dict[str, int] = field(default_factory=dict)
    recall_retrievalu: float = 0.0
    srednia_wystapien: float = 0.0


def podsumuj(przypadki: list[Przypadek], oceny: dict[str, OcenaV2]) -> dict:
    """Metryki v2 — z rozbiciem odmów na etapy.

    Kluczowe pole to `etapy_falszywych_odmow`. Odpowiada na pytanie,
    którego v1 nie umiał postawić: skoro system odmówił mimo obecnej
    odpowiedzi, to GDZIE ta odpowiedź przepadła.
    """
    from collections import Counter

    wg_id = {p.id: p for p in przypadki}
    lista = list(oceny.values())
    if not lista:
        return {"przypadkow": 0}

    odpowiadalne = [o for o in lista if wg_id[o.przypadek_id].odpowiadalny]
    odmowne = [o for o in lista if not wg_id[o.przypadek_id].odpowiadalny]

    # ⚠️ ROZDZIELENIE DWÓCH RÓŻNYCH BŁĘDÓW — NAPRAWA MYLĄCEJ MIARY.
    #
    # Do 15.08.2026 jedna miara nazywała się `etapy_falszywych_odmow`
    # i liczyła WSZYSTKIE nietrafione przypadki odpowiadalne, niezależnie
    # od tego, czy system odmówił, czy odpowiedział błędnie. Przy etapie
    # `odpowiedz` pokazywała więc „fałszywe odmowy" tam, gdzie system
    # niczego nie odmówił — tylko udzielił złej odpowiedzi.
    #
    # To są dwa różne błędy o różnej wadze. Odmowa przy istniejącej
    # odpowiedzi jest kosztowna. BŁĘDNA ODPOWIEDŹ JEST NIEBEZPIECZNA —
    # prawnik dostaje cytat z akt przy tezie, której ten cytat nie
    # popiera. Mieszanie ich w jednej liczbie zaciera to, co najważniejsze.
    #
    # Ta sama klasa pomyłki pomiarowej czterokrotnie zmyliła diagnozę
    # w tej sesji — tym razem w narzędziu zbudowanym w tym projekcie.
    falszywe_odmowy = [o for o in odpowiadalne
                       if not o.trafiony and o.etap is not Etap.ODPOWIEDZ]
    bledne_odpowiedzi = [o for o in odpowiadalne
                         if not o.trafiony and o.etap is Etap.ODPOWIEDZ]

    # J-3: udział pytań BEZ POKRYCIA, którym system odmówił.
    # Bramka projektu: ≥ 90%. Liczona wprost, żeby nie trzeba jej było
    # wyprowadzać ręcznie z rozkładu etapów.
    odmowione = [o for o in odmowne if o.etap is not Etap.ODPOWIEDZ]

    dotarly = [o for o in odpowiadalne if o.zdanie_dotarlo]

    # ── tryb cienia: ten sam zbiór, oba układy ───────────────────────
    #
    # Liczone wyłącznie wtedy, gdy pomiar cienia faktycznie się odbył.
    # Sekcja nieobecna w raporcie znaczy „nie mierzono" — inaczej zera
    # czytałoby się jako „kontrola nic nie zmienia", co jest zupełnie
    # innym zdaniem.
    cien: dict = {}
    if any(o.kontrola_cien for o in lista):

        def _wariant(odpowiedzialby, trafiony_po) -> dict:
            """Metryki dla jednego układu warstw, na tym samym przebiegu.

            `odpowiedzialby` i `trafiony_po` wyciągają z oceny pola
            odpowiadające danemu wariantowi. Dzięki temu wszystkie trzy
            układy liczone są DOKŁADNIE tym samym kodem — inaczej różnica
            między nimi mogłaby pochodzić z różnicy w liczeniu.
            """
            odm = [o for o in odmowne
                   if not odpowiedzialby(o) or o.etap is not Etap.ODPOWIEDZ]
            return {
                # Zysk: pytania bez pokrycia zamienione w odmowę. To jest
                # ta luka, dla której kontrola powstała.
                "J3_odmowa_poprawna": len(odm) / len(odmowne) if odmowne else 0.0,
                "falszywe_odpowiedzi": len(odmowne) - len(odm),
                # Koszt: poprawne odpowiedzi, które warstwa by zabrała.
                "trafnosc": (sum(1 for o in odpowiadalne if trafiony_po(o))
                             / len(odpowiadalne)) if odpowiadalne else 0.0,
                "utracone_trafienia": sum(
                    1 for o in odpowiadalne if o.trafiony and not trafiony_po(o)),
            }

        cien = {
            "zmierzono_na": sum(1 for o in lista if o.kontrola_cien),
            "twierdzen_odrzuconych": sum(o.twierdzen_odrzuconych for o in lista),
            **_wariant(lambda o: o.odpowiedzialby_z_kontrola,
                       lambda o: o.trafiony_z_kontrola),
            # Rozdzielenie warstw: która z nich wnosi zysk, a która koszt.
            "sama_mechanika": {
                "twierdzen_odrzuconych": sum(o.odrzuconych_ws for o in lista),
                **_wariant(lambda o: o.odpowiedzialby_ws,
                           lambda o: o.trafiony_ws)},
            "sam_kontroler": {
                "twierdzen_odrzuconych": sum(o.odrzuconych_km for o in lista),
                **_wariant(lambda o: o.odpowiedzialby_km,
                           lambda o: o.trafiony_km)},
        }

        # ── dlaczego cytat odpadł, w rozbiciu na słuszne i szkodliwe ──
        #
        # `szkodliwe` to odrzucenia cytatów, które TRAFIAŁY w prawdziwe
        # wystąpienie — czyli dokładnie ta strata, którą widać w kolumnie
        # „utracone trafienia". Rozbicie po przyczynie mówi, czy da się ją
        # odzyskać progiem (przyczyna „pokrycie") czy trzeba poprawić
        # ekstraktor wyróżników (przyczyna „wyroznik").
        szczegoly = [s for o in lista for s in o.cien_szczegoly]
        przyczyny: dict[str, dict] = {}
        for s in szczegoly:
            wpis = przyczyny.setdefault(
                s["przyczyna"], {"razem": 0, "szkodliwe": 0, "pokrycia": []})
            wpis["razem"] += 1
            if s["trafia"]:
                wpis["szkodliwe"] += 1
            if isinstance(s.get("pokrycie"), (int, float)):
                wpis["pokrycia"].append(float(s["pokrycie"]))

        cien["przyczyny_odrzucen"] = {
            nazwa: {
                "razem": w["razem"],
                "szkodliwe": w["szkodliwe"],
                "pokrycie_min": round(min(w["pokrycia"]), 3) if w["pokrycia"] else None,
                "pokrycie_maks": round(max(w["pokrycia"]), 3) if w["pokrycia"] else None,
            }
            for nazwa, w in sorted(przyczyny.items())
        }
        # Najczęstsze wyróżniki wycięte SZKODLIWIE — wprost wskazują,
        # który wzorzec w `wyrozniki.py` jest nadgorliwy.
        zle_wyrozniki = Counter(
            w for s in szczegoly if s["trafia"] for w in (s.get("brakujace") or []))
        if zle_wyrozniki:
            cien["wyrozniki_szkodliwe"] = dict(zle_wyrozniki.most_common(15))

    return {
        **({"gdyby_kontrola": cien} if cien else {}),
        "przypadkow": len(lista),
        "poprawnych": sum(1 for o in lista if o.poprawny),
        "trafnosc": sum(1 for o in odpowiadalne if o.trafiony) / len(odpowiadalne)
                    if odpowiadalne else 0.0,

        # ── bramka J-3: odmowa przy braku pokrycia ───────────────────
        "J3_odmowa_poprawna": len(odmowione) / len(odmowne) if odmowne else 0.0,
        "bez_pokrycia": len(odmowne),
        "bez_pokrycia_odmowionych": len(odmowione),
        # Pytania bez pokrycia, którym system ODPOWIEDZIAŁ. Najgroźniejsza
        # kategoria: prawnik dostaje odpowiedź tam, gdzie akta jej nie dają.
        "falszywe_odpowiedzi": len(odmowne) - len(odmowione),

        # ── naprawa W-1: gdzie przypadki umierają ────────────────────
        "etapy": dict(Counter(o.etap.value for o in lista)),
        "etapy_falszywych_odmow": dict(Counter(o.etap.value
                                               for o in falszywe_odmowy)),
        "falszywych_odmow": len(falszywe_odmowy),
        # Odpowiedział, ale cytat nie trafił w żadne prawdziwe wystąpienie.
        "blednych_odpowiedzi": len(bledne_odpowiedzi),

        # ── naprawa W-3: retrieval mierzony w izolacji ───────────────
        "recall_retrievalu": len(dotarly) / len(odpowiadalne)
                             if odpowiadalne else 0.0,

        # ── naprawa W-2: ile prawdziwych miejsc w ogóle istnieje ─────
        "srednia_wystapien": sum(o.liczba_wystapien for o in odpowiadalne)
                             / len(odpowiadalne) if odpowiadalne else 0.0,
        "bez_wystapien": sum(1 for o in odpowiadalne if o.liczba_wystapien == 0),
    }
