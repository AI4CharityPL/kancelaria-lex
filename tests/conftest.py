"""Opcje wiersza poleceń wspólne dla całego przebiegu.

⚠️ DLACZEGO `pytest_addoption` STOI TUTAJ, A NIE PRZY TESTACH IZOLACJI

Pytest przyjmuje `pytest_addoption` wyłącznie z conftestu początkowego —
z katalogu głównego albo z katalogu wskazanego w `testpaths`. Definicja
w `tests/izolacja/conftest.py` rejestrowała się dopiero na etapie
zbierania testów, czyli PO sparsowaniu wiersza poleceń.

Skutek był taki, że `--dozwol-pominiecie` działało z poziomu kodu
(`request.config.getoption`), ale próba podania go w wierszu poleceń
kończyła się błędem „unrecognized arguments" — mimo że i
`docs/11-testy-i-bramki.md`, i komunikat samej bramki instruowały
operatora, żeby go użył.

Furtka bezpieczeństwa, z której nie da się skorzystać, jest gorsza
od jej braku: pod presją ktoś sięgnie po `-k`, `--ignore` albo
`--no-verify` i wyłączy znacznie więcej, niż zamierzał.
"""

from __future__ import annotations


def pytest_addoption(parser):
    parser.addoption(
        "--dozwol-pominiecie",
        action="store_true",
        default=False,
        help="Pozwól pominąć testy wymagające Dockera zamiast zgłosić błąd. "
             "Używać świadomie — pominięty test izolacji nie jest testem zaliczonym.",
    )
