# Before anything else: please help an animal shelter in Wrocław 🐕

**This software is free. If it saves you time or money, please consider giving
that value to animals in Polish shelter.**

### 👉 [ratujemyzwierzaki.pl/schroniskowroclaw](https://www.ratujemyzwierzaki.pl/schroniskowroclaw)

**TOZ Schronisko dla Bezdomnych Zwierząt we Wrocławiu** - the *TOZ Shelter for
Homeless Animals in Wrocław* - has been rescuing animals **since 1962**. Situated
at 2 Ślazowa Street in Wrocław-Osobowice, run by **just over 30 employees**, some
of whom are also inspectors for the Polish Society for the Prevention of Cruelty
to Animals. They currently care for roughly **170 dogs and 140 cats**, plus
rabbits, parrots, snakes and eleven Vietnamese pigs.

> *"Together with the Volunteers who support us, we strive for one thing - to
> help those who cannot ask for it themselves."*

> **The donation page is in Polish only** - but it's possible to translate it using the internet browser. In Chrome,
> right-click anywhere on the page and choose **Translate to English** (Edge,
> Firefox and Safari all have the same feature). The payment method works in the same way,
> regardless of language.

> ### ⚠️ This is not our fundraiser.
>
> We are **not affiliated** with the shelter. We do **not** collect, handle or
> receive any of this money, and we get **nothing** if you donate. We are simply
> pointing at someone else's fundraiser because we think it deserves your
> attention more than we deserve your payment.
>
> Every złoty goes directly to the shelter through **ratujemyzwierzaki.pl**,
> a Polish donation platform. Verify it yourself before donating.

### Why we are asking now

**Winter is coming, and it's the hardest season that the shelter faces.** Cold weather
drives up every cost at once: heating itself can run into thousands of złoty per
month, animals need higher-calorie food just to keep their body temperature up,
and vets see a spike in frostbite and respiratory infections among the older
and sicker animals - the ones nobody adopts first. Winter is also a time when
shelters see an influx of animals given up as unwanted Christmas gifts.

These aren't abstract problems - they're real bills for heating, food, and vet care. 
That's what your donation goes toward.

You can give **10, 20, 50 or 100 zł once**, or **20–50 zł monthly**. You can also
"virtually adopt" a specific animal. 

### Why we are giving this away

This system took real work: measured, tested, documented. It could have been sold
to law firms, because that market pays well and there is no good local-only
competitor in Polish.

We would rather it be free and have the shelter get the money instead.

If you are a law firm and this replaces a paid tool, please donate roughly what
you would have paid. If you are a student, a solo practitioner, or just curious,
use it, donate nothing, and enjoy it. **No one is checking. There is no licence
key.** The request above is a request, never a condition.

---

# kancelaria-lex

[![testy](https://github.com/AI4CharityPL/kancelaria-lex/actions/workflows/testy.yml/badge.svg)](https://github.com/AI4CharityPL/kancelaria-lex/actions/workflows/testy.yml)
[![licencja MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)
[![bez zależności](https://img.shields.io/badge/runtime%20dependencies-none-brightgreen.svg)](pyproject.toml)

**A fully local AI system for analysing legal case files, built for Polish
lawyers, in Polish, for Polish legal reality.**

> **Language.** Two layers, two languages, and the split is deliberate.
>
> | Layer | Language |
> |---|---|
> | Documentation, README, repository files | **English**, so anyone can evaluate the project |
> | The application: interface, case material, code comments, identifiers | **Polish** |
>
> The application stays Polish because it is a product for Polish advocates and
> legal counsel, working on Polish case files under Polish procedure: the codes
> of criminal and civil procedure, procedural deadlines, court reference numbers,
> professional privilege. Translating the interface would make it worse rather
> than more useful. That is why names such as `panel/wyszukiwarka.py`,
> `reguly_terminow.yaml` and `szukaj_w_sprawie` appear in the documentation
> exactly as they appear in the code.

## What it does

You load the case file. You ask a question in plain Polish. You get an answer
where **every single sentence points to the exact place in the document it came
from, down to the character.**

Click a citation and the source opens with that passage highlighted. Not a page
number. Not a paraphrase. The actual sentence.

### Loading files, and being honest about scans

PDF, DOCX, TXT and RTF, dragged in or picked, many at once, with no Python
dependencies added for any of it. Measured on **173 real-world PDFs**
(contracts, invoices, offers, technical documentation, signed letters):
**87 read from the text layer, 16 through OCR, 70 refused with an explanation.**

Refusal is a correct outcome here. Extracted text becomes the **source of
citations**, and the verifier compares citations against it character by
character, so a bad extraction would break the whole guarantee silently:
the citation would verify against corrupted text.

**OCR is available, local, and never silent about itself.** Tesseract with the
Polish language pack, run as a separate process. It is switched on by a click,
never automatically, because it changes what the core promise means:

> *a citation points to an exact character in the case file* becomes
> *a citation points to an exact character **in the reading of a scan***

That reading is wrong most often in signatures, amounts and dates, and in our
measurement a handwritten date came out as `4 9.03.2026`. So a document read
this way carries a **permanent marker**, every citation from it shows `z OCR`
and a *check against the original* warning, and text provenance is tracked for
every route in: pasted, from a file, or through OCR.

Full numbers and limits: [`docs/document-loading-and-ocr.md`](docs/document-loading-and-ocr.md)

## What makes it different

**The model never writes a quotation.** It selects a *sentence number*, and the
code reconstructs the text from the source document. A fabricated citation is not
"detected and rejected"; it is **impossible to express**.

Measured on real-scale case files (722 documents, one Polish and one English
case, 100 matched questions):

| | |
|---|---|
| Citations inconsistent with the source | **0**, in every measurement run, without exception |
| For comparison: leading commercial legal AI tools (Stanford study) | **17–34% fabricated citations** |
| Citation accuracy | **above 80%** |
| Correctly refusing when the files give no answer | **above 80%** |
| Data sent anywhere | **0 bytes** |

Every answerable question has an identically-worded twin that the files
**cannot** answer, so "always answer" and "always refuse" both score zero.

**We also publish the numbers that look bad.** See
[`docs/measured-results.md`](docs/measured-results.md), including where the
system still falls short of its own targets, and four hypotheses we tested and
had to throw away.

> ### Which profile these numbers belong to
>
> They were measured on the **development profile**, Q4_K_M quantisation on 8 GB
> of VRAM, which is what [QUICKSTART](QUICKSTART.md) installs and what most
> people will run. **This project's own compliance documents do not approve that
> profile for real case files**; they require Q8_0 or higher, which needs 24 GB.
>
> We are stating this in the same breath as the numbers rather than further down,
> because a figure quoted without its profile is the kind of half-truth this
> whole project exists to avoid. Details:
> [before you load real case files](QUICKSTART.md#before-you-load-real-case-files).

## Fully local, enforced rather than promised

Nothing leaves the machine. Not case text, not fragments, not queries, not
metadata, not usage statistics.

Three independent layers enforce this:

| Layer | Mechanism |
|---|---|
| **Code** | No cloud SDKs. The model address is validated at import, and **a non-loopback address stops the process from starting.** A test scans the codebase so nobody can quietly add a second network call. |
| **Network** | Four Docker segments, three with `internal: true`, so there is no route to the gateway. |
| **Proof** | Traffic captured at packet level while a container inside each segment actively tried to reach the internet: **zero packets left.** |

It runs with the network cable unplugged. That is the simplest demonstration you
can give a client or an auditor.

## What it deliberately does **not** do

- It does **not** give legal advice or assess your case.
- It does **not** predict outcomes or assess the credibility of witnesses.
- It does **not** classify conduct legally.
- It does **not** replace reading the file.

It extracts facts and shows you where they are. **The lawyer decides.** This
boundary is built into the output schema, not just written in a disclaimer.

## Also included

Local profiles with password login and optional two-factor (TOTP), named
conversation threads you can close and reopen, verified backups with restore,
export to Markdown/HTML, a deterministic **procedural deadline calculator**
(computed by code, never by the model), an append-only **audit log with a hash
chain**, and a quality journal that never stores case content.

## Getting started

**[QUICKSTART.md](QUICKSTART.md)** is written for someone who has never used a
command line. About 30 minutes, most of it waiting for model downloads.

**Check the hardware first.** [Step 0](QUICKSTART.md#step-0-will-it-run-on-your-computer)
tells you whether this machine can run it *before* you download 9 GB:

| | Minimum | Recommended |
|---|---|---|
| Graphics memory (VRAM) | 6 GB free | 8 GB |
| RAM | 16 GB | 32 GB |
| Free disk | 15 GB | 25 GB |

It runs without a graphics card, but we measured it at **13 times slower**, usable
for trying it out, painful for daily work. Apple Silicon shares memory, so a
16 GB Mac takes the fast path.

The setup guide **pins the exact model versions by digest**. Two models with the
same name are not the same model, and the accuracy figures below belong to
specific weights, and [Step 3](QUICKSTART.md#step-3-download-the-two-language-models)
tells you how to confirm you have them.

Windows, macOS or Linux. No internet connection needed after setup.

## Documentation

Complete, in English, with an index in [`docs/README.md`](docs/README.md). The
places to start:

| | |
|---|---|
| [`context-and-goals.md`](docs/context-and-goals.md) | Why this exists and for whom |
| [`isolation-and-network.md`](docs/isolation-and-network.md) | **The core**: three layers of isolation |
| [`compliance/`](docs/compliance/) | GDPR/DPIA, KSC (NIS2), AI Act, professional secrecy |
| [`measured-results.md`](docs/measured-results.md) | Measurements, including the unflattering ones |
| [`risk-register.md`](docs/risk-register.md) | Open risks, honestly listed |
| [`adr/`](docs/adr/) | Seven architecture decisions, with what was rejected and why |

Benchmark corpora are **not** in this repository; see
[`eval/README.md`](eval/README.md) for how to obtain them. They are public
sources; they are simply large, and this project's first rule is that real case
files never enter a repository.

## Official source

The only current version lives at
**[github.com/AI4CharityPL/kancelaria-lex](https://github.com/AI4CharityPL/kancelaria-lex)**.

A copy received any other way, by email, on a drive or from an intermediary, is
not official, and you cannot know what was changed in it.

## Licence and liability

MIT; see [LICENSE](LICENSE). Use it, sell services around it, fork it.

Provided **as is**, without warranty. The authors are not liable for:

- **misuse**, in particular relying on an answer without opening the citation;
- **modified versions** or copies from outside the official source. Changing the
  code can remove exactly the safeguards this whole argument rests on: network
  isolation and citation verification;
- **the firm's own legal obligations**: KSC assessment and registration, DPIA
  approval, disk encryption, staff training.

**Professional responsibility for any document you sign remains entirely yours.**


*Built in Poland. Given away for the dogs and cats in Wrocław.*
