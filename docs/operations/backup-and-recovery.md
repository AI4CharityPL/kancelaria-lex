# Backups and recovery

## Targets

| Parameter | Value | Meaning |
|---|---|---|
| RPO | ≤ 24 h | Maximum work lost |
| RTO | ≤ 8 h | Maximum downtime |
| Restore test | quarterly | **An untested backup is not a backup** |
| Backup retention | 30 daily and 12 monthly copies | |

## What the backup covers

| Resource | Notes |
|---|---|
| PostgreSQL database | Consistent dump, including the vectors |
| Object store (MinIO) | Original documents |
| **Defence material store** | **Separate copy, separate key**, see below |
| Audit log | Outside the application database; the copy preserves the checksum chain |
| Configuration and compose | Versioned in the repository |
| Model weights | **Not in the daily backup.** Immutable and large; restored from the offline package following the manifest in `models/` |

Leaving the weights out of the daily backup is deliberate: they are a dozen or so gigabytes of immutable data that can be restored from the installation package. Copying them daily would lengthen the window and consume storage for no benefit.

## Rules

1. **The backup is encrypted**, with the key held separately from the medium.
2. The backup medium is kept outside the server room; losing the medium is a realistic incident scenario.
3. **Defence material has its own copy and its own key.** Restoring the main backup neither restores defence material nor gives access to it.
4. The backup does not leave the firm's control. No cloud service: the same rule applies to it as to production data.
5. The restore test runs on **a separate machine**, not on the production one.

## Keys, the most fallible point

Backups most often fail not through loss of data but through **loss of the key**.

| Key | Storage | Copy |
|---|---|---|
| Main backup key | Firm safe and a second location | Two copies, held separately |
| **Defence material key** | Hardware carrier, two-person authorisation | A copy in escrow, with a documented access procedure |
| Disk key | As above | As above |

Losing the defence material key means **irreversible loss of access** to the most important data in the system. The escrow procedure needs approval by the partners, because it is a decision about the trade-off between the risk of loss and the risk of disclosure.

## Restore test: quarterly procedure

1. A clean machine, with no contact with production.
2. Restore the database and the object store from the backup.
3. Restore the model weights from the offline package, **verifying the checksums**.
4. Start the stack and run the **isolation tests**: the restored environment has to be cut off in exactly the same way.
5. Verify: the number of cases and documents matches, **the audit log checksum chain is unbroken**, and a smoke run works from document through OCR and indexing to a query with citations.
6. Separately: a restore test of the defence material, including the key access procedure.
7. **Measure the actual time taken.** If it exceeds the RTO, then the RTO is fiction and needs either correcting or a better procedure.
8. Write it up in the journal; destroy the data on the test machine.

Step 5 with the audit log chain check matters: a backup that breaks the chain undermines the evidential value of the log.

## Failure scenarios

| Scenario | Response |
|---|---|
| Disk failure | Restore from the latest daily backup, within the RTO |
| Database corruption | Point-in-time restore |
| Human error (a case deleted) | Selective restore from a backup |
| Ransomware | Restore from an offline backup; segmentation limits the reach |
| Loss of the premises (fire, flood) | Restore on new hardware from the copy in the second location |
| **Seizure of hardware** | Defence material stays unreadable without its separate key |

The last row is the real justification for separate keying; see [`../compliance/legal-professional-privilege.md`](../compliance/legal-professional-privilege.md), requirement T-1.

## Journal

`infra/dziennik-kopii.md` holds the test date, the restore time, the verification result and any problems found. It is evidence for art. 32(c) and (d) GDPR and art. 21(c) of the Polish KSC act.
