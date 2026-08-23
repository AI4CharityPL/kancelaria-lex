# Runbook: security incident

> Deadlines run from the moment the incident is **established**. The clock starts earlier than people expect.

## Clocks

| Obligation | Deadline | Addressee |
|---|---|---|
| Early warning (KSC) | **24 h** | the competent CSIRT |
| Full report (KSC) | **72 h** | the competent CSIRT |
| Breach notification (GDPR art. 33) | **72 h** | the supervisory authority |
| Communication to individuals (GDPR art. 34) | without undue delay | the data subjects |
| Final report (KSC) | one month | the competent CSIRT |

The KSC obligations apply to the firm **only if it is within scope**; see scope assessment K-1. The GDPR obligations apply regardless.

## Overriding rule: report without disclosing privileged content

A report describes the **nature and extent** of the event, not the content of the file.

| Allowed | Not allowed |
|---|---|
| "Unauthorised access to the documents of one criminal case" | Names of parties, the case reference, document content |
| "Around 40 documents, categories of data: GDPR art. 9 and art. 10" | Extracts from the file, a description of the alleged offence |
| "Vector: a compromised user account" | |

The boundary has to be settled **before** an incident (task K-6). During one there is no time for it.

## Stage 1: detection and assessment *(0 to 4 h)*

**Signals:** a broken checksum chain in the audit log, a failed outbound connection attempt, a rejected write of `base_url` from outside the allowlist, an unusual pattern of access to case files, a mismatch in the model weight checksums, a report from a user.

**Actions:**
1. Notify the person responsible and the DPO.
2. **Preserve evidence before any repair:** a copy of the audit log, container logs and network state. Repair destroys traces.
3. Initial assessment: what, when, what extent, and whether it is ongoing.
4. **Start the clock:** record the time the incident was established.

**Decision:** is this a reportable incident? If in doubt, treat it as reportable and keep verifying. The deadline does not wait for the question to be settled.

## Stage 2: containment *(0 to 24 h)*

| Scenario | Action |
|---|---|
| Compromised account | Block the account, invalidate sessions, reset MFA |
| Unauthorised internal access | Withdraw permissions, preserve the log, notify the partners |
| Suspected container compromise | Stop the service; segmentation limits the reach |
| **Suspected outbound connection** | Disconnect from the LAN, capture traffic, analyse; see below |
| Loss of a backup medium | Assess whether the copy was encrypted and where the key was |
| Compromise of defence material | **Highest priority path.** Partners and a lawyer immediately |

**Early warning within 24 h**, if the reporting obligation applies. The warning may be incomplete; that is what it is for.

### Suspected outbound connection

This is the scenario the architecture is meant to make impossible. If it happens, it means all three layers failed at once and calls for a full reconstruction:

1. Physical disconnection.
2. Check layer A: did forbidden packages appear in the image?
3. Check layer B: was `base_url` changed? The audit log records every attempt.
4. Check layer C: was the network topology changed?
5. Analyse the captured traffic: where to, how much, what.
6. Establish whether privileged content was disclosed.

## Stage 3: reporting *(within 72 h)*

The full report: the nature of the incident, the categories and approximate number of people, the categories and approximate number of records, the likely consequences, the measures taken and planned, and the DPO's contact details.

**Review of the report by a lawyer for professional privilege is mandatory and happens before it is sent.**

Communication to individuals (art. 34) if the risk to rights and freedoms is high. With criminal case files that threshold is reached easily, because art. 9 and art. 10 data are present by definition.

## Stage 4: eradication and restoration

Remove the cause, restore from a clean backup if integrity is in doubt, run the **isolation tests before returning to work**, then observe.

## Stage 5: lessons *(within 30 days)*

Final report. Root cause analysis. Update the threat model and the risk register. **Add a test that would have caught this incident earlier.** If that cannot be done, it is a finding in itself.

## Contacts

| Role | Person | Telephone |
|---|---|---|
| Responsible for the system | _to be completed_ | |
| DPO | _to be completed_ | |
| Partner on call | _to be completed_ | |
| Competent CSIRT | _to be established after K-1_ | |
| Supervisory authority | | |

**Keep the contact list on paper, outside the system.** An incident may include the unavailability of the system that holds the contacts.

## Exercise

At least once a year, a tabletop exercise. Without exercising it, the runbook stays a document rather than a capability. The recommended first scenario is unauthorised internal access to a criminal case file, as the most likely one in a closed architecture.
