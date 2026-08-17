# ADR-0006 — Maszynowa weryfikacja cytatów zamiast sędziego LLM

**Status:** przyjęta · **Data:** 14.08.2026

## Kontekst

Model językowy w analizie akt karnych może wygenerować twierdzenie brzmiące wiarygodnie, ale nieznajdujące pokrycia w dokumentach. W kancelarii skutkiem jest błędna ocena sprawy — a przy obronie karnej szkoda bywa nieodwracalna.

Ryzyko jest podwyższone w profilu rozwojowym: karta modelu Bielika wprost ostrzega, że **kwantyzacja obniża jakość i zwiększa skłonność do halucynacji**, a 8 GB VRAM wymusza Q4.

## Rozważane opcje

| Opcja | Ocena |
|---|---|
| **A. Maszynowa weryfikacja spanów** ✅ | Deterministyczna, tania, wykrywa zmyślony cytat z pewnością |
| B. Sędzia LLM oceniający wierność | Podatny na te same błędy co model oceniany; **przepuszcza halucynacje**, zwłaszcza przy pewnie brzmiących odpowiedziach |
| C. Sama weryfikacja ludzka | Rzetelna, ale nie skaluje się i nie działa jako bramka automatyczna |
| D. Bez weryfikacji | Nieakceptowalne w tym zastosowaniu |

## Decyzja

**Opcja A jako bramka automatyczna, opcja C jako obowiązkowy krok pracy.**

Każde twierdzenie w odpowiedzi niesie identyfikator dokumentu i zakres znaków. Kod pobiera ten zakres ze źródła i porównuje tekst **znak po znaku**. Twierdzenia bez pokrycia są odrzucane, zanim prawnik je zobaczy. Odrzucone twierdzenia trafiają do logu jako miara jakości modelu w czasie.

Sędzia LLM został **świadomie odrzucony**. Model oceniający wierność odpowiedzi dzieli słabości z modelem ocenianym i bywa pobłażliwy dokładnie tam, gdzie ryzyko jest największe — przy odpowiedzi sformułowanej pewnie. Porównanie ciągów znaków nie ma tej wady: fragment albo istnieje i się zgadza, albo nie.

## Granica tej metody — wprost

**Weryfikacja potwierdza, że cytat pochodzi ze źródła. Nie potwierdza, że wniosek wyciągnięty z cytatu jest trafny.**

Model może poprawnie zacytować protokół i błędnie zinterpretować jego znaczenie. Żadna metoda maszynowa tego nie wyłapie.

Dlatego:
- cel projektu brzmi „odpowiedzi weryfikowalne", nie „odpowiedzi pewne" (C3),
- weryfikacja przez prawnika pozostaje **obowiązkowa**, nie zalecana,
- ryzyko R-4 w DPIA pozostaje na poziomie średnim — świadomie i jawnie,
- interfejs musi komunikować status narzędzia roboczego, nie tylko regulamin.

## Konsekwencje

**Pozytywne:** zmyślony cytat nie przechodzi · bramka J-1 na poziomie 99% jest osiągalna, bo mierzy własność binarną · odrzucenia są mierzalnym wskaźnikiem jakości modelu · brak zależności od drugiego modelu.

**Negatywne:** model musi zwracać ustrukturyzowane cytaty, co ogranicza swobodę formatu · przy 8k kontekstu retrieval musi być oszczędny · metoda nie chroni przed błędną interpretacją.

## Powiązania

Realizacja: `src/aplikacje/agenci/weryfikator_cytatow.py` · Bramka: J-1 w [`../11-testy-i-bramki.md`](../11-testy-i-bramki.md) · Ryzyko: R-4 w [`../09-compliance/rodo-dpia.md`](../09-compliance/rodo-dpia.md)
