"""Zadania w tle — analiza trwa, a użytkownik musi widzieć postęp.

PROBLEM Z POPRZEDNIĄ WERSJĄ
    Pytanie szło synchronicznie w jednym żądaniu HTTP. Przycisk gasł
    na „Analizuję akta…" i nie działo się nic widocznego przez minutę
    albo dłużej. Nie dało się odróżnić pracy od zawieszenia, a przy
    stu dokumentach analiza z założenia trwa.

ROZWIĄZANIE
    POST uruchamia zadanie i wraca natychmiast z identyfikatorem.
    Panel odpytuje o postęp: który etap, który dokument z ilu.

Zadania żyją w pamięci procesu — po restarcie panelu przepadają.
To świadome uproszczenie: wynik analizy i tak trafia do historii czatu
w bazie, więc traci się co najwyżej wgląd w przebieg trwającego zadania.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class Zadanie:
    id: str
    stan: str = "oczekuje"          # oczekuje | trwa | gotowe | blad
    etap: str = ""
    zrobione: int = 0
    wszystkie: int = 0
    wynik: Any = None
    blad: str | None = None
    utworzono: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(
            timespec="seconds"))

    def na_slownik(self) -> dict:
        return {
            "id": self.id, "stan": self.stan, "etap": self.etap,
            "zrobione": self.zrobione, "wszystkie": self.wszystkie,
            "wynik": self.wynik, "blad": self.blad,
        }


class Kolejka:
    """Prosty rejestr zadań w tle.

    Limit równoległości wynosi 1 — model na 8 GB VRAM i tak obsługuje
    jedno zapytanie naraz, a dwa równoległe wypchnęłyby warstwy na CPU
    i spowolniły oba (patrz docs/12-sprzet-i-koszty.md).
    """

    def __init__(self, maks_historii: int = 50):
        self._zadania: dict[str, Zadanie] = {}
        self._kolejnosc: list[str] = []
        self._zamek = threading.Lock()
        self._slot = threading.Semaphore(1)
        self._maks = maks_historii

    def uruchom(self, praca: Callable[[Callable[[str, int, int], None]], Any]) -> str:
        zadanie = Zadanie(id=uuid.uuid4().hex[:12])
        with self._zamek:
            self._zadania[zadanie.id] = zadanie
            self._kolejnosc.append(zadanie.id)
            while len(self._kolejnosc) > self._maks:
                self._zadania.pop(self._kolejnosc.pop(0), None)

        def melduj(etap: str, zrobione: int = 0, wszystkie: int = 0):
            with self._zamek:
                zadanie.etap = etap
                zadanie.zrobione = zrobione
                zadanie.wszystkie = wszystkie

        def bieg():
            with self._slot:
                with self._zamek:
                    zadanie.stan = "trwa"
                try:
                    wynik = praca(melduj)
                    with self._zamek:
                        zadanie.wynik = wynik
                        zadanie.stan = "gotowe"
                        zadanie.etap = "Gotowe"
                except Exception as e:                   # noqa: BLE001
                    with self._zamek:
                        zadanie.blad = f"{type(e).__name__}: {e}"
                        zadanie.stan = "blad"
                        zadanie.etap = "Błąd"

        threading.Thread(target=bieg, daemon=True).start()
        return zadanie.id

    def stan(self, zadanie_id: str) -> dict | None:
        with self._zamek:
            zadanie = self._zadania.get(zadanie_id)
            return zadanie.na_slownik() if zadanie else None

    def ile_czeka(self) -> int:
        with self._zamek:
            return sum(1 for z in self._zadania.values()
                       if z.stan in ("oczekuje", "trwa"))
