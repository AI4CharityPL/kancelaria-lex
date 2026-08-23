# Authors

**kancelaria-lex** — a fully local AI system for analysing legal case files.

> Written in English for the same reason as `README.md` and `QUICKSTART.md`: so
> anyone can evaluate who built this. The rest of the project is deliberately
> Polish — see [the README](README.md).

## Creator — sole author

### Krzysztof Augiewicz — "one man army"

- **Role:** Creator, architect and sole author of this system
- **Email:** krzysztof.augiewicz@gmail.com
- **LinkedIn:** [krzysztof-a](https://www.linkedin.com/in/krzysztof-a-97a170185/)
- **GitHub:** [KrzysztofAugiewicz](https://github.com/KrzysztofAugiewicz)

Designed, written and verified by one person — the software, the measurement
harness that produced its numbers, and the compliance documentation. What that
covered:

**The idea the whole system rests on.** The model never writes a quotation. It
selects a *sentence number*, and the code reconstructs the text from the source
document. This is the difference between a fabricated citation being *detected*
and being **impossible to express** — an architectural decision, not a filter
bolted on afterwards, and it is what every other part of the design serves.

**Enforced locality.** Not a promise in a README but three independent layers:
import-time validation that refuses to start the process on a non-loopback model
address; a test that scans the codebase so a second network call cannot be added
quietly; four Docker segments, three of them `internal: true` with no route to a
gateway; and packet-level capture proving zero packets left while a container in
each segment actively tried to reach the internet.

**Zero runtime dependencies, on purpose.** Every third-party package is a package
somebody has to keep watching (art. 21(2)(d) of the Polish NIS2 implementation),
so the panel runs on the standard library alone — `http.server`, `sqlite3`,
`hashlib.scrypt`, `secrets`, `http.cookies`, and one `urllib.request` call to a
local Ollama. **BM25 ranking, tokenisation and language detection were written
from scratch** rather than pulled in.

**The panel and everything in it.** Case ingestion from PDF, DOCX, TXT and RTF;
retrieval and analysis; local profiles with password login and optional TOTP
two-factor; named conversation threads that can be closed and reopened; verified
backups with a restore that is actually tested; export to Markdown and HTML.

**The parts that must never be left to a model.** A deterministic procedural
deadline calculator — including movable feasts — computed by code rather than
generated; and an append-only audit log with a hash chain.

**The measurement.** The evaluation harness and its design: 722 documents across
one Polish and one English case, 100 matched questions, where every answerable
question has an identically-worded twin the files **cannot** answer — so "always
answer" and "always refuse" both score zero. Including the discipline of
publishing the results that look bad, the four hypotheses that were tested and
thrown away, and the profile a number belongs to quoted in the same breath as the
number.

**Compliance and licensing.** The AI Act / NIS2 / KSC documentation under `docs/`,
the register of model licences, versions and checksums in
[`models/manifest.md`](models/manifest.md), and the third-party licence analysis
in [`NOTICE.md`](NOTICE.md) — including the finding that a repository's own licence
is not enough to judge by, because model weights carry their own terms.

**The gates that keep it honest.** The isolation and hygiene test suites and the
CI that runs them.
