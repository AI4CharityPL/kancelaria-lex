<#
.SYNOPSIS
    Uruchamia bramki jakościowe i izolacji.

.DESCRIPTION
    DLACZEGO LOKALNIE, A NIE W GITHUB ACTIONS

    Bo to repozytorium nie powinno opuszczać kancelarii. Zawiera model
    zagrożeń, topologię sieci, opis warstw izolacji i mapowanie
    obowiązków KSC — czyli instrukcję, gdzie szukać słabych punktów
    instancji przetwarzającej akta karne. Sam fakt prowadzenia sprawy
    jest objęty tajemnicą zawodową; metadane też (T-3).

    Wysłanie tego na cudzy serwer po to, żeby uruchomił `pytest`,
    byłoby dokładnie tym kompromisem, którego cała architektura unika.
    Bramki chodzą więc tam, gdzie chodzi system.

    Podział wyniku odpowiada docs/11-testy-i-bramki.md:

      GRUPA 1   izolacja (I-1…I-9)     — każdy build, próg 100%
      GRUPA 1b  wstrzyknięcia          — każdy build, próg 100%
      KONFIG.   serwer modelu          — maszyna z Ollamą
      JEDNOSTK. reszta

.PARAMETER Szybkie
    Pomiń bramki wymagające Dockera i działającego modelu.

.PARAMETER Zainstaluj
    Zainstaluj hak pre-commit uruchamiający testy jednostkowe.

.EXAMPLE
    powershell -File skrypty/bramki.ps1
    powershell -File skrypty/bramki.ps1 -Szybkie
    powershell -File skrypty/bramki.ps1 -Zainstaluj
#>
[CmdletBinding()]
param(
    [switch]$Szybkie,
    [switch]$Zainstaluj
)

$ErrorActionPreference = 'Stop'
$KORZEN = Split-Path -Parent $PSScriptRoot

# ── instalacja haka ──────────────────────────────────────────────────

if ($Zainstaluj) {
    $katalog = Join-Path $KORZEN '.git\hooks'
    if (-not (Test-Path $katalog)) { throw "Brak $katalog — czy to na pewno repozytorium git?" }

    $hak = Join-Path $katalog 'pre-commit'
    # Hak celowo NIE uruchamia bramek wymagających Dockera ani modelu —
    # commit ma być szybki. Pełny przebieg należy do wydania.
    @'
#!/bin/sh
# kancelaria-lex — hak pre-commit.
# Szybkie testy jednostkowe. Bramki izolacji i konfiguracji wymagają
# Dockera i Ollamy, więc idą osobno: powershell -File skrypty/bramki.ps1
echo "kancelaria-lex: testy jednostkowe..."
python -m pytest -q -m "not izolacja and not konfiguracja and not behawioralny" \
    --no-header -p no:cacheprovider
if [ $? -ne 0 ]; then
    echo ""
    echo "Testy nie przeszły — commit wstrzymany."
    echo "Pominięcie (świadome): git commit --no-verify"
    exit 1
fi
'@ | Set-Content -Path $hak -Encoding ascii -NoNewline

    Write-Host "Zainstalowano hak: $hak" -ForegroundColor Green
    Write-Host 'Uruchamia testy jednostkowe przed każdym commitem.'
    return
}

# ── przebieg bramek ──────────────────────────────────────────────────

Push-Location $KORZEN
try {
    $grupy = @(
        @{ Nazwa = 'Testy jednostkowe'
           Args  = @('-m', 'not izolacja and not konfiguracja and not behawioralny')
           Krytyczna = $true }
        @{ Nazwa = 'Bramki izolacji (I-1…I-9)'
           Args  = @('-m', 'izolacja')
           Krytyczna = $true }
        @{ Nazwa = 'Konfiguracja serwera modelu'
           Args  = @('-m', 'konfiguracja')
           Krytyczna = -not $Szybkie }
    )

    $wyniki = @()
    foreach ($g in $grupy) {
        # W trybie szybkim bramka konfiguracji nie jest uruchamiana wcale.
        # Uruchomienie jej i zignorowanie wyniku byłoby gorsze: dawałoby
        # zielony przebieg tam, gdzie nic nie sprawdzono.
        if ($Szybkie -and -not $g.Krytyczna) {
            $wyniki += [PSCustomObject]@{
                Grupa = $g.Nazwa; Kod = $null; Krytyczna = $false }
            continue
        }

        Write-Host ''
        Write-Host ('─' * 66) -ForegroundColor DarkGray
        Write-Host "  $($g.Nazwa)" -ForegroundColor Cyan
        Write-Host ('─' * 66) -ForegroundColor DarkGray

        $argumenty = @('-m', 'pytest', '-q', '--no-header', '-p', 'no:cacheprovider') + $g.Args
        if ($Szybkie) { $argumenty += '--dozwol-pominiecie' }

        & python @argumenty

        $wyniki += [PSCustomObject]@{
            Grupa     = $g.Nazwa
            Kod       = $LASTEXITCODE
            Krytyczna = $g.Krytyczna
        }
    }

    Write-Host ''
    Write-Host ('=' * 66) -ForegroundColor DarkCyan
    Write-Host '  PODSUMOWANIE' -ForegroundColor Cyan
    Write-Host ('=' * 66) -ForegroundColor DarkCyan

    $padl = $false
    foreach ($w in $wyniki) {
        if ($null -eq $w.Kod) {
            Write-Host ("  [   ]  " + $w.Grupa + '  — NIE URUCHOMIONA (-Szybkie)') -ForegroundColor DarkYellow
        } elseif ($w.Kod -eq 0) {
            Write-Host ("  [ OK ]  " + $w.Grupa) -ForegroundColor Green
        } else {
            Write-Host ("  [PADL]  " + $w.Grupa) -ForegroundColor Red
            $padl = $true
        }
    }

    if ($Szybkie) {
        Write-Host ''
        Write-Host '  Tryb szybki: część bramek nie została wykonana.' -ForegroundColor DarkYellow
        Write-Host '  Przed wydaniem wymagany pełny przebieg bez -Szybkie.' -ForegroundColor DarkYellow
    }

    Write-Host ''
    if ($padl) {
        Write-Host '  Bramka niezaliczona. Pominięty test bezpieczeństwa' -ForegroundColor Red
        Write-Host '  NIE jest testem zaliczonym (docs/11-testy-i-bramki.md).' -ForegroundColor Red
        Write-Host ''
        exit 1
    }
    Write-Host '  Wszystkie uruchomione bramki zaliczone.' -ForegroundColor Green
    Write-Host ''
}
finally { Pop-Location }
