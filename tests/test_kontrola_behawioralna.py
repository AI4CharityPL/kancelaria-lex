"""Czy kontroler POTRAFI powiedzieć NIE — na żywym modelu.

⚠️ POWÓD ISTNIENIA TEGO PLIKU

`tests/test_kontrola.py` sprawdza budowę zapytania i obsługę awarii
na atrapach. Nie odpowiada na pytanie najważniejsze: czy kontroler
w ogóle rozróżnia zdanie popierające twierdzenie od przeczącego mu.

Pomiar z 14.08.2026 pokazał, dlaczego to trzeba sprawdzać osobno:
w przebiegu na realnych przypadkach kontroler zwrócił „prawda"
sześć razy na sześć. Wyglądało to na kontrolę, która zawsze przepuszcza —
czyli gorszą od jej braku, bo daje złudzenie sprawdzenia (ta sama
zasada, co przy bramce izolacji: brak Dockera nie daje wyniku
pozytywnego).

Ta próba wykazała, że było inaczej: warstwa mechaniczna
(`panel/wsparcie.py`) odsiewała złe przypadki wcześniej, więc do
kontrolera docierały wyłącznie faktycznie poparte. Bez tego testu
nie dało się tych dwóch sytuacji odróżnić.

Uruchamianie osobno, bo wymaga modelu:
    pytest -m behawioralny
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panel"))

import kontrola  # noqa: E402

pytestmark = pytest.mark.behawioralny


# (język, twierdzenie, cytat, oczekiwany werdykt, opis)
ROZNICUJACE = [
    ("pl", "Świadek rozpoznał kierowcę pojazdu.",
           "Świadek zeznał, że nie był w stanie rozpoznać kierowcy pojazdu.",
           "falsz", "odwrócona negacja"),
    ("pl", "Sąd uwzględnił apelację obrońcy.",
           "Sąd nie uwzględnił apelacji obrońcy i utrzymał wyrok w mocy.",
           "falsz", "negacja"),
    ("pl", "Oskarżony przyznał się do winy.",
           "Sąd zasądził od oskarżonego koszty procesu w kwocie 1.008,00 zł.",
           "falsz", "zupełnie inna treść"),
    ("pl", "Termin do wniesienia apelacji wynosi 14 dni.",
           "Termin do wniesienia apelacji wynosi 7 dni od doręczenia wyroku.",
           "falsz", "inna liczba — 14 wobec 7"),
    ("en", "The court granted the motion.",
           "The court denied the motion in its entirety.",
           "falsz", "odwrócona negacja (EN)"),
    ("en", "The defendant was present at the hearing.",
           "The Clerk of Court is directed to file the exhibits under seal.",
           "falsz", "zupełnie inna treść (EN)"),
    ("pl", "Sąd zasądził koszty procesu od oskarżonego.",
           "Na podstawie art. 627 k.p.k. sąd zasądza od oskarżonego koszty procesu.",
           "prawda", "kontrolny pozytywny"),
    ("en", "Counsel waived service of the complaint.",
           "Counsel for Individual Defendants waived service and accepted "
           "a copy of the Complaint.",
           "prawda", "kontrolny pozytywny (EN)"),
]


@pytest.mark.parametrize("jezyk,twierdzenie,cytat,oczekiwany,opis", ROZNICUJACE,
                         ids=[p[4] for p in ROZNICUJACE])
def test_kontroler_rozroznia(jezyk, twierdzenie, cytat, oczekiwany, opis):
    wynik = kontrola.sprawdz(twierdzenie, [cytat], jezyk)

    if wynik.werdykt is kontrola.Werdykt.NIEZWERYFIKOWANE:
        pytest.skip(f"model niedostępny: {wynik.powod}")

    assert wynik.werdykt.value == oczekiwany, (
        f"{opis}: oczekiwano {oczekiwany}, jest {wynik.werdykt.value}. "
        f"Uzasadnienie kontrolera: {wynik.powod}"
    )


def test_kontroler_potrafi_odrzucic():
    """Bramka nadrzędna: przy odwróconej negacji MUSI paść „falsz".

    Gdyby kontroler nie potrafił nigdy odrzucić, cała warstwa 4 byłaby
    ozdobnikiem — kosztowałaby sekundy na twierdzenie i nie wnosiła nic.
    """
    wynik = kontrola.sprawdz(
        "Świadek rozpoznał kierowcę pojazdu.",
        ["Świadek zeznał, że nie był w stanie rozpoznać kierowcy pojazdu."],
        "pl")

    if wynik.werdykt is kontrola.Werdykt.NIEZWERYFIKOWANE:
        pytest.skip(f"model niedostępny: {wynik.powod}")

    assert wynik.werdykt is kontrola.Werdykt.FALSZ, (
        "KONTROLER NIGDY NIE ODRZUCA — warstwa 4 nie wnosi niczego, "
        "a kosztuje wywołanie modelu na każde twierdzenie. Kontrola, "
        "która zawsze przepuszcza, jest gorsza od jej braku."
    )
