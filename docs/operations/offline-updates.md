# Runbook: updates in a disconnected environment

## The problem

Being cut off from the internet protects the case files, but it also cuts off security patches. Without a procedure, the system stands a year later on components with publicly known vulnerabilities, and by then only the isolation defends it.

The answer is **a deliberate maintenance window** instead of automatic background updates.

## Rules

1. The production environment **never** downloads anything from the internet, including during an update.
2. The package is built in a preparation environment, verified, and carried across by hand.
3. **The two-person rule:** whoever builds the package does not carry it across alone.
4. Every update is reversible. No tested path back means no update.

## Roles

| Role | Task |
|---|---|
| Preparing engineer | Builds the package, generates the SBOM and the checksums |
| Deploying engineer | Verifies the checksums, carries the package across and deploys it. **A different person from the above** |
| Approver | A partner or the administrator; approves the maintenance window |

## Procedure

### Stage 1: preparation *(zone with network access)*

1. Review component vulnerabilities against the current SBOM.
2. Decide the scope: what we update and why. "Because there is a new version" is not a justification; a vulnerability or a needed feature is.
3. Pull images **by `sha256`**, not by tag.
4. Pull model weights, if in scope, together with **licence verification** (the weights licence is often different from the code licence, as in the Surya case).
5. Build the application images with the **CI gate on the lockfile**: the build fails on `anthropic`, `google-genai`, `posthog` or `mcp`.
6. Run the full test set: isolation, red team, quality gates.
7. Generate the SBOM (CycloneDX) and the checksum manifest.
8. Sign the manifest.

**Condition for going further: every test passes.** A package with a failing isolation test does not leave stage 1.

### Stage 2: transfer

9. Write the package to a medium used for nothing else.
10. Antivirus scan on an intermediate workstation.
11. Hand the medium to the deploying engineer, **a different person from the one who prepared it**.
12. Verify the manifest signature and the checksums **before** carrying it into the closed zone.

### Stage 3: deployment *(maintenance window)*

13. Approval from the approver; notify users.
14. **A backup before the change:** full and verified.
15. Verify the checksums again on the target side.
16. Import the images into the local registry mirror.
17. Deploy; run database migrations.
18. **Isolation tests on the production side.** This is not a repeat of stage 1, because the network topology here is different.
19. Smoke run: upload a document, OCR, indexing, a query with citations.
20. Write it up in the change journal: what, when, who, checksums, test results.

### Stage 4: after deployment

21. Observe for 24 hours.
22. Update the SBOM and the version register in `models/`.
23. Roll back if anything failed.

## Rollback

Conditions that force a rollback, **with no discussion**:

- a failing isolation test after deployment,
- a mismatch in a model weight checksum,
- a database migration error,
- quality falling below the gate thresholds.

Procedure: stop the services, restore the previous images from the mirror, restore the database from the backup made at step 14, run the isolation tests, write it up in the journal.

The previous image version stays in the mirror **at least until the observation period from step 21 ends**.

## Frequency

| Kind | Window |
|---|---|
| Critical vulnerability in an exposed component | Immediately, in an extraordinary window |
| High-severity vulnerabilities | Within 30 days |
| Routine updates | Quarterly |
| Language model update | Only after passing the **full quality gates**, because a newer model is not automatically better for Polish case files |

## Change journal

`infra/dziennik-zmian.md` holds the date, the scope, the checksums, the test results, the people involved and the outcome of observation. It is evidence for an audit under art. 21(e) of the Polish KSC act.
