# BADMS domain model

This document describes the data model in `modules/badms/models.py`. Database records store request metadata and opaque object keys; file bytes belong in the BADMS recovery storage alias.

## Records

| Model | Purpose | Important relationships and lifecycle data |
|---|---|---|
| `BackupSchedule` | Local or global schedule for one dataset | Unique `(scope, dataset)`; enabled flag, frequency, time, timezone, classifications, updater |
| `BackupRun` | One manual or scheduled backup attempt | Trigger, dataset, actor snapshot, start/scheduled/completion times, result, artifact key, SHA-256, integrity result |
| `ArchiveRequest` | User-submitted archive with authoritative review state | User/department snapshot, metadata, attachment key/size, submitted and final classification, actor IDs, archive key/checksum, retention deadline |
| `RestorationRequest` | Request to retrieve an archived item | User/department snapshot, protected FK to `ArchiveRequest`, classification, approval actor, outcome, restored object key |
| `StorageExtensionRequest` | Request for additional user storage | Department snapshot, requested bytes, justification, captured usage/capacity, HoD decision |
| `StorageThreshold` | Latest usage and full-quota state per user | Unique user identifier, department, usage, quota, `is_full` |
| `SecurityPolicy` | Institute-supplied classification retention durations | Singleton row with positive days per classification and updater; AES-256 standards are fixed in code |
| `SpecialArchiveOperation` | Recorded offline-triggered special archive | Super Admin actor, offline request reference, research description, archive key/checksum, outcome |
| `AuditEvent` | Append-style operational and security history | Actor, department, action, object, outcome, timestamp, structured details |
| `NotificationOutbox` | Durable pending email delivery | Recipient, message, attempt count, delivery state, last error |

`TimeStampedModel` supplies creation/update timestamps. `UserScopedModel` supplies the opaque IAM user identifier. BADMS does not store passwords, duplicate identities, or introduce a cross-module foreign key. The only foreign key is the local restoration-to-archive relationship.

## Data and trust boundaries

- IAM is authoritative for identity, active role, module grants, and permissions. The IAM integration stores permission overrides in the IAM service and audits changes there.
- Department identifiers and requester addresses are snapshots supplied from the directory service for routing and audit context.
- Database dumps and uploaded archives use `STORAGES["badms"]`; the platform-wide `default` storage remains independent.
- Production S3 configuration uses a workload role, SSE-KMS, and an institute-owned KMS key. BADMS stores an object key and checksum, never key material.
- Institute retention durations, quotas, capacity limits, contact routing, and cloud resources are deployment inputs. Missing retention policy blocks classification rather than inventing a duration.
- Approval services exclude the submitter from HoD decisions, classification, Sensitive archive creation, and restoration approval/execution. Department approval queues omit the approver's own pending submissions.
