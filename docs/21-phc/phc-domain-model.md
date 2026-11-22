# PHC domain model

## Ownership and identity

PHC business data lives in `fusion_integrated`. Every person reference is a plain integer `user_id`; PHC has no identity or access-control tables. The directory owns identity projection and `modules.directory.contracts.is_employee()` is the only employment eligibility check. No PHC model has a foreign key to another module or to the ERP.

## Medical records

`PatientVisit` stores the patient ID, visit date, clinical notes and recorder ID. A visit may have linked `Prescription` rows with medicine details, issue date and issuer ID. Compounder is the only PHC role that writes these records; patients read only their own. Visits and prescriptions are created in one transaction. Audit events record the action and object identifiers, never clinical text.

## Reimbursement

`ReimbursementPolicy` stores immutable effective date ranges and a positive submission window. The initial policy is 30 days from 2026-01-01. `ReimbursementClaim` stores claimant, prescription, amount, expense date and optional bill reference/remarks. A PostgreSQL exclusion constraint prevents overlapping policy periods. Submitted financial content is immutable. Each transition is represented by append-only `ReimbursementAction` history and an audit event in the same transaction.

## Inventory and requisitions

`InventoryItem` stores the catalogue entry and positive reorder threshold. `InventoryMovement` is an append-only signed quantity ledger; the visible stock is its sum and must never become negative. PostgreSQL trigger enforcement and row locking protect this invariant during concurrent adjustments. A `LowStockAlert` records the movement and below-threshold snapshot.

`InventoryRequisition` has a draft, pending approval, approved, rejected or fulfilled state. Its item and positive integer quantity lines become immutable after submission. Registrar decisions and Compounder fulfillment pass through the state transition service. Fulfillment records delivery status and does not silently alter stock.

## Schedules and attendance

`Doctor` stores display name, specialization and active status. `DoctorScheduleSlot` stores a weekday and local institute-time start/end, with draft or published status. A PostgreSQL exclusion constraint rejects overlapping slots for the same doctor and day. `DoctorAttendance` has one row per doctor and local calendar date; it stores available/departed status and the last updating user.

## Operations and communications

`AmbulanceUsage` stores event timestamp, patient name, destination and recorder. These records are restricted to Compounder and excluded from aggregate reports. `HealthAdvisory` stores title, body, publisher and publication timestamp; patients see only published advisories.

The notification outbox is written in the business transaction and uses a unique event key. The Celery task claims undelivered rows with `select_for_update(skip_locked=True)`, creates the user notification once, and marks delivery. PHC audit events, reimbursement actions and stock movements have indefinite retention and database-level append-only enforcement.

## Aggregate reporting

PHC reports expose only totals and date/category/status groupings. They contain no patient identifiers, directory fields, ambulance names or destinations, clinical notes, claim references or free-text remarks.
