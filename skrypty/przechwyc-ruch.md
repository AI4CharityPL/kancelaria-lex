# Bramka O-1 — przechwycenie ruchu jako dowód końcowy

**Warunek dopuszczenia systemu do rzeczywistych akt.**

Ta bramka nie sprawdza konfiguracji ani kodu. Obserwuje rzeczywistość na poziomie pakietów. Wszystkie pozostałe zabezpieczenia można pomylić w ocenie — tego nie.

## Kryterium

Podczas **pełnego cyklu przetwarzania dokumentu** z mostków segmentów `net_app`, `net_ai` i `net_parse` nie wychodzi **ani jeden pakiet** poza sieć Dockera.

Pełny cykl = wgranie → konwersja → OCR → parsowanie → embedding → indeksowanie → zapytanie → odpowiedź z cytatami.

## Przygotowanie

1. **Odłącz maszynę od internetu fizycznie** — kabel, wyłączone Wi-Fi. Nie polegaj na regule firewalla; sprawdzamy system, a nie własne umiejętności konfiguracyjne.
2. Uruchom stos i poczekaj na ustabilizowanie (usługi przestają się restartować).
3. Przygotuj dokument z korpusu syntetycznego, **wcześniej nieprzetwarzany** — dokument już zindeksowany nie uruchomi całej ścieżki.

## Wykonanie

Ustal nazwy mostków:

```bash
docker network ls --filter name=kancelaria-lex --format "{{.Name}} {{.ID}}"
```

Uruchom przechwytywanie na każdym mostku (osobne terminale, `br-<ID>`):

```bash
sudo tcpdump -i br-<ID> -w /tmp/lex-net_app.pcap -n
```

Przeprowadź pełny cykl przez interfejs, po czym zatrzymaj przechwytywanie.

## Analiza

Odfiltruj ruch wewnątrzsegmentowy i sprawdź, czy zostało cokolwiek:

```bash
tcpdump -r /tmp/lex-net_app.pcap -n "not net 172.16.0.0/12 and not net 192.168.0.0/16 and not net 10.0.0.0/8"
```

Osobno — zapytania DNS na zewnątrz:

```bash
tcpdump -r /tmp/lex-net_parse.pcap -n "udp port 53"
```

## Ocena

| Wynik | Znaczenie |
|---|---|
| Zero pakietów na wszystkich mostkach | ✓ **Bramka zaliczona** |
| Ruch do adresów prywatnych | ✓ Ruch wewnętrzny — w porządku |
| **Jakikolwiek pakiet do adresu publicznego** | ✗ **Zatrzymaj wdrożenie.** Uruchom ścieżkę „podejrzenie połączenia wychodzącego" z [`../docs/10-operacje/runbook-incydent.md`](../docs/10-operacje/runbook-incydent.md) |
| **Zapytanie DNS o nazwę zewnętrzną** | ✗ Traktuj jak wyżej — samo zapytanie potwierdza, że coś próbowało się połączyć |

## Uwaga o wariancie z gotenbergiem

Wykonaj cykl **także na pliku zawierającym linkowany zasób zewnętrzny** (obraz z adresem URL, encja XML). To bezpośredni test zagrożenia I-2: LibreOffice potrafi próbować pobrać taki zasób, a pismo od strony przeciwnej z linkowanym obrazem stałoby się potwierdzeniem odbioru pod kontrolowanym adresem.

Plik testowy przygotuj sam — z adresem w domenie `.invalid`, żeby próba była jednoznacznie rozpoznawalna w przechwyceniu.

## Zapis

⚠️ **Pliki `.pcap` mogą zawierać treść dokumentów** — są wyłączone z repozytorium (`.gitignore`) i podlegają tym samym zasadom co akta.

Do dziennika (`infra/dziennik-zmian.md`) trafia: data, wersja systemu, wynik, nazwisko wykonującego. Sam plik przechwycenia przechowuj jak materiał objęty tajemnicą albo usuń po analizie.
