"""Test negatywny — czy bramki izolacji POTRAFIĄ PAŚĆ.

Uzasadnienie (docs/11-testy-i-bramki.md):
test bezpieczeństwa, który przechodzi zawsze, jest gorszy niż brak
testu — daje fałszywą pewność. To najczęstszy sposób, w jaki tego
rodzaju zabezpieczenia cicho przestają działać.

Testy poniżej podsuwają bramkom spreparowane dane i sprawdzają,
że bramki je odrzucają.
"""

from __future__ import annotations

import re

from conftest import PAKIETY_ZAKAZANE


WZORZEC_OBRAZU = re.compile(r"\s*image:\s*(\S+)")


def _wykryj_zakazane(tresc: str) -> list[str]:
    """Ta sama logika co w bramce I-1."""
    znalezione = []
    for pakiet in PAKIETY_ZAKAZANE:
        wzorzec = re.compile(rf"(?<![\w-]){re.escape(pakiet)}(?![\w-])", re.IGNORECASE)
        for linia in tresc.splitlines():
            if wzorzec.search(linia.split("#", 1)[0]):
                znalezione.append(pakiet)
                break
    return znalezione


def _wykryj_nieprzypiete(tresc: str) -> list[str]:
    """Ta sama logika co w bramce I-8."""
    return [
        m.group(1)
        for linia in tresc.splitlines()
        if (m := WZORZEC_OBRAZU.match(linia.split("#", 1)[0]))
        and "@sha256:" not in m.group(1)
    ]


def test_bramka_i1_wykrywa_powrot_sdk():
    """Gdyby merge przywrócił ekstras — bramka musi to zobaczyć."""
    zatrute = "pydantic-ai-slim[openai,anthropic,google,mcp]>=1.107.1,<2\n"
    wykryte = _wykryj_zakazane(zatrute)
    assert "anthropic" in wykryte and "mcp" in wykryte, (
        "Bramka I-1 NIE wykryła przywróconych ekstras. "
        "Bramka jest nieskuteczna — napraw ją, zanim zaufasz jej wynikom."
    )


def test_bramka_i1_wykrywa_telemetrie():
    assert "posthog" in _wykryj_zakazane("posthog==7.35.4\n")


def test_bramka_i1_nie_blokuje_openai():
    """openai musi przejść — jest transportem do Ollamy (U-1)."""
    assert _wykryj_zakazane("openai>=2.52.0,<3\n") == [], (
        "Bramka I-1 blokuje 'openai'. To błąd: usunięcie tego pakietu "
        "zepsułoby model lokalny (ustalenie U-1, ADR-0003)."
    )


def test_bramka_i1_nie_lapie_podobnych_nazw():
    """Granice słowa — bez fałszywych trafień."""
    bezpieczne = "mcpower==1.0\ngoogle-auth==2.0\nanthropic-like-lib==1.0\n"
    assert _wykryj_zakazane(bezpieczne) == []


def test_bramka_i8_wykrywa_tag_latest():
    assert _wykryj_nieprzypiete("    image: privacy-filter:latest\n")


def test_bramka_i8_wykrywa_brak_tagu():
    assert _wykryj_nieprzypiete("    image: redis\n")


def test_bramka_i8_akceptuje_digest():
    przypiety = "    image: redis@sha256:" + "a" * 64 + "\n"
    assert _wykryj_nieprzypiete(przypiety) == []


def test_bramka_i8_pomija_komentarze():
    """Zakomentowany obraz nie jest obrazem."""
    assert _wykryj_nieprzypiete("    # image: redis:6\n") == []
