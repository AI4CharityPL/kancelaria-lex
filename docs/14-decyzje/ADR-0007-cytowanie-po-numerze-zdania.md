# ADR-0007 — Cytowanie po numerze zdania z gramatyką dekodowania

**Status:** przyjęty · 14.08.2026
**Zastępuje częściowo:** mechanizm cytowania z [ADR-0006](ADR-0006-weryfikacja-cytatow.md) (weryfikacja zostaje, zmienia się to, co weryfikuje)

## Kontekst

ADR-0006 rozstrzygnął, że cytaty sprawdzamy maszynowo, a nie sędzią LLM.
Mechanizm działał: model podawał treść cytatu, kod szukał jej w źródle,
niedopasowane twierdzenia przepadały.

Pomiar benchmarkiem ujawnił jednak, ile ten mechanizm kosztuje. Na
korpusie polskim **19% twierdzeń** odpadało, na angielskim **26%**,
i **wszystkie** z tego samego powodu: `odrzucony_zakres_poza_tekstem`
z zakresem 0-0, czyli fragmentu w ogóle nie znaleziono. Ani jednego
przypadku „zakres wskazany, treść inna".

To nie była wada weryfikatora. To był model, który **parafrazował
zamiast przepisywać**. Dosłowne odtworzenie dwudziestowyrazowego zdania
z polskiego pisma procesowego jest zadaniem kopiującym, na którym mały
model skwantyzowany zawodzi stochastycznie. Prawnik tracił co piąte
prawdziwe ustalenie, bo model przestawił przecinek.

Podnoszenie tego progu prośbą w szablonie nie działa — próbowano.

## Decyzja

**Model wskazuje NUMER zdania. Treść cytatu odtwarza kod.**

Kod dzieli dokument na zdania (z zachowaniem offsetów w oryginale),
numeruje je i pokazuje modelowi. Model zwraca numery. Kod bierze
`zrodlo[poczatek:koniec]` i to jest cytat.

Do tego **schemat JSON wymuszany przy dekodowaniu**: pole z numerami ma
`enum` zbudowany z numerów faktycznie pokazanych zdań. Ollama kompiluje
schemat do gramatyki i zeruje prawdopodobieństwo tokenów, które by ją
złamały.

```
  było:  model → tekst cytatu → kod szuka → weryfikacja → często pudło
  jest:  kod → ponumerowane zdania → model → numer → kod odtwarza cytat
```

**Zmyślenie cytatu przestaje być wykrywalne — staje się niewyrażalne.**

## Granice tej gwarancji

⚠️ **Ta sekcja jest ważniejsza od poprzedniej.**

**1. Gramatyka gwarantuje formę, nie trafność.** Dokumentacja Ollamy mówi
to wprost o polach `enum`: wartość jest zawsze dopuszczalna, ale
niekoniecznie właściwa, gdy model jest niepewny. Sprawdzone
doświadczalnie: przy schemacie dopuszczającym wyłącznie `enum: [7]`
i dokumencie o pięciu zdaniach model zwrócił `[7, 7]` — numer
nieistniejący, bo tylko taki był dozwolony.

**Wniosek operacyjny:** enum musi pochodzić z `WyborZdan.numery` tego
samego wywołania. Schemat rozminięty z wsadem zamienia się
z zabezpieczenia w wymuszacz błędu.

**2. Klasa błędu się zmienia, nie znika.** Z „model zmyślił cytat" na
„model wskazał niewłaściwe zdanie". Ta druga jest jednak dla prawnika
wykrywalna w kilka sekund, bo cytat prowadzi do prawdziwego miejsca
w aktach — a nie w próżnię.

**3. Pojawiła się degeneracja odwrotna.** Dopóki model musiał przepisać
cytat, wskazanie czegokolwiek kosztowało wysiłek i przy braku odpowiedzi
zwracał pustą listę. **Wskazanie numeru jest darmowe, więc model zaczął
wskazywać zawsze** — także przy pytaniu o rzecz, której w aktach nie ma.

Zmierzone bezpośrednio po wdrożeniu: wierność cytatu 100%, zdolność do
odmowy runęła. Zamiana degeneracji „zawsze odmawiaj" na „zawsze
odpowiadaj" nie jest postępem.

Dlatego dołożono **mechaniczne zakotwiczenie w pytaniu**: gdy pytanie
niesie wyróżnik złożony — pełną datę, kwotę, sygnaturę — przynajmniej
jeden musi wystąpić w zacytowanym materiale. Wyróżnik liczy się jako
całość: zgodność samego roku nie wystarcza, bo rok 2023 stoi w aktach
na każdej stronie. Pytania bez wyróżnika przechodzą bez zmian.

To jest ta sama zasada, dla której `wyszukiwarka.rdzen` zostawia liczby
nietknięte, a ADR-0005 oddaje terminy silnikowi reguł: **tam, gdzie
wystarczy reguła, model jest gorszym narzędziem.**

**4. Weryfikacja z ADR-0006 zostaje w mocy.** Nie jest zastąpiona.
Ścieżka zapasowa, w której model mimo schematu poda tekst cytatu,
przechodzi starą drogą przez `znajdz_fragment`.

## Konsekwencje

**Wymagane:** podział na zdania musi znać skróty prawnicze — bez tego
„art. 445 § 1 k.p.k." rozpada się na cztery zdania i numeracja przestaje
cokolwiek znaczyć (`panel/zdania.py`, `tests/test_zdania.py`).

**Wymagane:** jednostką retrievalu staje się zdanie, nie okno znakowe.
Okno cięte w środku zdania dawało numery wskazujące urwane ciągi
(„[1] za w przypadku wnioskowania orzeczenia...").

**Wymagane:** filtr jakości zdań musi działać w panelu, nie tylko
w benchmarku. Kod bierze wskazaną pozycję dosłownie, więc `n/d`
albo fragment tabeli trafiłby do prawnika jako cytat z akt.

**Zysk uboczny:** znika cała klasa usterek parsowania. Model nie zwraca
już tekstu, który trzeba dopasowywać, więc normalizacja nazw kluczy
i wariantów pisowni przestaje być pierwszą linią obrony.

**Koszt:** wsad rośnie o numerację — zmierzone od −1,5% do +3,6%,
czyli w granicach szumu.

## Alternatywy odrzucone

| Wariant | Powód odrzucenia |
|---|---|
| Ostrzejszy szablon („cytuj DOSŁOWNIE") | Próbowano. Nie podnosi progu — to zadanie kopiujące, nie kwestia chęci. |
| Dopasowanie rozmyte cytatu do zdania | Przepuszcza parafrazy, czyli dokładnie to, co ma odrzucać. Zmienia próg, nie naturę problemu. |
| Większy model | 11B daje 8 ustaleń zamiast 6, ale 99 s zamiast 35 s — poza celem N-20. I nie usuwa parafrazy, tylko ją przerzedza. |
| Sędzia LLM oceniający wierność | Odrzucone w ADR-0006 i potwierdzone niezależnie: *„LLM-as-a-Judge is Bad"*, Artificial Intelligence and Law (Springer 2026), na materiale egzaminu na członka KIO. |
