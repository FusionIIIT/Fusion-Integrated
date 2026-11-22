# Super Admin: Role Management Business Rules

## BR-SA-006: Multiple Concurrent Roles
- A basic user may hold multiple additional roles simultaneously unless an explicit conflict rule invalidates the combination.

## BR-SA-007: Singular Role Occupancy
- A role designated as singular (e.g., Dean, Director, HOD) may have only ONE active holder for the same scope at any given time.
- Overlapping assignments for a singular role must be rejected; reassignment must be used instead.

## BR-SA-008: Role Assignment Dating
- Every role assignment must have an explicit start date.
- Time-bound roles must also specify an end date. Permanent roles may omit an end date.

## BR-SA-009: Automatic Role Activation and Expiry
- A future-dated assignment activates automatically on its start date.
- A time-bound role expires automatically when its end date is reached.

## BR-SA-010: Role User-Type Eligibility
- Roles must match user type metadata (e.g., a student cannot be assigned faculty or administrative roles).

## BR-SA-014: Role Revocation Handling
- Early role revocation requires an effective date and a mandatory reason.
- Immediately deactivates role permissions and reassigns or closes pending tasks.

## BR-SA-016: Role Expiry Reminder and Extension
- The system alerts users prior to role expiry and allows extension by setting a new end date and justification.

## BR-SA-033: Audit Event Coverage
- Every role assignment, reassignment, extension, and revocation must record an immutable audit log with timestamp, actor, action, and target.


