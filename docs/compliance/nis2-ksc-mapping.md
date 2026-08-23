# NIS2 and the Polish KSC act: scope assessment and mapping of measures

> **Disclaimer.** A technical and organisational document, not a legal opinion. Whether the firm falls within scope, and how the provisions are to be read, is settled by the firm's own lawyer. Legal position as at 14.08.2026; check that it is current before relying on it.

## A deadline that is already running

The amendment to the Polish act on the national cybersecurity system, implementing the NIS2 directive:

| Date | Event |
|---|---|
| 19.02.2026 | Signed by the President |
| 02.03.2026 | Published in the Journal of Laws |
| 03.04.2026 | **Entry into force** |
| **02.10.2026** | **Deadline for self-identification and entry in the register** |
| 02.04.2027 | Deadline for implementing risk-management measures |
| 03.04.2028 | Deadline for the first audit for essential entities |

**About seven weeks remain to the registration deadline** (as at 14.08.2026).

The amendment widens the scope from roughly 400 entities to roughly 42,000. It works on a **self-identification model**: the entity assesses for itself whether it is in scope and registers itself. Absence from the register is not a neutral state.

**This task is independent of building the system.** It does not wait for Phase 6 or for the proof of concept. It is the first item of compliance work and it needs a decision from the firm, not code.

## Does the firm fall within scope?

**A law firm does not become an essential or important entity merely by being a law firm.** Legal services do not appear expressly in the directive's sectoral annexes.

Classification requires several elements to be considered together:

| Element | Question to settle |
|---|---|
| Actual business model | Does the firm provide services beyond legal assistance, for instance managed ICT services? |
| Sector | Does any line of business fall into the annexes? |
| Size thresholds | Headcount and turnover against the statutory thresholds |
| Related entities | Do ownership links change the classification? |
| Role in the supply chain | Is the firm a supplier to an essential entity? |

**The likely answer for a typical firm: not directly in scope.** But that has to be *established and documented* rather than assumed, because the self-identification model puts the burden of assessment on the entity.

### The real vector: the supply chain

Even where a firm is not directly in scope, art. 21(2)(d) of the directive requires essential and important entities to address the security of **relationships with their direct suppliers and service providers**.

A firm acting for a bank, a hospital, an energy operator or a digital service provider will receive security requirements **contractually**: questionnaires, clauses, audits. That happens regardless of the firm's own classification.

The practical conclusion: **we build to the level of art. 21 whatever the scope assessment concludes.** If the obligation does not arise, we gain an advantage in conversations with corporate clients. If it does, we are ready.

## Mapping art. 21 onto measures in this system

| Requirement, art. 21(2) | Implementation | Where |
|---|---|---|
| **a)** risk analysis and information system security policies | STRIDE threat model, risk register kept as a living document | [`../threat-model.md`](../threat-model.md), [`../risk-register.md`](../risk-register.md) |
| **b)** incident handling | Runbook with 24 and 72 hour deadlines, roles, decision path | [`../operations/incident-response.md`](../operations/incident-response.md) |
| **c)** business continuity, backups, crisis management | RPO ≤ 24 h, RTO ≤ 8 h, restore **tested** quarterly | [`../operations/backup-and-recovery.md`](../operations/backup-and-recovery.md) |
| **d)** supply chain security | Images pinned by `sha256`, a local mirror, SBOM, verification before introduction | [`../isolation-and-network.md`](../isolation-and-network.md) |
| **e)** security in acquisition, development and maintenance; vulnerability disclosure | CI gate on the lockfile, SBOM, a maintenance window for patches, vulnerability review | [`../operations/offline-updates.md`](../operations/offline-updates.md) |
| **f)** assessing the effectiveness of measures | **Isolation tests as an executable gate**, plus the quality gates | [`../testing-and-gates.md`](../testing-and-gates.md) |
| **g)** cyber hygiene and training | Training programme; **the management training obligation** introduced by the amendment | Phase 9 plan |
| **h)** cryptography and encryption | Disk encryption, a key per case, a separate key for defence material, mTLS | [`gdpr-register-and-art32.md`](gdpr-register-and-art32.md) |
| **i)** human resources security, access control, asset management | Named access, need-to-know, ethical walls, asset register | [`../case-domain-model.md`](../case-domain-model.md) |
| **j)** MFA or continuous authentication, secured communications | MFA required (N-36), mTLS between segments, our own CA | [`../isolation-and-network.md`](../isolation-and-network.md) |

**Requirement (f) is met here more strongly than is usual.** "Assessing the effectiveness of measures" normally means a periodic review of documentation. Here the effectiveness of isolation is checked by an executable test on every build, and the final proof is a packet capture. That is material to put in front of an auditor.

## Management liability

The amendment introduces **liability of the entity's management** for cybersecurity duties, together with penalties, and an obligation to complete training.

For a law firm that means the subject cannot be delegated wholesale to an IT supplier: the partners are personally answerable, and training is an obligation rather than a recommendation.

## Reporting incidents

Where the reporting obligation applies, it follows a staged path: **an early warning within 24 hours**, **the full report within 72 hours**, and a final report within a month.

**Collision with professional privilege.** An incident report must not disclose content covered by advocate or defence privilege. The runbook has to state exactly what goes into a report: the extent and nature of the event, without the content of the file. This point needs to be settled by a lawyer before the first incident occurs, not during it.

## Tasks in the KSC area

| # | Task | Deadline | Owner |
|---|---|---|---|
| K-1 | **Scope assessment: is the firm in scope** | by 15.09.2026 | lawyer and partners |
| K-2 | **Registration, if in scope** | **by 02.10.2026** | partners |
| K-3 | Review of client contracts for supply chain requirements | by 31.10.2026 | lawyer |
| K-4 | Management training | by 31.12.2026 | partners |
| K-5 | Implementation of art. 21 measures | by 02.04.2027 | project team |
| K-6 | Settle the reporting and privilege collision | before the pilot | lawyer |
| K-7 | First audit (if an essential entity) | by 03.04.2028 | external auditor |

**K-1 and K-2 do not depend on this project and should not wait for it.**

## Sources to verify

The text of the amendment (Journal of Laws 2026 item 252), the FAQ of the Ministry of Digital Affairs, the register of essential and important entities, and directive (EU) 2022/2555, art. 21. Check that these are current before every decision, because the provisions and guidance are still in the implementation phase.
