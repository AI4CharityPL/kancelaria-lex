# ADR-0007. Citation by sentence number with a decoding grammar

**Status:** accepted, 14.08.2026.
**Partly supersedes:** the citation mechanism from [ADR-0006](0006-mechanical-citation-verification.md). Verification stays; what changes is what it verifies.

## Context

ADR-0006 settled that citations are checked mechanically rather than by an LLM judge. The mechanism worked: the model supplied the text of the citation, the code looked for it in the source, and unmatched statements were dropped.

Benchmarking then revealed what that mechanism costs. On the Polish corpus **19% of statements** were discarded, on the English corpus **26%**, all for the same reason: `odrzucony_zakres_poza_tekstem` with range 0-0, meaning the fragment was not found at all. Not a single case of "range indicated, text different".

The cause was not the verifier but the model, which **paraphrased instead of transcribing**. Reproducing a twenty-word sentence from a Polish procedural document verbatim is a copying task, and a small quantised model fails at it stochastically. The lawyer was losing every fifth genuine finding because the model moved a comma.

Raising that bar by asking nicely in the prompt does not work. We tried.

## Decision

**The model indicates a sentence number. The code reconstructs the citation text.**

The code splits the document into sentences (preserving offsets into the original), numbers them and shows them to the model. The model returns numbers. The code takes `zrodlo[poczatek:koniec]` and that is the citation.

On top of that, **the JSON schema is enforced during decoding**: the field holding the numbers has an `enum` built from the numbers of the sentences actually shown. Ollama compiles the schema into a grammar and zeroes the probability of tokens that would break it.

```
  before:  model -> citation text -> code searches -> verification -> frequent miss
  after:   code -> numbered sentences -> model -> number -> code reconstructs citation
```

**Fabricating a citation stops being detectable and becomes inexpressible.**

## The limits of that guarantee

**This section matters more than the previous one.**

**1. The grammar guarantees form, not accuracy.** The Ollama documentation says so plainly about `enum` fields: the value is always permissible, but not necessarily correct when the model is uncertain. Confirmed experimentally: with a schema permitting only `enum: [7]` and a document of five sentences, the model returned `[7, 7]`, a number that does not exist, because it was the only one allowed.

**Operational conclusion:** the enum must come from `WyborZdan.numery` of the same call. A schema out of step with the input turns from a safeguard into an error generator.

**2. The class of error changes but does not disappear.** It moves from "the model fabricated a citation" to "the model pointed at the wrong sentence". The second, however, takes a lawyer seconds to spot, because the citation leads to a real place in the file.

**3. An inverse degeneration appeared.** As long as the model had to transcribe the citation, pointing at anything cost effort, and when there was no answer it returned an empty list. **Pointing at a number is free, so the model started pointing every time**, including at questions whose answer is not in the file.

Measured immediately after the change: citation fidelity 100%, ability to refuse collapsed. Trading the "always refuse" degeneration for "always answer" is not progress.

Hence the addition of **mechanical anchoring in the question**: when a question carries a compound discriminator, that is a full date, an amount or a case reference number, at least one of them must appear in the quoted material. The discriminator counts as a whole: matching the year alone is not enough, because the year 2023 appears on every page of the file. Questions without a discriminator pass unchanged.

The same principle is at work here as the one that makes `wyszukiwarka.rdzen` leave figures untouched and ADR-0005 hand deadlines to a rule engine: **where a rule suffices, the model is the worse tool.**

**4. Verification from ADR-0006 remains in force.** It is not replaced. The fallback path, where the model supplies citation text despite the schema, still goes the old way through `znajdz_fragment`.

## Consequences

**Required:** sentence splitting has to know legal abbreviations. Without that, "art. 445 § 1 k.p.k." breaks into four sentences and the numbering stops meaning anything (`panel/zdania.py`, `tests/test_zdania.py`).

**Required:** the unit of retrieval becomes the sentence rather than a character window. A window cut mid-sentence produced numbers pointing at truncated strings.

**Required:** the sentence quality filter has to run in the panel, not only in the benchmark. The code takes the indicated position literally, so `n/d` or a fragment of a table would reach the lawyer as a quotation from the case file.

**Side benefit:** an entire class of parsing defects disappears. The model no longer returns text that has to be matched, so normalising key names and spelling variants stops being the first line of defence.

**Cost:** the input grows by the numbering, measured at between −1.5% and +3.6%, which is within noise.

## Alternatives rejected

| Variant | Reason for rejection |
|---|---|
| A stricter prompt ("quote VERBATIM") | Tried. It does not raise the bar, because this is a copying task rather than a matter of willingness. |
| Fuzzy matching of the citation to a sentence | Lets paraphrase through, which is exactly what it is meant to reject. It shifts the threshold without touching the nature of the problem. |
| A larger model | 11B gives 8 findings instead of 6, but 99 s instead of 35 s, which is outside target N-20. It thins paraphrase out rather than removing it. |
| An LLM judge rating faithfulness | Rejected in ADR-0006 and confirmed independently: *"LLM-as-a-Judge is Bad"*, Artificial Intelligence and Law (Springer 2026), on material from the Polish public procurement board examination. |
