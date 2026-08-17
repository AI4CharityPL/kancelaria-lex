<#
.SYNOPSIS
    Uruchamia panel spraw kancelaria-lex z poprawną konfiguracją modelu.

.DESCRIPTION
    Skrypt robi trzy rzeczy, w tej kolejności:

      1. Ustawia zmienne środowiskowe serwera Ollamy — NA STAŁE dla
         użytkownika, nie tylko na czas tej konsoli.
      2. Restartuje serwer Ollamy, jeżeli pracuje na starych ustawieniach.
      3. Sprawdza modele i podnosi panel.

    KROK 2 JEST NIEZBĘDNY I NIEOCZYWISTY. Serwer Ollamy czyta swoje
    zmienne WYŁĄCZNIE przy starcie. Ustawienie ich w otwartej konsoli
    nie zmienia nic w procesie, który już działa — i dokładnie tak
    naprawa wydajnościowa z 14.08.2026 „przepadła" mimo opisania jej
    w raporcie.

    Źródłem wartości jest panel/konfiguracja.py, żeby skrypt i test
    (tests/test_konfiguracja_ollamy.py) nie mogły się rozjechać.

.PARAMETER TylkoKonfiguracja
    Ustaw zmienne i zrestartuj Ollamę, ale nie podnoś panelu.

.PARAMETER Force
    Nie pytaj o zgodę na restart serwera Ollamy.

.EXAMPLE
    powershell -File skrypty/start.ps1
    powershell -File skrypty/start.ps1 -TylkoKonfiguracja
#>
[CmdletBinding()]
param(
    [switch]$TylkoKonfiguracja,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$KORZEN = Split-Path -Parent $PSScriptRoot

function Naglowek($tekst) {
    Write-Host ''
    Write-Host ('=' * 66) -ForegroundColor DarkCyan
    Write-Host "  $tekst" -ForegroundColor Cyan
    Write-Host ('=' * 66) -ForegroundColor DarkCyan
}

# ── 1. konfiguracja ──────────────────────────────────────────────────

Naglowek 'KONFIGURACJA SERWERA MODELU'

# Wartości czytane z panel/konfiguracja.py — jedno źródło prawdy.
$surowe = & python -c @"
import json, sys
sys.path.insert(0, r'$KORZEN\panel')
import konfiguracja
print(json.dumps({'wymagane': konfiguracja.WYMAGANE,
                  'zakazane': list(konfiguracja.ZAKAZANE)}))
"@
if ($LASTEXITCODE -ne 0) { throw 'Nie udało się odczytać panel/konfiguracja.py' }
$cfg = $surowe | ConvertFrom-Json

$zmieniono = $false

foreach ($wpis in $cfg.wymagane.PSObject.Properties) {
    $nazwa, $oczekiwana = $wpis.Name, $wpis.Value
    $biezaca = [Environment]::GetEnvironmentVariable($nazwa, 'User')
    if ($biezaca -ne $oczekiwana) {
        [Environment]::SetEnvironmentVariable($nazwa, $oczekiwana, 'User')
        Write-Host "  ustawiono  $nazwa = $oczekiwana" -ForegroundColor Yellow
        $zmieniono = $true
    } else {
        Write-Host "  ok         $nazwa = $oczekiwana" -ForegroundColor DarkGray
    }
    # Także w bieżącym procesie, żeby test uruchomiony zaraz po skrypcie
    # widział już nowy stan.
    Set-Item -Path "Env:$nazwa" -Value $oczekiwana
}

foreach ($nazwa in $cfg.zakazane) {
    if ($null -ne [Environment]::GetEnvironmentVariable($nazwa, 'User')) {
        [Environment]::SetEnvironmentVariable($nazwa, $null, 'User')
        Write-Host "  usunieto   $nazwa" -ForegroundColor Yellow
        $zmieniono = $true
    }
    if (Test-Path "Env:$nazwa") { Remove-Item "Env:$nazwa" }
}

# ── 2. restart serwera Ollamy ────────────────────────────────────────

$procesy = @(Get-Process 'ollama', 'ollama app' -ErrorAction SilentlyContinue)

# ⚠️ NIE WYSTARCZY SPRAWDZIĆ, CZY TEN SKRYPT COŚ ZMIENIŁ.
#
# Serwer mógł wystartować dawno temu i odziedziczyć wtedy stare wartości,
# nawet jeśli profil użytkownika jest od dawna poprawny. Dokładnie tak
# było 14.08.2026: zmienne ustawione dobrze, serwer chodził od dwóch
# godzin na ośmiu slotach z cache'em f16, a sprawdzenie konfiguracji
# pokazywało „wszystko w porządku".
#
# Dlatego pytamy o stan ŻYWEGO serwera, czytając jego log.
$stary = & python -c @"
import sys
sys.path.insert(0, r'$KORZEN\panel')
import konfiguracja
print('\n'.join(konfiguracja.serwer_wymaga_restartu()))
"@
$serwerStary = -not [string]::IsNullOrWhiteSpace(($stary -join ''))

if (($zmieniono -or $serwerStary) -and $procesy.Count -gt 0) {
    Naglowek 'RESTART SERWERA OLLAMY'
    if ($serwerStary) {
        Write-Host '  Działający serwer pracuje na starych ustawieniach:' -ForegroundColor Yellow
        foreach ($l in @($stary)) {
            if (-not [string]::IsNullOrWhiteSpace($l)) {
                Write-Host "    - $l" -ForegroundColor Yellow
            }
        }
        Write-Host ''
    }
    Write-Host '  Serwer Ollamy czyta zmienne wyłącznie przy starcie.'
    Write-Host '  Bez restartu poprawna konfiguracja nic nie zmieni.'
    Write-Host ''

    $zgoda = $Force
    if (-not $zgoda) {
        $odp = Read-Host '  Zrestartować serwer Ollamy? [t/N]'
        $zgoda = $odp -match '^[tTyY]'
    }

    if ($zgoda) {
        $procesy | Stop-Process -Force
        Start-Sleep -Milliseconds 1500
        $aplikacja = "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe"
        if (Test-Path $aplikacja) {
            Start-Process $aplikacja
        } else {
            Start-Process 'ollama' -ArgumentList 'serve' -WindowStyle Hidden
        }
        Write-Host '  Serwer zrestartowany.' -ForegroundColor Green
    } else {
        Write-Warning ('Serwer pracuje na starych ustawieniach. ' +
                       'Analiza bedzie do ~18x wolniejsza.')
    }
} elseif ($zmieniono) {
    Write-Host ''
    Write-Host '  Serwer Ollamy nie działa — wystartuje z nowymi ustawieniami.' -ForegroundColor DarkGray
}

# Poczekaj, aż serwer odpowie.
$gotowy = $false
foreach ($i in 1..30) {
    try {
        Invoke-RestMethod 'http://127.0.0.1:11434/api/version' -TimeoutSec 2 | Out-Null
        $gotowy = $true
        break
    } catch { Start-Sleep -Milliseconds 700 }
}
if (-not $gotowy) {
    Write-Warning 'Serwer Ollamy nie odpowiada pod 127.0.0.1:11434. Uruchom Ollamę i powtórz.'
}

# ── 3. modele i panel ────────────────────────────────────────────────

if ($gotowy) {
    Naglowek 'MODELE'
    $obecne = (Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5).models.name
    $brakujace = @()
    foreach ($m in @('bielik-lex-map', 'llama-lex-map', 'bielik-lex-dev')) {
        if ($obecne -match "^$m(:latest)?$") {
            Write-Host "  jest       $m" -ForegroundColor DarkGray
        } else {
            Write-Host "  BRAK       $m" -ForegroundColor Red
            $brakujace += $m
        }
    }
    if ($brakujace.Count -gt 0) {
        Write-Host ''
        Write-Host '  Zbuduj brakujące modele:' -ForegroundColor Yellow
        Write-Host '    powershell -File skrypty/przygotuj-modele.ps1' -ForegroundColor Yellow
    }
}

if ($TylkoKonfiguracja) {
    Write-Host ''
    Write-Host 'Konfiguracja gotowa. Panel nieuruchomiony (-TylkoKonfiguracja).'
    Write-Host 'Sprawdzenie:  python -m pytest tests/test_konfiguracja_ollamy.py'
    return
}

# Port zajęty oznacza zwykle panel uruchomiony wcześniej — z poprzednim
# kodem. Lepiej powiedzieć to wprost, niż wywalić się na "address in use".
$zajety = Get-NetTCPConnection -LocalPort 8713 -State Listen -ErrorAction SilentlyContinue
if ($zajety) {
    Write-Warning ("Port 8713 jest już zajęty (PID $($zajety.OwningProcess)). " +
                   'Panel prawdopodobnie działa — i to na kodzie sprzed zmian. ' +
                   'Zatrzymaj go, żeby wystartował z nowym kodem.')
    return
}

Naglowek 'PANEL'
Push-Location $KORZEN
try { & python panel/serwer.py } finally { Pop-Location }
