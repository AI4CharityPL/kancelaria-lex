#!/usr/bin/env bash
# Przypina obrazy w compose.yml po sumie sha256 (ustalenie U-5, bramka I-8).
#
# Upstream używa tagów ':latest' z prywatnych przestrzeni rejestru
# (jscrudato/*, ghcr.io/jsv4/*). Treść takiego obrazu może się zmienić
# między jednym pobraniem a drugim, bez śladu w repozytorium.
# Przy aktach karnych jest to nie do przyjęcia.
#
# Uruchomienie:  bash skrypty/pobierz-digesty.sh
# Wymaga dostępu do sieci — uruchamiać w strefie przygotowawczej,
# nigdy na maszynie produkcyjnej.

set -euo pipefail

KORZEN="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="${KORZEN}/infra/compose/compose.yml"

echo "═══════════════════════════════════════════════════════════════"
echo "  Pobieranie sum sha256 dla obrazów z ${COMPOSE##*/}"
echo "═══════════════════════════════════════════════════════════════"
echo

# Obrazy z tagami — do przypięcia.
# ⚠️ KOMENTARZ W TEJ SAMEJ LINII TRZEBA ODCIĄĆ — NAPRAWIONE 16.08.2026.
#
# Pierwsza wersja brała wszystko po `image:` do końca wiersza, razem
# z komentarzem. W compose stoi np.:
#
#     image: gotenberg/gotenberg:8      # TODO: przypiąć po sha256
#
# więc do `docker pull` szła nazwa z doklejonym „# TODO…" i siedem z ośmiu
# obrazów kończyło się komunikatem „nie udało się pobrać — sprawdź nazwę".
# Wyglądało to na brak dostępu do rejestru, a było błędem rozbioru.
# Jedyny obraz, który przechodził, był jedynym bez komentarza w linii.
mapfile -t OBRAZY < <(
    grep -E '^\s*image:' "${COMPOSE}" \
    | sed -E 's/^\s*image:\s*//' \
    | sed -E 's/#.*$//' \
    | sed -E 's/[[:space:]]+$//' \
    | grep -v '^$' \
    | grep -v '@sha256:' \
    | sort -u
)

if [[ ${#OBRAZY[@]} -eq 0 ]]; then
    echo "✓ Wszystkie obrazy są już przypięte po sha256."
    exit 0
fi

echo "Do przypięcia: ${#OBRAZY[@]}"
echo

for obraz in "${OBRAZY[@]}"; do
    echo "── ${obraz}"
    if ! docker pull --quiet "${obraz}" >/dev/null 2>&1; then
        echo "   ✗ nie udało się pobrać — sprawdź nazwę i dostęp do rejestru"
        continue
    fi

    digest="$(docker inspect --format='{{index .RepoDigests 0}}' "${obraz}" 2>/dev/null || true)"
    if [[ -z "${digest}" ]]; then
        echo "   ✗ brak RepoDigest (obraz zbudowany lokalnie?) — pomijam"
        continue
    fi

    echo "   ${digest}"
    echo "   ${obraz}  →  ${digest}" >> "${KORZEN}/infra/digesty.txt"
done

echo
echo "═══════════════════════════════════════════════════════════════"
echo "  Sumy zapisane do infra/digesty.txt"
echo
echo "  DALEJ — ręcznie, świadomie:"
echo "  1. Przejrzyj infra/digesty.txt."
echo "  2. Wstaw sumy do compose.yml w miejsce tagów."
echo "  3. Uruchom: pytest tests/izolacja/test_czystosc_builda.py"
echo "     Bramka I-8 musi przejść."
echo
echo "  Podmiana NIE jest automatyczna celowo — przypięcie obrazu to"
echo "  decyzja o tym, jaki kod będzie przetwarzał akta. Wymaga"
echo "  przeglądu, nie skryptu."
echo "═══════════════════════════════════════════════════════════════"
