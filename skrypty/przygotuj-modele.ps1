<#
.SYNOPSIS
    Buduje modele robocze kancelaria-lex z manifestów w models/.

.DESCRIPTION
    Dotąd ta wiedza istniała wyłącznie w głowie autora: który model
    bazowy, pod jaką nazwą, z jakimi parametrami. Po przeniesieniu
    na inną maszynę panel wołałby modele, których tam nie ma.

    Skrypt buduje trzy modele:

      bielik-lex-map   mapowanie dokumentów POLSKICH   (12 z 13 wywołań)
      llama-lex-map    mapowanie dokumentów ANGIELSKICH
      bielik-lex-dev   czat i synteza

    ⚠️ URUCHOMIĆ PONOWNIE PO KAŻDEJ ZMIANIE PLIKU Modelfile.
       `ollama create` zapiekają parametry (m.in. num_ctx) w model.
       Zmiana samego pliku nic nie daje, dopóki model nie zostanie
       zbudowany od nowa.

    ⚠️ POBIERANIE WAG WYMAGA SIECI. To jest czynność z okna serwisowego,
       wykonywana w strefie z dostępem do internetu, przed przeniesieniem
       instancji do strefy zamkniętej. Wagi wnosi się potem paczką
       offline — docs/10-operacje/runbook-aktualizacje.md. Licencje wag
       weryfikuje się osobno: models/manifest.md.

.PARAMETER Wymus
    Przebuduj także modele, które już istnieją.

.EXAMPLE
    powershell -File skrypty/przygotuj-modele.ps1
    powershell -File skrypty/przygotuj-modele.ps1 -Wymus
#>
[CmdletBinding()]
param([switch]$Wymus)

$ErrorActionPreference = 'Stop'
$KORZEN = Split-Path -Parent $PSScriptRoot
$MODELE = Join-Path $KORZEN 'models'

$DO_ZBUDOWANIA = @(
    @{ Nazwa = 'bielik-lex-map'; Plik = 'Modelfile.bielik-map'
       Rola = 'mapowanie dokumentów polskich' }
    @{ Nazwa = 'llama-lex-map';  Plik = 'Modelfile.llama-map'
       Rola = 'mapowanie dokumentów angielskich' }
    @{ Nazwa = 'bielik-lex-dev'; Plik = 'Modelfile.bielik-dev'
       Rola = 'czat i synteza' }
)

Write-Host ''
Write-Host ('=' * 66) -ForegroundColor DarkCyan
Write-Host '  BUDOWA MODELI ROBOCZYCH' -ForegroundColor Cyan
Write-Host ('=' * 66) -ForegroundColor DarkCyan

try {
    Invoke-RestMethod 'http://127.0.0.1:11434/api/version' -TimeoutSec 3 | Out-Null
} catch {
    throw 'Serwer Ollamy nie odpowiada pod 127.0.0.1:11434. Uruchom Ollamę i powtórz.'
}

$istniejace = (Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5).models.name

foreach ($m in $DO_ZBUDOWANIA) {
    $sciezka = Join-Path $MODELE $m.Plik
    Write-Host ''
    Write-Host "  $($m.Nazwa)" -ForegroundColor White
    Write-Host "    rola: $($m.Rola)" -ForegroundColor DarkGray

    if (-not (Test-Path $sciezka)) {
        Write-Host "    BRAK PLIKU: $sciezka" -ForegroundColor Red
        continue
    }

    $juz = $istniejace -match "^$($m.Nazwa)(:latest)?$"
    if ($juz -and -not $Wymus) {
        Write-Host '    istnieje — pomijam (-Wymus przebuduje)' -ForegroundColor DarkGray
        continue
    }

    Write-Host '    buduję…' -ForegroundColor Yellow
    & ollama create $m.Nazwa -f $sciezka
    if ($LASTEXITCODE -eq 0) {
        Write-Host '    gotowe' -ForegroundColor Green
    } else {
        Write-Host "    BŁĄD (kod $LASTEXITCODE)" -ForegroundColor Red
    }
}

Write-Host ''
Write-Host 'Sprawdzenie:  ollama list' -ForegroundColor DarkGray
Write-Host ''
