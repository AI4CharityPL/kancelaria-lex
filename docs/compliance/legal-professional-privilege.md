# Legal professional privilege: technical requirements

> **Disclaimer.** This document translates professional obligations into technical requirements. Interpretation of the law is settled by the firm's own lawyer.

## Why this matters more than the GDPR

The GDPR allows for compromise: data may be processed on an appropriate legal basis, entrusted to a processor under a contract, transferred outside the EEA with appropriate safeguards.

**Legal professional privilege knows no such compromise.** Disclosing information covered by advocate or legal-counsel privilege breaches a professional obligation regardless of what processing agreement was signed with the supplier.

That is the real justification for a closed architecture. The GDPR alone would not forbid using a cloud provider under a suitable contract. Professional privilege forbids it in practice.

## Two levels, two regimes

| | Advocate and legal-counsel privilege | **Defence privilege** |
|---|---|---|
| Scope | Everything the lawyer learned in connection with providing legal assistance | Facts learned while advising or conducting a case **as defence counsel** |
| Lifting | Exceptionally, by court order (art. 180 § 2 of the Polish Code of Criminal Procedure) | **Cannot be lifted.** Defence counsel may not be examined at all (art. 178 pt 1) |
| Technical consequence | Raised standard protection | **Separate store, separate key, separate authorisation** |

The difference between them is one of kind, not of degree. Defence material is the only category of data in this system that no legal procedure can compel, and therefore the only one whose technical protection must hold even against a lawful demand to surrender the system.

## Technical requirements

### T-1. Defence material cannot be a record with a flag

A flag in the database is changed by one query. A database backup contains everything regardless of flags. Seizure of the hardware gives access to all of it.

**Requirement:** a separate object store, encrypted with a key unavailable to the process serving the remaining cases, behind separate authorisation.

**Effect:** a dump of the main database, whether from a failure, a backup or a seizure, does not contain defence material in readable form.

### T-2. The defence-material key lives outside the system

The key must not sit in the same place as the data. The target is a hardware carrier (a token or an HSM) or split storage with two-person authorisation. Losing the key means losing access, so a copy of the key needs its own procedure, described in [`../operations/backup-and-recovery.md`](../operations/backup-and-recovery.md).

### T-3. Zero connectivity, no exceptions

Three layers of isolation ([`../isolation-and-network.md`](../isolation-and-network.md)). There is no category of "less sensitive data that may be sent". The mere fact that a case is being conducted is covered by privilege, so metadata is covered too.

### T-4. The audit log as evidence of due diligence

In a dispute over the observance of privilege, the firm has to be able to show who had sight of the file. A log open to modification is not evidence, hence the chain of checksums and storage outside the application database.

The log records access but **does not copy the content of the file**. Otherwise it would itself become a second body of privileged material.

### T-5. Ethical walls

A conflict of interest is a professional breach regardless of intent. Checks run when access is granted and when a case is assigned; breaking a wall is possible only by decision of the administrator, with a justification and an audit entry.

### T-6. Development work on a synthetic corpus

A lawyer does not discuss the details of a case with an outsider. The same rule applies to tools: real case files do not go into the repository, into a test environment, or into the context of external tools.

Hence `eval/korpus-syntetyczny/`: fictional case files in Polish procedural form, built to reproduce the structure and the difficulties of real documents without reproducing real data.

### T-7. Reporting an incident without disclosing privileged content

Reporting obligations (24 and 72 hours under the Polish KSC act, 72 hours under the GDPR) collide with privilege. A report has to describe the nature and extent of the event **without content covered by privilege**.

The boundary has to be settled **before** an incident occurs, which is task K-6 in [`nis2-ksc-mapping.md`](nis2-ksc-mapping.md). During an incident there is no time for that analysis.

## Consequences for design decisions

| Decision | Justification in privilege |
|---|---|
| No cloud provider of any kind | Disclosure regardless of any processing agreement |
| Removal of the MCP server | An external agent client is a disclosure channel |
| No fine-tuning of the model on case files | The weights could fix privileged content |
| `gotenberg` with no network route | Fetching a resource embedded in a letter confirms possession of the document |
| Port 5555 closed | Task names reveal case metadata |
| Separate store for defence material | Art. 178 pt 1, no mechanism for lifting privilege |
| Synthetic corpus during development | Case files do not leave the firm even to build the system |

## For the firm's lawyer to settle

1. Is material marked as defence material by hand on upload, or does it follow from the type of case?
2. Who may apply and remove the defence-material marking?
3. What is the procedure when an authority demands the data, given the differing regimes of the two privileges?
4. Where does the boundary of an incident report lie (T-7)?
5. Is it acceptable to keep the files of different clients in one instance, or is separation deeper than logical required?
