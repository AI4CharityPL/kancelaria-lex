# Third-party components and their licences

> **Why this is a separate file.** It used to live at the bottom of `LICENSE`.
> GitHub and PyPI detect a licence by matching the whole file against known
> texts, so the appendix made both report `NOASSERTION` instead of `MIT` —
> the repository looked unlicensed to every automated check. `LICENSE` is now
> the plain MIT text and nothing else. The content below did not change;
> it moved. Corrected 17.08.2026.

## ⚠️ The code licence is not the model licence

The MIT licence in [`LICENSE`](LICENSE) covers **only the code in this
repository**. It says nothing about the language models, the embedder or the
OCR engines the system works with. **Each of those has its own licence and its
own restrictions.**

The case that makes this concrete: **Surya** — Apache 2.0 code, but weights
under AI Pubs Open-RAIL-M, which restricts commercial use above a revenue
threshold. For a commercial law firm that would require a separate licence.
**A repository's licence is not enough to judge by.**

**Every model update requires re-verifying the licence of the weights.**

Register of licences, versions and checksums: [`models/manifest.md`](models/manifest.md).
Procedure for introducing a model: [`docs/10-operacje/runbook-aktualizacje.md`](docs/10-operacje/runbook-aktualizacje.md).

## Components, as verified on 17.08.2026

### In production — what the system actually runs

| Component | Role | Licence |
|---|---|---|
| **Bielik-minitron-7B-v3.0-Instruct** (weights) | Polish documents — `bielik-lex-map` | Apache 2.0 |
| **Llama 3.1 8B Instruct** (weights) | English documents — `llama-lex-map` | **Llama 3.1 Community License** |
| **multilingual-e5-base** (weights) | embedder, 768 dimensions | MIT |

> ⚠️ **Llama 3.1 is not a fully open licence.** The Llama 3.1 Community License
> imposes conditions that Apache 2.0 does not — among them a 700 million monthly
> active user threshold and a requirement to state "Built with Llama". For a law
> firm this has no practical effect, but it is **not** Apache 2.0 and must be
> treated as its own licence in any review.

### Available but not in production

| Component | Status | Licence |
|---|---|---|
| **Bielik-11B-v3.0-Instruct** (weights) | rejected in the 14.08.2026 ablation; `Modelfile.bielik-dev` kept only to reproduce it | Apache 2.0 |
| **OpenContracts** | base code of the fork; cloned, not vendored here | MIT |
| **Tesseract 5.x + `pol.traineddata`** | OCR, default choice — **not currently wired in** | Apache 2.0 |
| **RapidOCR** | OCR, fallback for poor photocopies | Apache 2.0 |
| ~~**Surya**~~ | **to be avoided** — commercial threshold in the weights licence | code Apache 2.0 / weights Open-RAIL-M |

### Python dependencies

**None at runtime.** The panel uses only the Python standard library — this is a
requirement, recorded in [`pyproject.toml`](pyproject.toml), not an accident.
Every package in the supply chain is a package somebody has to watch
(art. 21(2)(d) of the Polish KSC act). BM25, tokenisation and language detection
are written from scratch for that reason.

The only development dependency is `pytest`.

## Attribution when you redistribute

MIT requires you to carry the copyright notice and the permission text. If you
also redistribute the models, **their licences travel with them**, and the Llama
notice requirement applies to you rather than to us.
