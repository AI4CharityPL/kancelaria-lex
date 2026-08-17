"""PEŁNY ŁAŃCUCH dla akt polskich wczytanych z pliku — aż do cytatu.

════════════════════════════════════════════════════════════════════════
 CZEGO TE TESTY PILNUJĄ, A CZEGO NIE PILNOWAŁ ŻADEN INNY
════════════════════════════════════════════════════════════════════════

`test_wczytywanie.py` sprawdza WYDOBYCIE tekstu z pliku. Osobne testy
sprawdzają cytowanie. Nikt natomiast nie sprawdzał ICH POŁĄCZENIA, a to
tam jest realne ryzyko dla systemu obiecującego cytat znak w znak:

    plik → dekodowanie → naprawa kodowania → porządkowanie →
    → podział na zdania → wybór → CYTAT PO OFFSETACH

Każdy z tych kroków może przesunąć offsety o jeden znak. Przy polskim
tekście ryzyko jest większe niż przy angielskim, bo dochodzi konwersja
kodowania (cp1250/ISO-8859-2), sklejanie wyrazów dzielonych na końcu
wiersza i litery spoza ASCII. Cytat przesunięty o jeden znak wygląda
poprawnie na ekranie i jest fałszywy.

⚠️ OCR JEST POZA ZAKRESEM — I TO JEST STAN FAKTYCZNY, NIE PRZEOCZENIE.
   `wczytywanie.py` czyta wyłącznie WARSTWĘ TEKSTOWĄ pliku PDF. Skan bez
   tej warstwy jest odrzucany z komunikatem, a nie wczytywany jako pusty.
   Test `test_skan_jest_odrzucany_a_nie_wczytany_pusty` pilnuje właśnie
   tego, bo cicha akceptacja skanu byłaby najgorszym z możliwych
   zachowań: sprawa wyglądałaby na wczytaną i nie dałaby żadnych cytatów.
"""

from __future__ import annotations

import sys
import zipfile
import zlib
from io import BytesIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panel"))

import wczytywanie  # noqa: E402
import zdania as mod_zdania  # noqa: E402
import wyszukiwarka  # noqa: E402

# Tekst z KOMPLETEM polskich znaków diakrytycznych, w tym wielkimi.
POLSKI = (
    "Sąd Rejonowy w Świdnicy, Wydział II Karny, po rozpoznaniu sprawy "
    "oskarżonego Zbigniewa Łąckiego, ustalił co następuje. "
    "Świadek zeznał, że w dniu 13 stycznia 2025 roku około godziny 15.20 "
    "widział pojazd marki Żuk przy ulicy Ćwiartki. "
    "Biegły stwierdził, że ślady hamowania świadczą o prędkości "
    "przekraczającej dopuszczalną. "
    "Oskarżony nie przyznał się do winy i odmówił składania wyjaśnień."
)
OGONKI = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"


def _docx(tresc: str) -> bytes:
    """Minimalny DOCX — przestrzeń nazw MUSI być prawdziwa.

    Pierwsza wersja tego pomocnika deklarowała `xmlns:w="x"` i moduł
    zwracał pusty tekst. To zachowanie modułu jest POPRAWNE (nie czyta
    czegoś, co tylko udaje DOCX), ale w teście dawało fałszywy alarm.
    """
    bufor = BytesIO()
    with zipfile.ZipFile(bufor, "w") as archiwum:
        archiwum.writestr("[Content_Types].xml", "<Types/>")
        archiwum.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/'
            f'wordprocessingml/2006/main"><w:body>'
            f"<w:p><w:r><w:t>{tresc}</w:t></w:r></w:p>"
            '</w:body></w:document>')
    return bufor.getvalue()


def _pdf(tekst_bajty: bytes) -> bytes:
    tresc = b"BT /F1 12 Tf (" + tekst_bajty + b") Tj ET"
    spakowana = zlib.compress(tresc)
    return (b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Page /Font << /F1 2 0 R >> >>\nendobj\n"
            b"2 0 obj\n<< /Type /Font /BaseFont /Helvetica >>\nendobj\n"
            b"3 0 obj\n<< /Length " + str(len(spakowana)).encode() +
            b" /Filter /FlateDecode >>\nstream\n" + spakowana +
            b"\nendstream\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF")


# ── 1. Ogonki przeżywają wczytanie ──────────────────────────────────

@pytest.mark.parametrize("nazwa,dane", [
    ("akta.txt", POLSKI.encode("utf-8")),
    ("akta.txt", POLSKI.encode("cp1250")),
    ("akta.docx", _docx(POLSKI)),
])
def test_ogonki_przezywaja_wczytanie(nazwa, dane):
    """Każdy polski znak ma wyjść taki, jaki wszedł."""
    wynik = wczytywanie.wczytaj(nazwa, dane)
    for znak in OGONKI:
        if znak in POLSKI:
            assert znak in wynik.tekst, (
                f"{nazwa}: zgubiono {znak!r}; "
                f"otrzymano: {wynik.tekst[:120]!r}")


def test_cp1250_odtwarza_tekst_identycznie_jak_utf8():
    """Ten sam dokument w dwóch kodowaniach musi dać ten SAM tekst.

    Inaczej offsety cytatu zależałyby od tego, w czym kancelaria
    zapisała plik — a to jest niewidoczne dla użytkownika.
    """
    a = wczytywanie.wczytaj("akta.txt", POLSKI.encode("utf-8")).tekst
    b = wczytywanie.wczytaj("akta.txt", POLSKI.encode("cp1250")).tekst
    assert a == b


# ── 2. Offsety po wczytaniu wskazują TO SAMO ────────────────────────

@pytest.mark.parametrize("nazwa,dane", [
    ("akta.txt", POLSKI.encode("utf-8")),
    ("akta.txt", POLSKI.encode("cp1250")),
    ("akta.docx", _docx(POLSKI)),
])
def test_offsety_zdan_wskazuja_dokladnie_zdanie(nazwa, dane):
    """Sedno całego łańcucha.

    Zdanie wycięte z tekstu po offsetach musi być IDENTYCZNE z treścią,
    którą niesie obiekt zdania. Przesunięcie o jeden znak daje cytat
    wyglądający poprawnie i fałszywy.
    """
    tekst = wczytywanie.wczytaj(nazwa, dane).tekst
    zdania = mod_zdania.podziel_na_zdania(tekst, "pl")
    assert zdania, "podział nie dał żadnego zdania"

    for z in zdania:
        assert tekst[z.poczatek:z.koniec] == z.tresc, (
            f"{nazwa}: rozjazd offsetów\n"
            f"  z offsetów: {tekst[z.poczatek:z.koniec]!r}\n"
            f"  z obiektu : {z.tresc!r}")


def test_zdanie_z_ogonkami_wycina_sie_poprawnie():
    """Zdanie zawierające ogonki i skrót — najtrudniejszy przypadek."""
    tekst = wczytywanie.wczytaj("akta.txt", POLSKI.encode("cp1250")).tekst
    zdania = mod_zdania.podziel_na_zdania(tekst, "pl")
    z_ogonkami = [z for z in zdania if any(o in z.tresc for o in "ąćęłńóśźż")]
    assert z_ogonkami, "żadne zdanie nie zawiera ogonków — podejrzane"
    for z in z_ogonkami:
        assert tekst[z.poczatek:z.koniec] == z.tresc


# ── 3. Wyszukiwarka znajduje polskie słowa po wczytaniu ─────────────

def test_tokenizacja_dziala_na_tekscie_po_wczytaniu():
    """Jeśli kodowanie się rozjedzie, BM25 przestanie trafiać w polskie
    wyrazy — a objawi się to jako „model nie znajduje odpowiedzi", czyli
    w miejscu, w którym nikt nie szuka przyczyny.

    Sprawdzamy więc, że wyraz z ogonkami wydobyty z pliku daje TE SAME
    tokeny co ten sam wyraz wpisany wprost.
    """
    tekst = wczytywanie.wczytaj("akta.txt", POLSKI.encode("cp1250")).tekst
    assert "oskarżonego" in tekst, tekst[:150]

    z_pliku = set(wyszukiwarka.tokenizuj(tekst, "pl"))
    wprost = set(wyszukiwarka.tokenizuj(POLSKI, "pl"))
    assert z_pliku == wprost, (
        f"tokeny się rozjechały; brakuje: {wprost - z_pliku}, "
        f"nadmiarowe: {z_pliku - wprost}")


# ── 4. OCR: skan ma być ODRZUCONY, nie wczytany pusty ───────────────

def test_skan_jest_odrzucany_a_nie_wczytany_pusty():
    """PDF bez warstwy tekstowej to skan. Cicha akceptacja byłaby
    najgorszym zachowaniem: sprawa wyglądałaby na wczytaną, a nie
    dałaby ani jednego cytatu — i nikt by nie wiedział dlaczego."""
    pusty_pdf = _pdf(b"")
    wynik = wczytywanie.wczytaj("skan.pdf", pusty_pdf)
    assert not wynik.nadaje_sie, "skan przeszedł jako nadający się"
    assert wynik.wymaga_ocr, "nie oznaczono jako wymagający OCR"
    assert any("OCR" in o or "skan" in o.lower() for o in wynik.ostrzezenia), (
        f"komunikat nie mówi o OCR: {wynik.ostrzezenia}")


def test_ocen_jakosci_rozpoznaje_skan_po_znikomej_warstwie():
    """Skan z resztką tekstu (nagłówek stopki) też ma być oznaczony."""
    ostrzezenia, wymaga = wczytywanie.ocen_jakosc("str. 1", 250_000, "pdf")
    assert wymaga is True, (ostrzezenia, wymaga)
