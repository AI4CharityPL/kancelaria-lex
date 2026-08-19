# Contributing

Thank you for looking. A few things about this project are unusual, and knowing
them first will save you work.

**Polish is the working language of the code.** Comments, identifiers, commit
messages and everything in `docs/` are Polish, deliberately —
[the README explains why](README.md#what-it-does). `README.md` and `QUICKSTART.md`
are English so the project can be evaluated from outside. **Issues and pull
requests are welcome in either language.** If you write English, we will reply in
English; the code you touch should stay in Polish so the file does not end up
half and half.

## ⚠️ Never put real case material in this repository

This is rule **T-6** ([`docs/09-compliance/tajemnica-zawodowa.md`](docs/09-compliance/tajemnica-zawodowa.md))
and it is the one rule with no exceptions — including "just this once, to
reproduce the bug".

It applies to **issues, pull requests, test fixtures and screenshots**, not only
to committed files. If a bug only reproduces on real material, reproduce it on
`eval/korpus-syntetyczny/` or on a public court ruling instead, and describe the
shape of the data rather than pasting it.

A CI gate checks every push for databases, corpora, weights and secrets. If it
fires on your branch, that is the gate working.

If you find real data already in the repository, **do not open an issue** —
report it privately as described in [`SECURITY.md`](SECURITY.md), and treat it
as an incident rather than a bug.

## Before you open a pull request

```bash
python -m pytest tests/ -q --dozwol-pominiecie
```

Expected: `569 passed, 121 skipped, 1 warning`. The skips need Docker, the
OpenContracts fork or the measurement corpora; the warning is the deliberate
J-3 gap. Anything failing is a genuine failure.

⚠️ **Without `--dozwol-pominiecie` you get 14 failures on a fresh clone, and
they are not bugs.** The isolation gates fail rather than skip when the fork or
Docker is missing — a security gate that quietly passes when it could not run
reports success it never verified. The flag is how you acknowledge they did not
run. On a machine holding real case files they must actually pass, not be
skipped.

The suite must run on **Python 3.11, 3.12 and 3.13** — CI checks all three. This
matters more than it sounds: a syntax feature added in 3.12 once shipped to
`main` because everything was developed on 3.13 and nobody ran 3.11 locally.

## What gets a change accepted

**Measurement beats argument.** Several plausible, well-motivated improvements
have been reverted here because the numbers refused them — including one taken
straight from a published paper. If your change is meant to improve quality,
say what you measured and on what. "This should be better" is not enough, and we
will not hold it against you if the measurement disagrees; we will record it.

**A quality regression is a change and must be written down.** `CHANGELOG.md`
records degradation as well as improvement, on purpose — degradation is quiet,
unlike a crash.

**Two properties are not negotiable**, because everything else rests on them:

1. Nothing leaves the device.
2. A citation cannot be fabricated — the model selects a sentence number, and
   the code reconstructs the text from the source.

A change that weakens either will be declined even if it improves the numbers.
If you think one of them should change, open an issue and argue it first; do not
start with code.

**No runtime dependencies.** The panel uses only the standard library, and that
is a supply-chain requirement recorded in [`pyproject.toml`](pyproject.toml), not
an oversight. Adding one needs a deliberate decision and an entry in
`docs/14-decyzje/`.

## Style

Match the file you are editing. The comment density here is higher than usual and
comments explain **why**, often including what was tried and rejected — that is
the house style, not an accident. Keep it.
