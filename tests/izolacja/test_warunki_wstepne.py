"""Pojedynczy, celowo głośny sygnał o niewykonanych bramkach izolacji.

Bez tego testu brak Dockera dawałby wynik "wszystko pominięte, zero
błędów" — czyli dokładnie to, przed czym ostrzega docs/11-testy-i-bramki.md:
test bezpieczeństwa, który nie potrafi paść, jest gorszy niż jego brak.

Ten test zapewnia, że przebieg bez sprawdzonej izolacji JEST czerwony,
a komunikat da się przeczytać bez przewijania osiemdziesięciu błędów.
"""

from __future__ import annotations

import pytest

from conftest import KOMUNIKAT_BRAK_DOCKERA, docker_dostepny


def test_docker_dostepny_dla_bramek_izolacji(request):
    """Bramki I-3, I-4, I-5 wymagają działającego stosu."""
    if docker_dostepny():
        return
    if request.config.getoption("--dozwol-pominiecie"):
        pytest.skip(KOMUNIKAT_BRAK_DOCKERA)
    pytest.fail(KOMUNIKAT_BRAK_DOCKERA, pytrace=False)
