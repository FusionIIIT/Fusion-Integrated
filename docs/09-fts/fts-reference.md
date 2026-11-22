# FTS Specification Implementation Reference

This document is automatically generated and verified by `ops/docs/fts_reference.py`.
It maps every live specification identifier (CFR, AFR, BR, UC, BW) to its code.

| Spec ID | Description | Enforcing Code Location |
|---|---|---|
| `BR-FTS-001` | Single holder | [modules/fts/domain/state_machine.py#L11](modules/fts/domain/state_machine.py#L11) |
| `BR-FTS-002` | Owner retains ownership | [modules/fts/services/files.py#L95](modules/fts/services/files.py#L95) |
| `BR-FTS-003` | Forward custody transfer | [modules/fts/services/movements.py#L136](modules/fts/services/movements.py#L136) |
| `BR-FTS-004` | Return custody back | [modules/fts/services/movements.py#L281](modules/fts/services/movements.py#L281) |
| `BR-FTS-005` | Owner-only archival | [modules/fts/services/archival.py#L77](modules/fts/services/archival.py#L77) |
| `BR-FTS-006` | Mandatory remarks | [modules/fts/services/movements.py#L136](modules/fts/services/movements.py#L136) |
| `BR-FTS-007` | Draft editable pre-circ | [modules/fts/services/files.py#L262](modules/fts/services/files.py#L262) |
| `BR-FTS-008` | Discard draft transition | [modules/fts/services/files.py#L307](modules/fts/services/files.py#L307) |
| `BR-FTS-009` | Sequential ordering | [modules/fts/selectors/history.py#L9](modules/fts/selectors/history.py#L9) |
| `BR-FTS-010` | Scoped access | [modules/fts/selectors/scoping.py#L11](modules/fts/selectors/scoping.py#L11) |
| `BR-FTS-011` | Attachment limit | [modules/fts/models/attachments.py#L6](modules/fts/models/attachments.py#L6) |
| `BR-FTS-012` | Immutable audit log | [modules/fts/selectors/audit.py#L19](modules/fts/selectors/audit.py#L19) |
| `BR-FTS-013` | Notification tasks | [modules/fts/tasks.py#L12](modules/fts/tasks.py#L12) |
| `BR-FTS-014` | Audit continuity check | [modules/fts/tasks.py#L28](modules/fts/tasks.py#L28) |
| `FTS-UC-001` | Create institute file note | [modules/fts/services/files.py#L95](modules/fts/services/files.py#L95) |
| `FTS-UC-002` | Save file as draft | [modules/fts/services/files.py#L95](modules/fts/services/files.py#L95) |
| `FTS-UC-003` | Edit pre-circulation draft | [modules/fts/services/files.py#L262](modules/fts/services/files.py#L262) |
| `FTS-UC-004` | Discard uncirculated draft | [modules/fts/services/files.py#L307](modules/fts/services/files.py#L307) |
| `FTS-UC-005` | Forward active file | [modules/fts/services/movements.py#L136](modules/fts/services/movements.py#L136) |
| `FTS-UC-006` | Return active file | [modules/fts/services/movements.py#L281](modules/fts/services/movements.py#L281) |
| `FTS-UC-007` | Archive completed file | [modules/fts/services/archival.py#L77](modules/fts/services/archival.py#L77) |
| `FTS-UC-008` | View user file inbox | [modules/fts/selectors/files.py#L15](modules/fts/selectors/files.py#L15) |
| `FTS-UC-009` | View user file outbox | [modules/fts/selectors/files.py#L23](modules/fts/selectors/files.py#L23) |
| `FTS-UC-010` | Governance view | [modules/fts/selectors/audit.py#L19](modules/fts/selectors/audit.py#L19) |
| `BW-FTS-01` | File immediate circulation | [modules/fts/services/files.py#L95](modules/fts/services/files.py#L95) |
| `BW-FTS-02` | Sequential forwarding | [modules/fts/services/movements.py#L136](modules/fts/services/movements.py#L136) |
| `BW-FTS-03` | File return to sender | [modules/fts/services/movements.py#L281](modules/fts/services/movements.py#L281) |
| `BW-FTS-04` | Owner archival | [modules/fts/services/archival.py#L77](modules/fts/services/archival.py#L77) |
| `BW-FTS-05` | Draft discard workflow | [modules/fts/services/files.py#L307](modules/fts/services/files.py#L307) |
| `BW-FTS-06` | History inspection | [modules/fts/selectors/history.py#L9](modules/fts/selectors/history.py#L9) |
| `BW-FTS-07` | Soft-delete draft | [modules/fts/services/files.py#L307](modules/fts/services/files.py#L307) |
| `BW-FTS-08` | Module integration | [modules/fts/contracts.py#L66](modules/fts/contracts.py#L66) |
| `CFR-FTS-01` | Core File Creation | [modules/fts/services/files.py#L95](modules/fts/services/files.py#L95) |
| `CFR-FTS-02` | Core Forwarding | [modules/fts/services/movements.py#L136](modules/fts/services/movements.py#L136) |
| `CFR-FTS-03` | Core File Return | [modules/fts/services/movements.py#L281](modules/fts/services/movements.py#L281) |
| `CFR-FTS-04` | Core Archival | [modules/fts/services/archival.py#L77](modules/fts/services/archival.py#L77) |
| `CFR-FTS-05` | Core Audit | [modules/fts/selectors/audit.py#L19](modules/fts/selectors/audit.py#L19) |
| `AFR-FTS-011` | Reference generation | [modules/fts/models/files.py#L20](modules/fts/models/files.py#L20) |
| `AFR-FTS-012` | Subject and metadata | [modules/fts/domain/entities.py#L16](modules/fts/domain/entities.py#L16) |
| `AFR-FTS-013` | Attachment upload | [modules/fts/models/attachments.py#L6](modules/fts/models/attachments.py#L6) |
| `AFR-FTS-014` | Draft capability | [modules/fts/domain/state_machine.py#L10](modules/fts/domain/state_machine.py#L10) |
| `AFR-FTS-015` | Draft modification | [modules/fts/services/files.py#L262](modules/fts/services/files.py#L262) |
| `AFR-FTS-016` | Draft discarding | [modules/fts/services/files.py#L307](modules/fts/services/files.py#L307) |
| `AFR-FTS-021` | Forward to employee | [modules/fts/services/movements.py#L136](modules/fts/services/movements.py#L136) |
| `AFR-FTS-022` | Mandatory forward note | [modules/fts/services/movements.py#L136](modules/fts/services/movements.py#L136) |
| `AFR-FTS-023` | Forward custody | [modules/fts/domain/state_machine.py#L27](modules/fts/domain/state_machine.py#L27) |
| `AFR-FTS-024` | Notify | [modules/fts/services/notifications.py#L11](modules/fts/services/notifications.py#L11) |
| `AFR-FTS-031` | Return to handler | [modules/fts/services/movements.py#L281](modules/fts/services/movements.py#L281) |
| `AFR-FTS-032` | Mandatory return note | [modules/fts/services/movements.py#L281](modules/fts/services/movements.py#L281) |
| `AFR-FTS-033` | Return custody | [modules/fts/domain/state_machine.py#L27](modules/fts/domain/state_machine.py#L27) |
| `AFR-FTS-041` | Archival by owner | [modules/fts/services/archival.py#L77](modules/fts/services/archival.py#L77) |
| `AFR-FTS-042` | Archived status | [modules/fts/domain/state_machine.py#L12](modules/fts/domain/state_machine.py#L12) |
| `AFR-FTS-043` | Archived lock | [modules/fts/domain/state_machine.py#L27](modules/fts/domain/state_machine.py#L27) |
| `AFR-FTS-051` | History retrieval | [modules/fts/selectors/history.py#L9](modules/fts/selectors/history.py#L9) |
| `AFR-FTS-052` | Governance metrics | [modules/fts/selectors/audit.py#L27](modules/fts/selectors/audit.py#L27) |
| `AFR-FTS-053` | Audit trail | [modules/fts/selectors/audit.py#L19](modules/fts/selectors/audit.py#L19) |
| `AFR-FTS-054` | Immutable logging | [modules/fts/services/audit.py#L11](modules/fts/services/audit.py#L11) |
