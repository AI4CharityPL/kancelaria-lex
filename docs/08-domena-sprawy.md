# 08 — Model domenowy: sprawy

> **Zastrzeżenie.** Ten dokument opisuje model danych i sposób działania systemu. Wszystkie reguły procesowe — zwłaszcza terminy — wymagają **zatwierdzenia przez prawnika kancelarii** przed wdrożeniem i przeglądu przy każdej nowelizacji przepisów. Autor tego dokumentu nie jest źródłem prawa; źródłem są ustawy i weryfikacja przez osobę odpowiedzialną zawodowo.

## Model danych

```
  Sprawa ──1:1── Corpus (zbiór dokumentów forka)
    │
    ├── Sygnatura      (wiele — sprawa wędruje między instancjami i organami)
    ├── Organ          (sąd / prokuratura / inny)
    ├── Strona         (rola procesowa, dane, pełnomocnik)
    ├── Etap           (postępowanie przygotowawcze, I instancja, odwoławcze…)
    ├── Termin         (procesowy — z podstawą i zdarzeniem inicjującym)
    ├── Rozprawa       (data, sala, obecność)
    ├── Prowadzący     (przypisanie imienne)
    └── KlauzulaPoufnosci (poziom + czy materiał obrończy)
```

### Sprawa

| Pole | Uwagi |
|---|---|
| `rodzaj` | karna / cywilna / gospodarcza / administracyjna / rodzinna |
| `tryb` | dla karnych: publicznoskargowy, prywatnoskargowy, przyspieszony |
| `stan` | aktywna / zawieszona / zakończona / archiwalna |
| `poziom_poufnosci` | standardowy / podwyższony / **materiał obrończy** |
| `data_wszczecia`, `data_zakonczenia` | |
| `prowadzacy` | imiennie, wymagane |

### Sygnatura

Sprawa ma zwykle **wiele sygnatur** — inną w prokuraturze, inną w sądzie I instancji, inną w odwoławczym. To częsty błąd modelowania: sygnatura nie jest atrybutem sprawy, tylko osobnym bytem powiązanym z organem i etapem.

Wzorce rozpoznawane (do zatwierdzenia i uzupełnienia przez prawnika):

| Wzorzec | Przykład | Kontekst |
|---|---|---|
| `<rzymska> K <nr>/<rok>` | `II K 123/26` | sąd rejonowy, sprawa karna |
| `<rzymska> Ka <nr>/<rok>` | `IV Ka 45/26` | sąd okręgowy, odwoławcza karna |
| `<rzymska> Kp <nr>/<rok>` | `III Kp 12/26` | postępowanie przygotowawcze — kontrola sądowa |
| `<rzymska> C <nr>/<rok>` | `I C 890/26` | cywilna |
| `Ds` / `PO ... Ds` | `PO I Ds 12.2026` | prokuratura |

Walidacja odbywa się **wzorcem, nie modelem** — sygnatura to dane strukturalne, a nie zadanie językowe. Model może wskazać kandydata w tekście; poprawność rozstrzyga wzorzec.

---

## Terminy procesowe

### Podział odpowiedzialności

```
  MODEL           rozpoznaje w piśmie zdarzenie inicjujące + cytat
     │            (zadanie językowe — model się do tego nadaje)
     ▼
  SILNIK REGUŁ    wylicza termin: podstawa, długość, sposób liczenia,
     │            dni ustawowo wolne
     │            (arytmetyka — kod, testowalny, audytowalny)
     ▼
  PRAWNIK         potwierdza. Bez potwierdzenia termin nie jest obowiązujący.
```

### Dlaczego tak

Przeoczony termin procesowy oznacza utratę środka zaskarżenia — szkodę dla klienta, zwykle nieodwracalną, oraz odpowiedzialność zawodową prawnika. Model probabilistyczny nie jest właściwym narzędziem do arytmetyki, której wynik ma taki skutek.

Podział wykorzystuje mocne strony obu: model czyta zdanie *„odpis wyroku z uzasadnieniem doręczono w dniu 12 sierpnia 2026 r."* i rozpoznaje zdarzenie. Kod liczy termin i sprawdza dni wolne. Prawnik potwierdza.

### Struktura reguły

Reguły są **danymi** (`src/aplikacje/sprawy/reguly_terminow.yaml`), nie kodem — prawnik ma je przejrzeć bez czytania Pythona.

```yaml
- id: apelacja_karna
  zdarzenie: doreczenie_wyroku_z_uzasadnieniem
  dlugosc_dni: 14
  liczenie: od_dnia_nastepnego
  dni_wolne: przesun_na_nastepny_roboczy
  podstawa: "art. 445 § 1 k.p.k."
  wymaga_potwierdzenia: true
  uwaga: "Zatwierdzone przez: ______  data: ______"
```

Każda reguła przed wdrożeniem wymaga wypełnienia pola zatwierdzenia. Reguła niezatwierdzona działa w trybie „tylko propozycja z ostrzeżeniem".

Katalog startowy obejmuje najczęstsze terminy karne i cywilne (m.in. zażalenie, apelacja, wniosek o uzasadnienie, sprzeciw od nakazu). **Katalog jest szkicem do weryfikacji, nie źródłem prawa** — pełna lista i brzmienie podstaw podlegają zatwierdzeniu przez prawnika w Fazie 5.

### Ostrzeganie

Terminy sygnalizowane wielokrotnie z wyprzedzeniem, na malejących odstępach. Ostrzeżenie o terminie niepotwierdzonym jest **głośniejsze** niż o potwierdzonym — nierozpoznany termin jest groźniejszy od znanego.

---

## Poufność w modelu domenowym

### Materiał obrończy — odrębny magazyn

Tajemnica obrończa (art. 178 pkt 1 k.p.k.) ma inny charakter niż tajemnica adwokacka. Tę drugą sąd może uchylić w trybie art. 180 § 2 k.p.k.; tej pierwszej — nie.

**Konsekwencja techniczna: materiał obrończy nie może być zwykłym rekordem z flagą.** Flagę można zmienić zapytaniem SQL. Materiał obrończy trafia do:

- odrębnego magazynu obiektów,
- szyfrowanego **osobnym kluczem**, niedostępnym dla procesu obsługującego pozostałe sprawy,
- za odrębną autoryzacją.

Skutek praktyczny: zrzut głównej bazy danych — z awarii, kopii zapasowej czy zajęcia sprzętu — **nie zawiera materiału obrończego w postaci czytelnej**.

### Ściany etyczne

Blokada dostępu przy konflikcie interesów, na poziomie warstwy uprawnień: rejestr powiązań między sprawami i osobami, kontrola przy nadaniu dostępu, ostrzeżenie przy przypisaniu prowadzącego, wpis audytowy przy każdym przełamaniu ściany (możliwym tylko decyzją administratora, z uzasadnieniem).

### Ślad audytowy

Log append-only z łańcuchem sum kontrolnych, poza bazą aplikacji. Rejestruje: kto, kiedy, który dokument lub sprawa, jaka operacja, z jakiego adresu.

Wymagana odpowiedź na pytanie „kto miał wgląd w akta sprawy X" — w sporze o zachowanie tajemnicy zawodowej to dowód należytej staranności. Log podatny na modyfikację nie jest dowodem.

---

## Retencja

Domyślnie 10 lat, konfigurowalnie. Napięcie do rozstrzygnięcia w [`09-compliance/rodo-rejestr-i-art32.md`](09-compliance/rodo-rejestr-i-art32.md): prawo do usunięcia danych (art. 17 RODO) versus obowiązek przechowywania akt i tajemnica zawodowa. W praktyce obowiązek przechowywania zwykle przeważa (art. 17 ust. 3 lit. b i e RODO), ale **każdy przypadek wymaga oceny** — system musi umieć wstrzymać usunięcie (legal hold), a nie tylko usuwać po terminie.
