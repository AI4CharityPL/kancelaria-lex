# Changelog

Format per [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Semantic versioning.

The rule here: **a fall in quality is a change and belongs in this file.** Degradation of the model, of retrieval or of OCR is quiet, unlike a crash (`docs/testing-and-gates.md`).

## [1.0.0], 17.08.2026: first public release

Published under MIT on the **AI4CharityPL** account, together with a request to support the fundraiser for the Wrocław animal shelter (TOZ, ratujemyzwierzaki.pl). The system could have been sold to law firms; instead it is free, and the request for payment is directed at the shelter.

### Added

- `README.md` in English, opening with the request to support the fundraiser and stating unambiguously that **the fundraiser is not ours** and that we receive nothing from it.
- `QUICKSTART.md`: installation step by step for someone who has never used a command line, with a "when something goes wrong" section and a list of the firm's obligations before real case files are loaded.
- `eval/README.md`: where to obtain the measurement corpora (SAOS, RECAP) and why they are not in the repository.
- **QUICKSTART step 0, hardware requirements.** Minimum and recommended figures (VRAM, RAM, disk, cores), the reference machine every published number was measured on, and a measurement of the GPU against CPU difference: **2.6 s against 33.7 s, that is 13.2 times slower** on the same model and question. What stood there before was one sentence about "8 GB of VRAM or patience", which is not enough for anyone to know, before downloading 9 GB, whether it will run on their machine.
- **QUICKSTART step 3, model versions pinned by digest.** Ollama tags are sometimes repointed at new builds, and without a digest there is no way to tell whether someone is measuring on the same weights. The full SHA-256 sums of both base models are given, with instructions for checking them and a plain statement: a different digest is not a defect, but the published results stop applying to that installation.
- **QUICKSTART step 10, verifying the installation with the test suite.** The expected `582 passed, 105 skipped, 1 warning`, with an explanation of each of the three numbers, including that the warning about the J-3 gap (82% against a target of 90%) is deliberate and appears on every run.
- Troubleshooting: distinguishing "the model did not fit on the card" from "the question covers the whole case" through the PROCESSOR column in `ollama ps`, and handling out-of-memory conditions when running on the processor.

### Fixed

- **The first public release did not contain the procedural deadline engine.** The `sprawy/` pattern in `.gitignore`, intended to block case data, had no leading slash, so it matched a directory of that name **at every level** and cut out `src/aplikacje/sprawy/`, that is `silnik_terminow.py` together with `reguly_terminow.yaml`. The README describes the deadline calculator as one of the main features, and it was not in the repository. The pattern is now anchored to the root (`/sprawy/`) and the files have been added.

  This was caught by the CI gate (`ModuleNotFoundError: No module named 'sprawy'`) rather than by the pre-publication check, because that check only looked at whether **anything forbidden had left** and never at whether **everything needed had arrived**. A one-directional check does not detect absences. A gate in the other direction has been added: "no code is excluded by `.gitignore`", checking `panel/`, `src/aplikacje/`, `eval/benchmark/`, `skrypty/` and `tests/` on every push.
- **The code did not compile on Python 3.11, despite declaring `>=3.11`.** `panel/wyszukiwarka.py:516` had a backslash inside an f-string expression, a construction permitted only from 3.12 (PEP 701). We work on 3.13 locally, so it was invisible until the CI gate went red on both of the first two pushes. On PyPI the consequence would have been worse than a red build: pip would have installed the package on 3.11 as declared, and the import would have failed for a stranger. The substitution moved into the module-level constant `_ODSTEPY`, which as a side effect compiles the pattern once rather than for each of tens of thousands of sentences.
- **A contradiction between the setup guide and the compliance documents.** QUICKSTART walked a lawyer step by step into installing the Q4_K_M profile on 8 GB of VRAM, while `docs/ai-stack.md`, `docs/compliance/gdpr-dpia.md` (point 106), `SECURITY.md` and an earlier entry in this changelog all describe that profile as **development-only and not approved for real case files**. The guide and the README now carry that information plainly, with a table of profiles and references to the sources. Resolved in favour of the compliance documents, because no measurement on Q8_0 exists that would justify departing from them.
- **GitHub did not recognise the licence and reported `NOASSERTION`.** The `LICENSE` file contained the MIT text plus a long appendix about weights licences, and licence detection matches **the whole file**. To every automated check the repository therefore looked unlicensed. `LICENSE` now contains the MIT text and nothing else; the appendix moved without substantive change into a new `NOTICE.md`.
- **The version in `pyproject.toml` diverged from the changelog**, showing 0.1.0 against the 1.0.0 announced here. Unified on 1.0.0.
- **`models/manifest.md` described a model the system does not use.** It listed Bielik-11B as "the language model", although that model was rejected in the ablation of 14.08.2026, while production runs on two models selected by document language: `bielik-lex-map` (minitron-7B) and `llama-lex-map` (Llama 3.1 8B). A manifest pointing at an unused model is worse than no manifest, because it leads directly to installing something other than what was measured. Digests, VRAM footprint and parameters added.
- **The Llama weights licence named plainly.** The manifest implied Apache 2.0 throughout; the Llama 3.1 Community License carries conditions Apache does not and is not a free licence. For a law firm it has no practical effect, but it has to be checked on every model change, exactly like the Surya case noted earlier.

### Added: package readiness and repository hygiene

- `NOTICE.md`: licences of third-party components, separating what the system actually runs from what is merely available.
- `CONTRIBUTING.md`: rule T-6 as it applies to issues and pull requests, the expected test result, the requirement to work on 3.11 to 3.13, and the two non-negotiable properties.
- `pyproject.toml`: classifiers, `[project.urls]`, and the licence in SPDX form (PEP 639, `setuptools>=77`).
- **A block on uploading to PyPI**, through the `Private :: Do Not Upload` classifier. The top-level module is called `panel`, and `panel` on PyPI is HoloViz Panel (version 1.9.3, sponsored among others by Anaconda and NumFOCUS). Uploading would break `import panel` in other people's environments, quietly and depending on `sys.path` order, and a version once uploaded to PyPI cannot be replaced. The block comes off together with the module rename; the names `kancelaria-lex` and `kancelaria_lex` are free on PyPI (checked 17.08.2026).

### Documentation moved to English

- **All 33 documents in `docs/` translated into English, with English file names.** The convention now reads: **the code and the interface are Polish, the documentation and repository files are English.** The reason is the same in both directions: it is a product for Polish lawyers, so translating the interface would make it worse, while documentation nobody outside Poland can read cannot be evaluated.
- Sequential numbering (`01-` to `23-`) dropped in favour of topical names, following the practice of comparable projects. Numbering stays only in `docs/adr/`, where it is the convention.
- Directories renamed: `adr/` to `adr/`, `compliance/` to `compliance/`, `operations/` to `operations/`, `obrazy/` to `images/`.
- `docs/README.md` added as an index, with the language rule stated at the top.
- **Identifier collision in the risk register resolved.** `RY-19` to `RY-23` each appeared twice, once among the technical risks and once among the substantive ones, so the same number meant two different things, and `RY-20` is cited from `weryfikator_cytatow.py`. The later technical additions moved to `RY-50` and above; the numbers cited from code keep their meaning.

### Removed

- `docs/00-wejscie/`: the private input report, prepared for a specific person and signed with their name. It carried nothing that is not in the rest of `docs/`, and publishing it would have revealed who commissioned this work. Added to `.gitignore` so it cannot return.

### Changed

- `LICENSE`: the rights holder is **AI4CharityPL**.
- The repository is published with **a new history**, because the previous one contained the deleted private report, and a file removed from the tree stays in history and remains recoverable.

## [Unreleased]

### Added

- The git repository, `pyproject.toml`, `LICENSE` and this changelog.
- `panel/__init__.py`: the panel is a package, so `kancelaria-lex` works from an editable install. `python panel/serwer.py` works as before.
- `panel/konfiguracja.py`: one source of truth about the model server configuration, read both by the startup script and by the gate.
- `skrypty/start.ps1`: sets the configuration, detects a server running on stale settings and restarts it, checks the models, and brings the panel up.
- `skrypty/przygotuj-modele.ps1`: builds the working models from `models/`. Until now that knowledge existed only in the author's head.
- `skrypty/bramki.ps1`: a run of the gates grouped as in `docs/testing-and-gates.md`; `-Zainstaluj` sets up a pre-commit hook. Deliberately local, without GitHub Actions: the private repository contains the threat model and the topology of an instance processing criminal case files, and should not leave the firm.
- `tests/test_konfiguracja_ollamy.py`: a gate checking both the persistent configuration and the state of the live server, together with a negative test reproducing the August regression.
- **A bilingual benchmark** (`eval/benchmark/`): a quantitative assessment of citation fidelity and refusal, with ground truth derived mechanically, without an LLM judge and without a lawyer's time. The method is matched pairs: every answerable case has a twin identical in form, differing only in the value of the anchor and verified as absent from the file. The headline measure, pair discriminability, gives zero to both degenerate behaviours, "always answer" and "always refuse". Reasoning and market context: `eval/benchmark/README.md`.
- **`panel/zdania.py`**: sentence splitting with offsets into the original, aware of legal abbreviations (`art.`, `§`, `k.p.k.`, `ust.`, `Dz.U.`). Without it "art. 445 § 1 k.p.k." breaks into four sentences. Shared by the benchmark and by citation by sentence number.

### Found by the benchmark *(defects in the system, not in the benchmark)*

- **The fast track had no retrieval, only a truncation at 6,000 characters.** `agent.py` gave the model the first 6,000 characters of each document. With a median of 21,000 characters per judgment that meant the header and the opening of the reasoning; everything beyond was invisible. Measured coverage: **28.2%** of the content of case 3 and **17.8%** of case 4. The refusals looked like caution on the model's part and in fact followed from never having been shown the document. The fast track now uses the same BM25 fragment selection as the analysis.
- **The fast track never received the lesson recorded at the mapping stage.** The template told the model to ANSWER the question and made refusal prominent. An ablation on three questions whose answers are present in the file:

  | template | model | statements | time |
  |---|---|---:|---:|
  | answering | bielik-lex-dev (11B) | **0** | 11.0 s |
  | answering | bielik-lex-map (7B) | 6 | 39.4 s |
  | extracting | bielik-lex-dev (11B) | **8** | 99.0 s |
  | extracting | bielik-lex-map (7B) | 6 | 35.1 s |

  Zero was reachable **only** in the starting configuration, which is exactly the one running in the panel. The template was changed to the extracting one and the model to `bielik-lex-map` (99 s exceeds target N-20).
- **`agent.py` looked for citations through `find()` rather than `znajdz_fragment()`.** The fast track was stricter than the analysis and lost correct citations from PDFs because of line breaks, the same cause that had earlier rejected 133 of 147 statements with the reason "range 0-0".
- **42.5% of the content of case 3 is HTML markup.** SAOS documents were uploaded together with `<p>`, `<div>`, `<td colspan="3">` and `<span class="anon-block">`. The panel indexes them as words of content, hands them to the model in place of the case file, and shows them in citations. Against a budget of 9,000 characters for mapping, that is around 3,800 characters of markup. The benchmark cleans them on load, but the right place to fix it is the document upload path.

### A note for anyone working on Windows

The `.ps1` scripts are saved in UTF-8 **with a BOM**. Windows PowerShell 5.1 reads files without a BOM as ANSI, which scrambles Polish characters and breaks the parser, so the script fails with a syntax error in an arbitrary place. Keep the BOM when editing them.

### Fixed

- **The model's answer was being truncated at the mapping stage (D-1).** The constant `KONTEKST_MAPOWANIA = 8192` was defined and never used, so `_mapuj_dokument` ran on the default `num_ctx = 4096`. With an input of `BUDZET_MAPOWANIA = 9000` characters (around 3,285 tokens) plus the template, that left around 400 tokens for an answer that really needs 600 to 900. The answer was cut off halfway. Every stage is now unified on 8192, which as a side effect removes the model reload between stages.
- **The Ollama server was running on settings from before the fix (D-2).** The log showed `8/8 seqs` and a `K (f16)` cache, that is 12.8 GB of KV with 9.2 GB of it on the CPU, exactly the state from before the fix described in `eval/wyniki/skala-2026-08-14.md`.

  The cause turned out to be different from how it looked at first glance: **the persistent configuration had been correct for some time.** The old values were sitting in the environment of *running processes*. The Ollama server had started before the fix and inherited them for its whole lifetime. The server reads the variables only at startup, so the fix never reached it.

  This is a failure mode worth remembering: checking the variables answers "everything is fine" while the system runs eighteen times slower. That is why the gate checks **two disjoint layers**, the persistent configuration (the Windows registry, not `os.environ`, which shows only what the test process inherited) and the state of the live server read from its log. `skrypty/start.ps1` restarts the server whenever it detects a divergence, whether or not it changed anything itself.

  After the fix: `1/1 seqs`, `K (q8_0)`, a cache of 680 MiB instead of 12,800 MiB, 41 of 41 layers on the GPU, and the model entirely on the card.
- **The `izolacja` marker was applied to no test.** It was declared in `pytest.ini` and described as "isolation gates (I-1 to I-9)", but not one test carried it. `pytest -m izolacja` collected zero tests and exited with code 5, so a run of "the isolation gates" checked nothing, while `-m "not izolacja"` excluded nothing, letting gates that need Docker into the fast unit run. The marker is now applied by directory (`tests/izolacja/conftest.py`), so a test added in future receives it automatically.
- **`--dozwol-pominiecie` could not be passed on the command line.** `pytest_addoption` sat in `tests/izolacja/conftest.py`, which pytest does not treat as an initial conftest, so the option registered only during collection, that is after the arguments had been parsed. It worked from code, but using it the way `docs/testing-and-gates.md` and the gate's own message instruct ended in "unrecognized arguments". An escape hatch that cannot be used is worse than none: under pressure someone reaches for `-k` or `--ignore` and disables more than they intended. Moved to `tests/conftest.py`.

## [0.1.0-poc], 14.08.2026

The starting point: a proof of concept with complete project documentation.

### Working

- The case panel (`panel/serwer.py`, port 8713): cases, documents, a chat whose memory is confined to a case, and a corpus of legal provisions.
- Deep map-reduce analysis: decomposition, document selection (BM25), mapping per document, provisions, synthesis, citation verification.
- The citation verifier: character-by-character comparison, with no LLM judge (ADR-0006).
- The deterministic deadline engine (ADR-0005): implemented and tested, **not wired into the panel**.
- Document language detection and model selection per language.
- An audit log with a chain of checksums.
- The OpenContracts fork with patches 01 to 03: 14,726 lines of MCP and discovery code removed.

### Measured

- 320 SAOS judgments (16.3 million characters) and 402 documents from the Lacey case (9.1 million characters), analysed in around 265 s and 283 s respectively.
- The number of model calls does not grow with the size of the file (BM25 selects 12).
- Raw citation accuracy: 82% on the Polish corpus, 9% on the English one before the model was matched to the language.
- Tests: 163 passing, 2 red (unpinned images, Docker switched off), 88 skipped.

### Known limitations

- No accounts or profiles; the panel listens on 127.0.0.1 only.
- The audit log does not record the person (requirement F-33 unmet).
- No file upload and no OCR; content is pasted as text.
- The Q4 profile on 8 GB of VRAM is **not approved for real case files** (`docs/ai-stack.md`, DPIA condition 2).
