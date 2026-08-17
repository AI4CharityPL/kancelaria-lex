"""Schematy JSON wymuszane przy dekodowaniu — warstwa 1 precyzji.

════════════════════════════════════════════════════════════════════════
 CO TO ZMIENIA
════════════════════════════════════════════════════════════════════════

Dotąd wywołania szły z `"format": "json"`, co wymusza wyłącznie POPRAWNY
JSON — dowolnej treści. Kształt odpowiedzi był prośbą w szablonie,
a jego niedotrzymanie trzeba było łatać po fakcie (normalizacja nazw
kluczy w analiza.py, przyjmowanie wariantów pisowni „watki"/„wątki").

Ollama od wersji 0.5 przyjmuje pełny **schemat JSON** i kompiluje go do
gramatyki: przy próbkowaniu zeruje prawdopodobieństwo każdego tokenu,
który złamałby schemat. Mamy 0.32.9.

Konsekwencja dla cytowania jest jakościowa, nie ilościowa. Gdy pole
`zdania` ma `enum` z numerami faktycznie pokazanych zdań, numer spoza
zakresu **przestaje być możliwy do wygenerowania**. Cytat nie jest
odrzucany na weryfikacji — jest niewyrażalny.

    warstwa 1  NIEWYRAŻALNE   ← ten plik
    warstwa 2  WERYFIKOWALNE  ← weryfikator_cytatow.py, porównanie znaków
    warstwa 3  ODEJMUJĄCE     ← planowane NLI (ADR-0008)

════════════════════════════════════════════════════════════════════════
 ⚠️ GRANICA GWARANCJI — WAŻNIEJSZA NIŻ SAMA GWARANCJA
════════════════════════════════════════════════════════════════════════

Gramatyka zapewnia POPRAWNOŚĆ FORMY, nie TRAFNOŚĆ WYBORU. Dokumentacja
Ollamy mówi to wprost o polach `enum`: wartość jest zawsze dopuszczalna,
ale niekoniecznie właściwa, gdy model jest niepewny.

Sprawdzone doświadczalnie 14.08.2026 na `bielik-lex-map`: przy schemacie
dopuszczającym wyłącznie `enum: [7]` i dokumencie mającym pięć zdań model
zwrócił `[7, 7]` — numer nieistniejący, bo tylko taki był dozwolony.
Nie potrafił wygenerować niczego innego.

Wniosek praktyczny: enum MUSI być budowany z numerów faktycznie
pokazanych zdań (`WyborZdan.numery`), nigdy z zakresu „na oko".
Schemat rozminięty z wsadem zamienia się z zabezpieczenia w wymuszacz
błędu.

Klasa błędu zmienia się więc z „model zmyślił cytat" na „model wskazał
niewłaściwe zdanie". Ta druga jest dla prawnika wykrywalna w kilka
sekund, bo cytat prowadzi do prawdziwego miejsca w aktach.
"""

from __future__ import annotations


def mapowanie(numery_zdan: list[int], maks_ustalen: int = 12,
              maks_zdan_na_ustalenie: int = 3) -> dict:
    """Schemat etapu wydobywania faktów — cytat przez NUMER zdania.

    `numery_zdan` musi pochodzić z `WyborZdan.numery` tego samego
    wywołania. Rozjazd między wsadem a schematem oznacza, że model
    zostanie zmuszony do wskazania zdania, którego nie widział.
    """
    if not numery_zdan:
        # Pusty enum jest niewyrażalny w gramatyce — zwracamy schemat
        # dopuszczający wyłącznie pustą listę ustaleń. Model nie ma
        # czego cytować i ma to powiedzieć wprost.
        return {
            "type": "object", "required": ["ustalenia"],
            "properties": {"ustalenia": {
                "type": "array", "maxItems": 0, "items": {"type": "object"}}},
        }

    return {
        "type": "object",
        "required": ["ustalenia"],
        "properties": {
            "ustalenia": {
                "type": "array",
                "maxItems": maks_ustalen,
                "items": {
                    "type": "object",
                    "required": ["tekst", "zdania"],
                    "properties": {
                        "tekst": {"type": "string", "minLength": 10},
                        "zdania": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": maks_zdan_na_ustalenie,
                            "items": {"type": "integer",
                                      "enum": list(numery_zdan)},
                        },
                    },
                },
            },
        },
    }


def twierdzenia(numery_zdan: list[int], maks: int = 10) -> dict:
    """Schemat toru szybkiego (czatu). Ta sama mechanika co `mapowanie`,
    inna nazwa klucza — historia panelu zna „twierdzenia" w czacie
    i „ustalenia" w analizie, a zmiana nazwy unieważniłaby zapisane
    wątki rozmów w bazie.
    """
    schemat = mapowanie(numery_zdan, maks_ustalen=maks)
    if "ustalenia" not in schemat["properties"]:
        return {"type": "object", "required": ["twierdzenia"],
                "properties": {"twierdzenia": {
                    "type": "array", "maxItems": 0, "items": {"type": "object"}}}}
    return {
        "type": "object",
        "required": ["twierdzenia"],
        "properties": {"twierdzenia": schemat["properties"]["ustalenia"]},
    }


def dekompozycja(maks_watkow: int = 4) -> dict:
    """Schemat rozbicia pytania na wątki analityczne.

    Usuwa całą klasę usterek, którą dotąd łatała normalizacja kluczy:
    model pisał po polsku i zwracał „wątki" tam, gdzie szablon prosił
    o „watki", a sztywny odczyt dawał ciche zero.
    """
    return {
        "type": "object",
        "required": ["watki"],
        "properties": {
            "watki": {
                "type": "array",
                "minItems": 1,
                "maxItems": maks_watkow,
                "items": {"type": "string", "minLength": 10},
            },
        },
    }


def synteza(dozwolone_ustalenia: list[int],
            numery_przepisow: list[int] | None = None) -> dict:
    """Schemat etapu syntezy — wnioski zakotwiczone w NUMERACH ustaleń.

    `oparte_na` ma `enum` z numerami ustaleń, które faktycznie przeszły
    weryfikację. Wniosek powołujący się na ustalenie nieistniejące albo
    odrzucone staje się niewyrażalny — dotąd trzeba go było wyłapywać
    po fakcie i odrzucać jako „wniosek_bez_zakotwiczenia".
    """
    kotwica = {
        "type": "array", "minItems": 1, "maxItems": 6,
        "items": {"type": "integer", "enum": list(dozwolone_ustalenia)},
    } if dozwolone_ustalenia else {"type": "array", "maxItems": 0,
                                   "items": {"type": "integer"}}

    podstawa: dict = {"type": "array", "maxItems": 0, "items": {"type": "object"}}
    if numery_przepisow:
        podstawa = {
            "type": "array", "maxItems": 6,
            "items": {
                "type": "object",
                "required": ["tekst", "przepis"],
                "properties": {
                    "tekst": {"type": "string", "minLength": 10},
                    "przepis": {"type": "integer",
                                "enum": list(numery_przepisow)},
                },
            },
        }

    return {
        "type": "object",
        "required": ["wnioski", "rozbieznosci", "luki", "podstawa_prawna"],
        "properties": {
            "wnioski": {
                "type": "array", "maxItems": 8,
                "items": {
                    "type": "object",
                    "required": ["tekst", "oparte_na"],
                    "properties": {
                        "tekst": {"type": "string", "minLength": 10},
                        "oparte_na": kotwica,
                    },
                },
            },
            "rozbieznosci": {
                "type": "array", "maxItems": 6,
                "items": {
                    "type": "object",
                    "required": ["opis", "oparte_na"],
                    "properties": {
                        "opis": {"type": "string", "minLength": 10},
                        "oparte_na": kotwica,
                    },
                },
            },
            "luki": {
                "type": "array", "maxItems": 6,
                "items": {"type": "string", "minLength": 10},
            },
            "podstawa_prawna": podstawa,
        },
    }
