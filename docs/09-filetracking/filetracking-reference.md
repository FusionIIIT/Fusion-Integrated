# File Tracking System (FTS-007) — Specification Traceability Reference

| Specification ID | Description | Enforcement Location |
| :--- | :--- | :--- |
| `CFR-FTS-001` | File Creation and Draft State | [`modules/filetracking/services/files.py:63`](../../modules/filetracking/services/files.py:63#L63) |
| `CFR-FTS-002` | Subject & Content Definition | [`modules/filetracking/domain/rules.py:24`](../../modules/filetracking/domain/rules.py:24#L24) |
| `CFR-FTS-003` | Mandatory Initial Note/Comment | [`modules/filetracking/domain/rules.py:24`](../../modules/filetracking/domain/rules.py:24#L24) |
| `CFR-FTS-004` | File Circulation & Transfer | [`modules/filetracking/services/files.py:291`](../../modules/filetracking/services/files.py:291#L291) |
| `CFR-FTS-005` | Sequential Forwarding | [`modules/filetracking/services/files.py:330`](../../modules/filetracking/services/files.py:330#L330) |
| `CFR-FTS-006` | Single Current Holder Invariant | [`modules/filetracking/models/files.py:26`](../../modules/filetracking/models/files.py:26#L26) |
| `CFR-FTS-007` | Return to Previous Sender | [`modules/filetracking/services/files.py:417`](../../modules/filetracking/services/files.py:417#L417) |
| `CFR-FTS-008` | Mandatory Note on Forward/Return | [`modules/filetracking/domain/rules.py:32`](../../modules/filetracking/domain/rules.py:32#L32) |
| `CFR-FTS-009` | Inbox and Outbox Views | [`modules/filetracking/selectors/files.py:10`](../../modules/filetracking/selectors/files.py:10#L10) |
| `CFR-FTS-010` | Full Lifecycle Movement History | [`modules/filetracking/selectors/files.py:70`](../../modules/filetracking/selectors/files.py:70#L70) |
| `CFR-FTS-011` | File Archival & Final Closure | [`modules/filetracking/services/files.py:542`](../../modules/filetracking/services/files.py:542#L542) |
| `CFR-FTS-012` | Draft Discard & Cleanup | [`modules/filetracking/services/files.py:246`](../../modules/filetracking/services/files.py:246#L246) |
| `BR-FTS-001` | Unique Monotonic File ID | [`modules/filetracking/services/files.py:35`](../../modules/filetracking/services/files.py:35#L35) |
| `BR-FTS-002` | Single Active Custodian | [`modules/filetracking/domain/rules.py:40`](../../modules/filetracking/domain/rules.py:40#L40) |
| `BR-FTS-003` | Holder-Only Forwarding | [`modules/filetracking/services/files.py:311`](../../modules/filetracking/services/files.py:311#L311) |
| `BR-FTS-004` | Mandatory Movement Remarks | [`modules/filetracking/domain/rules.py:24`](../../modules/filetracking/domain/rules.py:24#L24) |
| `BR-FTS-005` | Draft Discard Restraint | [`modules/filetracking/domain/rules.py:56`](../../modules/filetracking/domain/rules.py:56#L56) |
| `BR-FTS-006` | Append-Only Movement Sequence | [`modules/filetracking/models/movements.py:23`](../../modules/filetracking/models/movements.py:23#L23) |
| `BR-FTS-007` | Return Exclusively to Prior | [`modules/filetracking/domain/rules.py:48`](../../modules/filetracking/domain/rules.py:48#L48) |
| `BR-FTS-008` | Sequential Timestamp Auditing | [`modules/filetracking/models/movements.py:24`](../../modules/filetracking/models/movements.py:24#L24) |
| `BR-FTS-009` | Association Scoping (Yield 404) | [`modules/filetracking/selectors/scoping.py:20`](../../modules/filetracking/selectors/scoping.py:20#L20) |
| `BR-FTS-010` | Attachment Size Constraints | [`modules/filetracking/domain/rules.py:80`](../../modules/filetracking/domain/rules.py:80#L80) |
| `BR-FTS-011` | Immutable System Audit Log | [`modules/filetracking/services/audit.py:10`](../../modules/filetracking/services/audit.py:10#L10) |
| `BR-FTS-012` | Owner-Only File Archival | [`modules/filetracking/domain/rules.py:72`](../../modules/filetracking/domain/rules.py:72#L72) |
| `BR-FTS-013` | Decoupled Outbox Notifications | [`modules/filetracking/services/notifications.py:30`](../../modules/filetracking/services/notifications.py:30#L30) |
| `BR-FTS-014` | Pure Framework-Free Domain | [`modules/filetracking/domain/state_machine.py:1`](../../modules/filetracking/domain/state_machine.py:1#L1) |
| `FTS-UC-001` | Create and Circulate File | [`modules/filetracking/services/files.py:63`](../../modules/filetracking/services/files.py:63#L63) |
| `FTS-UC-002` | Discard Uncirculated Draft | [`modules/filetracking/services/files.py:246`](../../modules/filetracking/services/files.py:246#L246) |
| `FTS-UC-003` | Update Uncirculated Draft | [`modules/filetracking/services/files.py:174`](../../modules/filetracking/services/files.py:174#L174) |
| `FTS-UC-004` | Forward Received File | [`modules/filetracking/services/files.py:291`](../../modules/filetracking/services/files.py:291#L291) |
| `FTS-UC-005` | Return Received File | [`modules/filetracking/services/files.py:417`](../../modules/filetracking/services/files.py:417#L417) |
| `FTS-UC-006` | View Movement History | [`modules/filetracking/selectors/files.py:70`](../../modules/filetracking/selectors/files.py:70#L70) |
| `FTS-UC-007` | Archive Circulated File | [`modules/filetracking/services/files.py:542`](../../modules/filetracking/services/files.py:542#L542) |
| `FTS-UC-008` | View Inbox Files | [`modules/filetracking/selectors/files.py:10`](../../modules/filetracking/selectors/files.py:10#L10) |
| `FTS-UC-009` | View Outbox Files | [`modules/filetracking/selectors/files.py:22`](../../modules/filetracking/selectors/files.py:22#L22) |
| `FTS-UC-010` | View Archived Files | [`modules/filetracking/selectors/files.py:52`](../../modules/filetracking/selectors/files.py:52#L52) |
| `BW-FTS-01` | Basis Workflow: Initial Creation | [`modules/filetracking/domain/state_machine.py:17`](../../modules/filetracking/domain/state_machine.py:17#L17) |
| `BW-FTS-02` | Basis Workflow: Forward Across Actors | [`modules/filetracking/domain/state_machine.py:20`](../../modules/filetracking/domain/state_machine.py:20#L20) |
| `BW-FTS-03` | Basis Workflow: Return to Previous | [`modules/filetracking/domain/state_machine.py:21`](../../modules/filetracking/domain/state_machine.py:21#L21) |
| `BW-FTS-04` | Basis Workflow: Final Archival | [`modules/filetracking/domain/state_machine.py:24`](../../modules/filetracking/domain/state_machine.py:24#L24) |
| `BW-FTS-05` | Basis Workflow: Create Draft | [`modules/filetracking/domain/state_machine.py:15`](../../modules/filetracking/domain/state_machine.py:15#L15) |
| `BW-FTS-06` | Basis Workflow: Update Draft | [`modules/filetracking/domain/state_machine.py:15`](../../modules/filetracking/domain/state_machine.py:15#L15) |
| `BW-FTS-07` | Basis Workflow: Discard Draft | [`modules/filetracking/domain/state_machine.py:16`](../../modules/filetracking/domain/state_machine.py:16#L16) |
| `BW-FTS-08` | Basis Workflow: Submit Draft | [`modules/filetracking/domain/state_machine.py:17`](../../modules/filetracking/domain/state_machine.py:17#L17) |
| `CW-FTS-01` | Composite Workflow: Routing Cycle | [`modules/filetracking/tests/test_workflows.py:10`](../../modules/filetracking/tests/test_workflows.py:10#L10) |
| `CW-FTS-02` | Composite Workflow: Draft to Circ | [`modules/filetracking/tests/test_workflows.py:40`](../../modules/filetracking/tests/test_workflows.py:40#L40) |
