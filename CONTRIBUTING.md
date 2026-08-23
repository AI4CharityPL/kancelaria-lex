# Contributing

Thank you for looking. A few things about this project are unusual, and knowing
them first will save you work.

**Two layers, two languages.** The application is Polish: the interface, the
code comments, the identifiers and the case material. The documentation is
English: `docs/`, this file, `README.md`, `QUICKSTART.md`, `SECURITY.md` and
`CHANGELOG.md`.

The split is deliberate rather than accidental. It is a product for Polish
advocates and legal counsel, so a Polish interface is the correct interface;
documentation nobody outside Poland can read, on the other hand, cannot be
evaluated by anyone outside Poland.

In practice that means: **code you touch stays Polish**, so a file does not end
up half and half, and **documentation you write stays English**. Names from the
application, such as `szukaj_w_sprawie` or `reguly_terminow.yaml`, appear in the
documentation exactly as they appear in the code, without translation.

**Issues and pull requests are welcome in either language.** If you write in
English, we will reply in English.

## Never put real case material in this repository

This is rule **T-6** ([`docs/compliance/legal-professional-privilege.md`](docs/compliance/legal-professional-privilege.md))
and it is the one rule with no exceptions, including "just this once, to
reproduce the bug".

It applies to **issues, pull requests, test fixtures and screenshots**, not only
to committed files. If a bug only reproduces on real material, reproduce it on
`eval/korpus-syntetyczny/` or on a public court ruling instead, and describe the
shape of the data rather than pasting it.

A CI gate checks every push for databases, corpora, weights and secrets. If it
fires on your branch, that is the gate working.

If you find real data already in the repository, **do not open an issue.**
Report it privately as described in [`SECURITY.md`](SECURITY.md), and treat it
as an incident rather than a bug.

## Before you open a pull request

```bash
python -m pytest tests/ -q --dozwol-pominiecie
```

Expected: `582 passed, 123 skipped, 1 warning`. The skips need Docker, the
OpenContracts fork or the measurement corpora; the warning is the deliberate
J-3 gap. Anything failing is a genuine failure.

**Without `--dozwol-pominiecie` you get 14 failures on a fresh clone, and they
are not bugs.** The isolation gates fail rather than skip when the fork or Docker
is missing, because a security gate that quietly passes when it could not run
reports a success it never verified. The flag is how you acknowledge they did not
run. On a machine holding real case files they have to actually pass rather than
be skipped.

The suite must run on **Python 3.11, 3.12 and 3.13**, and CI checks all three. This
matters more than it sounds: a syntax feature added in 3.12 once reached
`main` because everything was developed on 3.13 and nobody ran 3.11 locally.

## What gets a change accepted

**Measurement beats argument.** Several plausible, well-motivated improvements
have been reverted here because the numbers refused them, including one taken
straight from a published paper. If your change is meant to improve quality,
say what you measured and on what. "This should be better" is not enough, and we
will not hold it against you if the measurement disagrees; we will record it.

**A quality regression is a change and must be written down.** `CHANGELOG.md`
records degradation as well as improvement, on purpose, because degradation is
quiet, unlike a crash.

**Two properties are not negotiable**, because everything else rests on them:

1. Nothing leaves the device.
2. A citation cannot be fabricated: the model selects a sentence number, and
   the code reconstructs the text from the source.

A change that weakens either will be declined even if it improves the numbers.
If you think one of them should change, open an issue and argue it first; do not
start with code.

**No runtime dependencies.** The panel uses only the standard library, and that
is a supply-chain requirement recorded in [`pyproject.toml`](pyproject.toml), not
an oversight. Adding one needs a deliberate decision and an entry in
`docs/adr/`.

## Style

Match the file you are editing. The comment density here is higher than usual and
comments explain **why**, often including what was tried and rejected. That is
the house style rather than an accident. Keep it.
