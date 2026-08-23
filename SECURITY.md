# Security

## What this project is, and what it is not

`kancelaria-lex` processes material covered by legal professional privilege, including the files of non-public criminal proceedings. The threat model is therefore different from that of a typical web application: **the adversary is not only an attacker on the network, but also an accidental leak of content to a cloud provider**, and the seizure of hardware.

The project's entire argument rests on two properties:

1. **Nothing leaves the device.** Three independent layers of isolation ([`docs/isolation-and-network.md`](docs/isolation-and-network.md)).
2. **A citation cannot be fabricated.** The model indicates a sentence number and the code reconstructs the text from the source ([`docs/adr/0007-citation-by-sentence-number.md`](docs/adr/0007-citation-by-sentence-number.md)).

**Modifying the code can remove exactly those two properties.** A version modified by a third party is not covered by any of the assurances in [`README.md`](README.md).

## Reporting a vulnerability

Report vulnerabilities **privately**, through "Report a vulnerability" in the repository's Security tab, rather than by opening a public issue.

**Do not include the content of case files or any real data in a report.** If a defect can only be demonstrated on data, describe it using the synthetic corpus in `eval/korpus-syntetyczny/` or on publicly available material.

Response time: the project is run on a voluntary basis, so we do not promise a service level. Reports concerning network isolation and citation verification are treated as priority.

## Areas of particular importance

Reports in these areas matter most, because they concern the properties the whole project rests on:

| Area | Why it is critical |
|---|---|
| Any path that sends data off the device | It undermines property 1 |
| A way to pass a citation that is inconsistent with its source | It undermines property 2 |
| Escaping the scope of a case (quoting from another case) | Ethical walls, art. 21(2)(i) of the Polish KSC act |
| Injecting instructions through document content | Case content is data, never a command |
| Reading a session or elevating privilege | Profile separation and authorship of entries |
| Leaking content into a log, journal or audit trail | T-4: the log records access, it does not copy content |

## Known limitations, reported rather than hidden

The following are **known and documented**. Reporting them is not a vulnerability, but information about how to exploit them is.

- **MFA is available but not the default.** `panel/profile.py` implements login and password (scrypt, a server-side session, throttling of repeated attempts), and `panel/totp.py` provides a second factor over TOTP per RFC 6238, with single-use backup codes. **Until the user enables it, login stays single-factor** and art. 21(2)(j) is not satisfied. The second factor is also illusory when the TOTP application sits on the same computer as the panel, and no code can check that.
- **The panel listens on `127.0.0.1` only and has no TLS of its own.** Exposing it on the firm's network requires a reverse proxy with TLS from an internal CA; the panel is not meant to be published without that layer ([`docs/operations/deployment.md`](docs/operations/deployment.md)).
- **Disk encryption is the firm's responsibility.** The `panel/dane/panel.sqlite3` database is not encrypted at rest by the application. If an unencrypted disk is seized, the case files are readable.
- **Q4 quantisation** lowers model quality and increases the tendency to hallucinate. It is acceptable in the development profile and not acceptable for criminal case files ([`docs/hardware-and-costs.md`](docs/hardware-and-costs.md)).
- **J-3 is 82% against a target of 90%.** The system answers some questions for which the file gives no basis. The citation is then genuine but does not support the proposition. That is why **a citation has to be clicked and checked**; see [`docs/measured-results.md`](docs/measured-results.md) and RY-16 in [`docs/risk-register.md`](docs/risk-register.md).

## The rule about data in the repository

**Real case files never enter the repository** (requirement T-6, [`docs/compliance/legal-professional-privilege.md`](docs/compliance/legal-professional-privilege.md)). That covers bug reports, tests that reproduce a problem, and screenshots.

If you notice that real data has reached the repository, report it through the private route above and treat it as an incident rather than an ordinary defect.
