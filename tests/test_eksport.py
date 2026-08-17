"""Eksport wyniku analizy do pliku.

⚠️ NAJWAŻNIEJSZY TEST W TYM PLIKU DOTYCZY TEGO, CZEGO EKSPORT NIE GUBI.

Dokument bez sekcji odrzuconych i bez stanu kontroli wygląda na
pewniejszy, niż jest. Jeżeli trafi do notatki dla klienta albo do pisma,
zabiera ze sobą wrażenie pewności, którego system nigdy nie dawał.
"""

from __future__ import annotations

import sys
from pathlib import Path

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import eksport  # noqa: E402

WYNIK = {
    "pytanie": "Kiedy sąd oddalił wniosek obrońcy?",
    "przeanalizowane_dokumenty": ["postanowienie.pdf", "protokol.docx"],
    "ustalenia": [{
        "tekst": "Sąd oddalił wniosek obrońcy 14 września 2006 r.",
        "dokument": "postanowienie.pdf",
        "cytaty": [{
            "dokument_id": "1", "poczatek": 120, "koniec": 210,
            "fragment": "Sąd oddalił wniosek obrońcy o dopuszczenie dowodu "
                        "z opinii biegłego.",
            "stopien": "mocne", "pokrycie": 0.82, "kontrola": "prawda",
        }],
    }, {
        "tekst": "Zabezpieczenie ustalono na 1 008,00 zł.",
        "dokument": "protokol.docx",
        "cytaty": [{
            "dokument_id": "2", "poczatek": 40, "koniec": 90,
            "fragment": "Zabezpieczenie w kwocie 1 008,00 zł.",
            "stopien": "slabe", "pokrycie": 0.31,
            "kontrola": "niezweryfikowane",
            "ostrzezenie": "nie zweryfikowano niezależnie: model niedostępny",
        }],
    }],
    "wnioski": [{"tekst": "Wniosek dowodowy nie został uwzględniony.",
                 "oparte_na": [1]}],
    "rozbieznosci": [{"opis": "Protokół podaje inną kwotę niż postanowienie.",
                      "oparte_na": [1, 2]}],
    "luki": ["Brak w aktach potwierdzenia doręczenia."],
    "podstawa_prawna": [{"tekst": "art. 170 § 1 k.p.k.",
                         "cytat": {"nazwa": "k.p.k. art. 170",
                                   "fragment": "Oddala się wniosek dowodowy…"}}],
    "odrzucone": [{"tekst": "Sąd uwzględnił wniosek obrońcy.",
                   "powod": "odrzucony_kontrola_niezalezna",
                   "szczegol": "Zacytowane zdanie tego nie stwierdza."}],
}


# ── zawartość, której nie wolno zgubić ───────────────────────────────

def test_markdown_zawiera_cytat_w_brzmieniu_zrodla():
    tekst = eksport.do_markdown(WYNIK, "II K 147/26", "Anna Kowalska")
    assert "Sąd oddalił wniosek obrońcy o dopuszczenie dowodu" in tekst
    assert "znaki 120–210" in tekst


def test_markdown_niesie_sekcje_odrzuconych():
    """⚠️ Bez tej sekcji dokument zmienia wymowę.

    Czytelnik nie wie, że system coś rozważył i odsiał — ani dlaczego.
    """
    tekst = eksport.do_markdown(WYNIK)
    assert "Odrzucone w kontroli" in tekst
    assert "Sąd uwzględnił wniosek obrońcy." in tekst
    assert "odrzucony_kontrola_niezalezna" in tekst


def test_markdown_niesie_stan_kontroli():
    tekst = eksport.do_markdown(WYNIK)
    assert "sprawdzone przez niezależną kontrolę" in tekst
    assert "NIE zweryfikowane niezależnie" in tekst


def test_markdown_niesie_ostrzezenie_przy_cytacie():
    tekst = eksport.do_markdown(WYNIK)
    assert "model niedostępny" in tekst


def test_markdown_ma_zastrzezenie_o_roli_materialu():
    tekst = eksport.do_markdown(WYNIK)
    assert "Materiał roboczy prawnika, nie opinia prawna" in tekst
    assert "sprawdzić w aktach" in tekst


def test_rozbieznosci_z_zastrzezeniem_o_wiarygodnosci():
    """Granica z AI Act: system nie ocenia wiarygodności osób."""
    tekst = eksport.do_markdown(WYNIK)
    assert "nie ocenia wiarygodności osób" in tekst


# ── HTML ─────────────────────────────────────────────────────────────

def test_html_jest_samodzielnym_dokumentem():
    tekst = eksport.do_html(WYNIK, "II K 147/26")
    assert tekst.startswith("<!doctype html>")
    assert "</html>" in tekst
    assert "<style>" in tekst          # styl w pliku, bez zasobów z sieci


def test_html_nie_wpuszcza_znacznikow_z_akt():
    """Treść akt jest DANYMI. Fragment z `<script>` nie może stać się kodem."""
    zlosliwy = {**WYNIK, "ustalenia": [{
        "tekst": "<script>alert(1)</script>",
        "dokument": "x", "cytaty": [{
            "dokument_id": "1", "poczatek": 0, "koniec": 5,
            "fragment": "<img src=x onerror=alert(1)>"}]}]}
    tekst = eksport.do_html(zlosliwy)
    assert "<script>alert(1)</script>" not in tekst
    assert "&lt;script&gt;" in tekst
    assert "onerror=alert(1)>" not in tekst


def test_html_niesie_odrzucone_i_stan_kontroli():
    tekst = eksport.do_html(WYNIK)
    assert "Odrzucone w kontroli" in tekst
    assert "sprawdzone przez niezależną kontrolę" in tekst


# ── przypadki brzegowe ───────────────────────────────────────────────

def test_odmowa_eksportuje_sie_jako_odmowa():
    """Pusty wynik nie może wyjść jako pusty dokument bez wyjaśnienia."""
    tekst = eksport.do_markdown({"pytanie": "O co chodzi?", "ustalenia": [],
                                 "wnioski": []})
    assert "nie znaleziono podstawy do odpowiedzi" in tekst
    assert "Odmowa jest poprawnym wynikiem" in tekst


def test_nazwa_pliku_bezpieczna_dla_systemu_plikow():
    nazwa = eksport.nazwa_pliku("II K 147/26", "md")
    assert "/" not in nazwa and "\\" not in nazwa
    assert nazwa.endswith(".md")
    assert nazwa.startswith("analiza-")


def test_eksport_nie_dodaje_tresci_ktorej_nie_ma():
    """Eksport przepisuje, nie streszcza i nie wnioskuje."""
    minimalny = {"pytanie": "P", "ustalenia": [
        {"tekst": "Jedyne ustalenie.", "dokument": "d", "cytaty": []}]}
    tekst = eksport.do_markdown(minimalny)
    assert "Jedyne ustalenie." in tekst
    assert "Wnioski" not in tekst
    assert "Rozbieżności" not in tekst
