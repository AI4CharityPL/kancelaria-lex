# Data protection impact assessment (DPIA), art. 35 GDPR

> **Disclaimer.** A DPIA skeleton prepared from the technical side. The assessment needs completing and approving by the controller, and consultation with the data protection officer. It is not a legal opinion.

## The DPIA is mandatory

This is not a matter of discretion. The conditions in art. 35(3) GDPR are met several times over:

| Condition | Occurrence |
|---|---|
| Large-scale processing of special categories of data (art. 9) | Case files contain data on health, sex life, opinions and affiliations |
| Data relating to convictions and offences (art. 10) | The substance of criminal cases |
| Systematic evaluation based on automated processing | Classifying documents, detecting discrepancies, proposing deadlines |
| New technology | Local language models applied to case files |
| Data of dependent or particularly vulnerable people | Defendants, victims, witnesses, minors |

On top of that comes what the GDPR does not govern and what matters more here: **legal professional privilege**, including defence privilege, which cannot be lifted.

## 1. Description of the processing

**Purpose:** supporting lawyers in analysing case files and conducting cases: search, chronology, proposed deadlines, detection of discrepancies.

**Scope of data:** identifying data of parties and participants, art. 9 data, art. 10 data, the content of procedural documents, case metadata.

**Categories of people:** clients, opposing parties, witnesses, victims, experts, representatives, officers.

**Legal bases:** performance of the legal services contract (art. 6(1)(b)), legal obligation (art. 6(1)(c)) and legitimate interests (art. 6(1)(f)). For art. 9 data it is the establishment, exercise or defence of legal claims (art. 9(2)(f)). For art. 10 data, processing under the control of official authority or authorised by national law (**to be confirmed with the DPO, together with the Polish acts on the bar and on legal counsels**).

**Recipients: none.** The system is closed. There is no entrustment of processing to a cloud provider, which is the main effect of the architecture.

**Transfers outside the EEA: none**, excluded by construction (three layers of isolation).

**Retention:** ten years by default, configurable, with the ability to suspend deletion.

## 2. Necessity and proportionality

| Question | Answer |
|---|---|
| Could the purpose be achieved less intrusively? | The system does not widen the scope of data, because the firm already holds these files by virtue of conducting the case. What changes is the manner of processing, not the scope. |
| Is the scope minimal? | Yes: no enrichment from outside, no profiling of individuals, no data from beyond the case file. |
| Does automated processing produce legal effects for individuals? | **No.** The output is working material for a lawyer. No decision is taken automatically, so art. 22 GDPR does not apply. |
| Does data go into training models? | **No.** Fine-tuning on case files was deliberately rejected; see [`../ai-stack.md`](../ai-stack.md). The model weights are immutable. |

The last point matters: without fine-tuning, **personal data does not become fixed in the model weights**. Deleting a document deletes the data in reality, without the problem of "a model that remembers".

## 3. Risks to rights and freedoms

| # | Risk | Likelihood | Impact | Measures | Level after |
|---|---|---|---|---|---|
| R-1 | Case files leak to an external model provider | Very low | **Critical** | Three layers of isolation, tested by execution | Very low |
| R-2 | Disclosure of defence material | Very low | **Critical** | Separate store, separate key, separate authorisation | Very low |
| R-3 | Access by an unauthorised person inside the firm | Medium | High | Named access, need-to-know, ethical walls, MFA, audit log | Low |
| R-4 | A faulty analysis affects the defence | Medium | High | Forced citation with mechanical verification, mandatory review by a lawyer, quality gates | Medium |
| R-5 | A deadline missed through a fault of the system | Low | High | Deterministic engine, confirmation by a lawyer, repeated warnings | Low |
| R-6 | Data loss | Low | High | Encrypted backups, **tested** restore | Low |
| R-7 | Manipulation through a document from the opposing party | Medium | Medium | No network tools, citation verification, red team tests | Low |
| R-8 | Data becoming fixed in the model weights | **Excluded** | not applicable | No fine-tuning | not applicable |

### R-4 stays at medium, deliberately

It is the only risk we do not bring down to low, and honesty requires saying so plainly.

Citation verification confirms that the quoted fragment **exists in the file and was not fabricated**. It does not confirm that **the conclusion drawn from that fragment is sound**. The model can quote correctly and interpret wrongly, and in the development profile (Q4 quantisation) that risk is higher.

The mitigation is organisational rather than technical: **every analysis is reviewed by a lawyer**, and the system is presented to users as a working tool rather than a source of findings. The interface has to say so, not only the terms of use.

## 4. Rights of data subjects

| Right | Implementation | Notes |
|---|---|---|
| Access (art. 15) | Through the firm, on general terms | Limited by professional privilege and the rights of third parties |
| Rectification (art. 16) | Possible | The procedural document stays unchanged as evidence; correction happens in the metadata layer |
| Erasure (art. 17) | **Usually excluded** | Art. 17(3)(b) and (e): legal obligation, and establishment, exercise or defence of claims. **Each case needs assessment**; the system must be able to suspend deletion |
| Restriction (art. 18) | Possible | Marking on the case |
| Portability (art. 20) | Does not apply | The basis is neither consent nor solely a contract with the data subject |
| Objection (art. 21) | Assessed individually | Overriding interest in conducting the defence |
| Automated decisions (art. 22) | **Does not apply** | There are no automated decisions |

**A tension to settle:** a person whose data appears in the file as a witness or a victim may demand erasure. The obligation to retain the file and the right to a defence will usually prevail, but the answer "we never delete" is wrong. The assessment procedure needs to be drawn up by the DPO.

## 5. Outcome

**Residual risk: acceptable**, subject to R-4.

**Prior consultation with the supervisory authority (art. 36 GDPR): provisionally not required**, because the measures applied bring risks R-1 and R-2 down to very low. The DPO confirms this assessment.

A closed architecture **reduces** the risk profile relative to the current state, if the firm has been using any cloud tools until now. The main effect of this assessment is therefore that the project removes existing risks rather than introducing new ones.

## Conditions for admitting real data

The DPIA applies **conditionally**. The conditions must be met together:

1. The gates in [`../testing-and-gates.md`](../testing-and-gates.md) pass, including the isolation tests and the packet capture.
2. The production model profile (Q8 or higher). **The Q4 development profile is not approved for real case files.**
3. The audit log works and resists tampering.
4. Defence material has its own store and its own key.
5. A backup has been restored in a test at least once.
6. Users are trained, including in the duty of review (R-4).

## Review

On every change of model, scope of data or architecture; otherwise once a year.

| Field | Value |
|---|---|
| Controller | _to be completed_ |
| DPO | _to be completed_ |
| Date drawn up | 14.08.2026 |
| Date approved | _pending_ |
