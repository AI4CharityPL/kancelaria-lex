#!/usr/bin/env bash
# Własne CA dla kancelaria-lex — zamiast ACME (ustalenie U-6).
#
# Upstream Traefik używa Let's Encrypt, co Z DEFINICJI wymaga połączenia
# wychodzącego i publicznie rozwiązywalnej domeny. W środowisku zamkniętym
# nie ma prawa działać.
#
# Uruchomienie:  bash infra/ca/utworz-ca.sh

set -euo pipefail

KATALOG="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DNI_CA=3650
DNI_SERWER=825
DOMENA="${LEX_DOMENA:-kancelaria-lex.local}"

echo "═══════════════════════════════════════════════════════════════"
echo "  Tworzenie własnego CA — bez ACME, bez połączeń wychodzących"
echo "  Domena: ${DOMENA}"
echo "═══════════════════════════════════════════════════════════════"

if [[ -f "${KATALOG}/ca.key" ]]; then
    echo "✗ ${KATALOG}/ca.key już istnieje."
    echo "  Nadpisanie unieważni wszystkie wydane certyfikaty."
    echo "  Usuń ręcznie, jeśli na pewno chcesz zacząć od nowa."
    exit 1
fi

# ── CA ──────────────────────────────────────────────────────────────
openssl genrsa -out "${KATALOG}/ca.key" 4096
chmod 600 "${KATALOG}/ca.key"

openssl req -x509 -new -nodes \
    -key "${KATALOG}/ca.key" \
    -sha256 -days "${DNI_CA}" \
    -out "${KATALOG}/ca.crt" \
    -subj "/C=PL/O=Kancelaria/OU=kancelaria-lex/CN=kancelaria-lex Root CA"

# ── Certyfikat serwera ──────────────────────────────────────────────
openssl genrsa -out "${KATALOG}/serwer.key" 2048
chmod 600 "${KATALOG}/serwer.key"

cat > "${KATALOG}/serwer.cnf" <<EOF
[req]
distinguished_name = dn
req_extensions     = ext
prompt             = no

[dn]
C  = PL
O  = Kancelaria
CN = ${DOMENA}

[ext]
basicConstraints = CA:FALSE
keyUsage         = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName   = @alt

[alt]
DNS.1 = ${DOMENA}
DNS.2 = localhost
IP.1  = 127.0.0.1
EOF

openssl req -new \
    -key "${KATALOG}/serwer.key" \
    -out "${KATALOG}/serwer.csr" \
    -config "${KATALOG}/serwer.cnf"

openssl x509 -req \
    -in "${KATALOG}/serwer.csr" \
    -CA "${KATALOG}/ca.crt" -CAkey "${KATALOG}/ca.key" -CAcreateserial \
    -out "${KATALOG}/serwer.crt" \
    -days "${DNI_SERWER}" -sha256 \
    -extfile "${KATALOG}/serwer.cnf" -extensions ext

rm -f "${KATALOG}/serwer.csr"

echo
echo "✓ Gotowe:"
echo "    ca.crt      — do zainstalowania w przeglądarkach kancelarii"
echo "    serwer.crt  — dla Traefika"
echo "    serwer.key  — klucz prywatny (chmod 600)"
echo
echo "⚠️  KLUCZE NIE TRAFIAJĄ DO REPOZYTORIUM — patrz .gitignore"
echo "⚠️  Ważność certyfikatu serwera: ${DNI_SERWER} dni."
echo "    Wpisz datę odnowienia do kalendarza — bez ACME nikt nie odnowi"
echo "    go automatycznie, a wygaśnięcie zatrzyma dostęp do systemu."
echo
echo "Profil produkcyjny wymaga dodatkowo mTLS — certyfikatów klientów"
echo "wydanych z tego samego CA (docs/10-operacje/runbook-wdrozenie.md)."
