"""Usługa embeddingów — czy decyzja ADR-0004 faktycznie działa.

Domyślny embedder OpenContracts (`all-MiniLM-L6-v2`, 384 wym., korpus
angielski) został zastąpiony przez `multilingual-e5-base` z jednego
powodu: retrieval na POLSKICH pismach procesowych. Testy poniżej
sprawdzają, czy ten powód jest zaspokojony, a nie tylko czy usługa
odpowiada 200.

⚠️ WYMAGA DZIAŁAJĄCEJ USŁUGI. Bez niej testy się POMIJAJĄ, a nie
   zaliczają po cichu — pominięty test nie jest testem zaliczonym.

   docker compose -f infra/compose/compose.yml up -d embedder
"""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.request

import pytest

pytestmark = pytest.mark.izolacja

ADRES = "http://127.0.0.1:8000"
WYMIARY = 768


def _zapytaj(sciezka: str, cialo: dict | None = None):
    dane = json.dumps(cialo).encode() if cialo is not None else None
    zadanie = urllib.request.Request(
        ADRES + sciezka, data=dane,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(zadanie, timeout=30) as odp:
            return odp.status, json.loads(odp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


@pytest.fixture(scope="module")
def usluga():
    """Pominięcie, gdy usługa nie działa — nigdy ciche zaliczenie."""
    try:
        kod, stan = _zapytaj("/zdrowie")
    except OSError as e:
        pytest.skip(
            f"Embedder nie odpowiada pod {ADRES} ({e}). Uruchom:\n"
            "  docker compose -f infra/compose/compose.yml up -d embedder\n"
            "  (usługa wymaga wag w models/e5-base — patrz "
            "src/aplikacje/embedder/README.md)")
    assert kod == 200 and stan["stan"] == "gotowy", stan
    return stan


def _wektor(tekst: str, typ: str = "passage") -> list[float]:
    kod, d = _zapytaj("/v1/embeddings", {"input": [tekst], "typ": typ})
    assert kod == 200, d
    return d["data"][0]["embedding"]


def _podobienstwo(a: list[float], b: list[float]) -> float:
    """Kosinus. Wektory są znormalizowane, więc to iloczyn skalarny."""
    return sum(x * y for x, y in zip(a, b))


# ── kontrakt usługi ─────────────────────────────────────────────────

def test_zdrowie_podaje_zrodlo_wag(usluga):
    """Audytor musi widzieć, SKĄD wzięły się wagi."""
    assert usluga["wymiary"] == WYMIARY
    assert "e5" in usluga["model"]
    assert usluga["zrodlo_wag"], "brak informacji o źródle wag"


def test_wektor_ma_768_wymiarow(usluga):
    """768 zamiast 384 to sedno ADR-0004: mieści się w schemacie pgvector
    bez migracji, a obsługuje polski."""
    assert len(_wektor("Sąd oddalił wniosek.")) == WYMIARY


def test_wektor_jest_znormalizowany(usluga):
    """Norma 1 pozwala liczyć podobieństwo iloczynem skalarnym."""
    norma = math.sqrt(sum(x * x for x in _wektor("Protokół przesłuchania.")))
    assert abs(norma - 1.0) < 1e-4, norma


def test_wiele_tekstow_naraz(usluga):
    kod, d = _zapytaj("/v1/embeddings",
                      {"input": ["pierwszy", "drugi", "trzeci"],
                       "typ": "passage"})
    assert kod == 200
    assert [w["index"] for w in d["data"]] == [0, 1, 2]


# ── prefiksy E5 — usterka, która nie daje błędu ────────────────────

@pytest.mark.parametrize("typ", ["", "dokument", "Query", "zapytanie"])
def test_zly_typ_odrzucony(usluga, typ):
    """Rodzina E5 wymaga prefiksu `query:` albo `passage:`.

    Pominięcie go NIE daje błędu — daje cicho gorszy retrieval. Dlatego
    pole jest walidowane, zamiast mieć domyślną wartość, o której nikt
    nie pamięta.
    """
    kod, d = _zapytaj("/v1/embeddings", {"input": ["tekst"], "typ": typ})
    assert kod == 400, d
    assert "query" in d["blad"] and "passage" in d["blad"]


def test_prefiks_zmienia_wektor(usluga):
    """Dowód, że prefiks faktycznie trafia do modelu.

    Gdyby był ignorowany, oba wektory byłyby identyczne — i cała
    walidacja `typ` byłaby teatrem.
    """
    tekst = "Kiedy doszło do zdarzenia?"
    assert _podobienstwo(_wektor(tekst, "query"),
                         _wektor(tekst, "passage")) < 0.999


# ── to, dla czego zmieniono model ──────────────────────────────────

def test_polski_retrieval_dziala(usluga):
    """SEDNO ADR-0004.

    Pytanie po polsku musi być bliżej fragmentu, który na nie odpowiada,
    niż fragmentu o czymś innym. Model anglojęzyczny (domyślny
    `all-MiniLM-L6-v2`) właśnie tutaj zawodzi na polskich pismach.
    """
    pytanie = _wektor("Kiedy świadek widział pojazd?", "query")
    trafny = _wektor(
        "Świadek zeznał, że widział pojazd 13 stycznia 2025 roku "
        "około godziny 15.20.", "passage")
    nietrafny = _wektor(
        "Biegły ustalił wysokość szkody na kwotę 12 400 złotych.",
        "passage")

    blisko, daleko = _podobienstwo(pytanie, trafny), _podobienstwo(pytanie, nietrafny)
    assert blisko > daleko, (
        f"retrieval po polsku nie działa: trafny={blisko:.4f} "
        f"nietrafny={daleko:.4f}")


def test_polska_fleksja_nie_gubi_znaczenia(usluga):
    """Polska odmiana to główny powód odrzucenia modelu angielskiego."""
    a = _wektor("oskarżony nie przyznał się do winy", "passage")
    b = _wektor("oskarżonemu nie przypisano przyznania się do winy", "passage")
    c = _wektor("posiedzenie odroczono do przyszłego miesiąca", "passage")
    assert _podobienstwo(a, b) > _podobienstwo(a, c)


def test_ogonki_maja_znaczenie(usluga):
    """Tekst z polskimi znakami i bez nich ma być bliski, ale nie
    identyczny — inaczej znaczyłoby to, że diakrytyki są zjadane
    przez tokenizator, co psułoby dopasowanie na aktach z OCR-u."""
    z_ogonkami = _wektor("zażalenie na postanowienie sądu", "passage")
    bez = _wektor("zazalenie na postanowienie sadu", "passage")
    podobne = _podobienstwo(z_ogonkami, bez)
    assert 0.80 < podobne < 0.9999, podobne


# ── granice ─────────────────────────────────────────────────────────

def test_puste_wejscie_odrzucone(usluga):
    kod, _ = _zapytaj("/v1/embeddings", {"input": [], "typ": "passage"})
    assert kod == 400


def test_za_duza_paczka_odrzucona(usluga):
    """Limit chroni pamięć kontenera — bez niego jedno żądanie z całym
    tomem akt wywróciłoby usługę dla wszystkich."""
    kod, _ = _zapytaj("/v1/embeddings",
                      {"input": ["x"] * 200, "typ": "passage"})
    assert kod == 413
