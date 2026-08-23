# GDPR: record of processing activities and art. 32 measures

> **Disclaimer.** A skeleton to be completed and approved by the controller and the data protection officer.

## Record of processing activities (art. 30)

An entry in the firm's existing record. The system does not create a new processing activity, only a new **manner** of processing files the firm already holds.

| Field | Content |
|---|---|
| Name of the activity | Analysis of case files using a local supporting system |
| Controller | _to be completed_ |
| DPO | _to be completed_ |
| Purposes | Support in analysing case files, keeping the procedural deadline diary, searching documents |
| Categories of people | Clients, opposing parties, witnesses, victims, experts, representatives, officers |
| Categories of data | Identifying, contact, **art. 9**, **art. 10**, content of procedural documents |
| Recipients | **None.** A closed system, with no entrustment of processing |
| Transfers outside the EEA | **None**, excluded by construction |
| Erasure period | In line with the rules on retaining case files, ten years by default |
| General description of measures | See the art. 32 section below |

**The entry "recipients: none" is the main effect of this project.** Any cloud tool would require an entry here and a processing agreement, and with professional privilege also a decision on whether entrustment is permissible at all.

## Technical and organisational measures (art. 32)

### (a) Pseudonymisation and encryption

| Measure | Implementation |
|---|---|
| Encryption at rest | Full disk encryption and a data key for each case |
| **Defence material** | Separate store, separate key, separate authorisation |
| Encryption in transit | mTLS between segments, our own CA (no ACME) |
| Backups | Encrypted, key held separately |
| Pseudonymisation | Before export and before using material in evaluation |

### (b) Confidentiality, integrity, availability, resilience

| Dimension | Measures |
|---|---|
| Confidentiality | Three layers of isolation, named access, need-to-know, MFA, ethical walls |
| Integrity | Audit log with a chain of checksums, checksums of model weights, images pinned by `sha256` |
| Availability | Backups, RPO ≤ 24 h, RTO ≤ 8 h |
| Resilience | Segmentation limiting the reach of a breach, resource limits, no root in containers |

### (c) Restoring availability

Daily backups, encrypted, held outside the production system. **Restore tested quarterly**, because an untested backup is not a backup. Details: [`../operations/backup-and-recovery.md`](../operations/backup-and-recovery.md).

### (d) Regular testing and assessment of effectiveness

Here the system goes beyond usual practice: the effectiveness of the isolation measures is **tested by execution on every build**, rather than assessed by a periodic review of documentation.

| Test | Frequency |
|---|---|
| Isolation tests (`tests/izolacja/`) | Every build |
| Packet capture during a full run | Before every release |
| Red team tests (`tests/injection/`) | Every build |
| Quality gates (gold set) | On a change of model or retrieval |
| Restore test | Quarterly |
| Access review | Quarterly |
| Risk register review | Twice a year |

## Retention and the right to erasure: a tension to settle

A person whose data went into a case file as a witness or a victim may demand erasure (art. 17 GDPR).

**The retention obligation will usually prevail**: art. 17(3)(b) (legal obligation) and (e) (establishment, exercise or defence of claims), and beyond that professional privilege and the rules on retaining case files.

But the answer "we never delete" is wrong. Requirements for the system:

1. The ability to **suspend erasure** (a legal hold) irrespective of the retention period.
2. A register of erasure requests together with the reasoning behind each decision.
3. Automatic deletion after the period **must not** touch files under a hold.
4. Erasure is effective, because without fine-tuning the data does not become fixed in the weights.

The assessment procedure is drawn up by the DPO.

## Personal data breaches

Notification to the supervisory authority within 72 hours (art. 33), communication to individuals where the risk is high (art. 34).

Collision with professional privilege: a notification must not disclose privileged content. A shared path with the KSC obligation: [`../operations/incident-response.md`](../operations/incident-response.md).

A practical note: in a closed architecture the most likely breach is not a leak to the outside, but access by an unauthorised person inside the firm (risk R-3) or the loss of a backup medium. The runbook has to cover those scenarios first.

## Tasks

| # | Task | Owner |
|---|---|---|
| P-1 | Add this entry to the record of processing activities | DPO |
| P-2 | Approve the DPIA | Controller and DPO |
| P-3 | Procedure for assessing erasure requests | DPO |
| P-4 | Update the information notices | lawyer |
| P-5 | User training, including the duty to review analyses (R-4) | DPO and project team |
| P-6 | Review of processing agreements: do the cloud tools used until now need terminating | lawyer |
