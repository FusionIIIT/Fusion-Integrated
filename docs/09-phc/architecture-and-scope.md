# Primary Health Center module: architecture and scope

## Repository analysis

Fusion-Integrated is a Django 5.2 / Django REST Framework modular monolith with a React 18,
TypeScript, Vite and Mantine 7 client. IAM owns authentication, roles and institute identity;
this service stores no user table. The directory module is the local projection and its
`contracts.py` is the only supported cross-module read surface. Each domain module owns its
tables and migrations and cannot use cross-module foreign keys. The `placement` module is the
reference for permission manifests, selectors, services, API routes and client registration.

## PHC boundary and integration points

`modules.phc` owns patient enrollment references, doctor records and schedules, appointments,
consultations, prescriptions, inventory transactions and announcements. IAM sessions provide
the actor and permission set; `modules.directory.contracts.get_active_users()` validates institute
identities in a batched lookup. The shell mounts the module only when IAM grants the `phc`
module code. PHC does not write directory data or authenticate patients independently.

## Data design decisions

| Entity | Key relationships and constraints |
|---|---|
| Patient | Unique integer IAM `user_id`; unique PHC number; registering actor ID; no IAM FK |
| Doctor | Unique IAM `user_id`, specialty, availability; no IAM FK |
| DoctorSchedule | FK to Doctor; weekday, interval, slot length and effective dates |
| Appointment | FKs to Patient and Doctor; constrained status; unique doctor/time while not cancelled |
| AppointmentTransition | Append-only status audit with actor ID and reason |
| Consultation | One-to-one appointment; finalized clinical fields and recorder ID |
| Prescription / PrescribedMedicine | Consultation-owned issue and multiple medicine instructions |
| Medicine | Unique name, unit, aggregate quantity, low-stock threshold and expiry date |
| InventoryTransaction | Medicine FK, positive quantity, action and actor; optional patient integer ID |
| Announcement | Public-safe title/body, publisher ID and publication flag |

All timestamps use the shared timestamp mixin. The migration is additive and module-local.
There are no cross-module foreign keys. Appointment double booking is guarded by a conditional
database unique constraint as well as service validation. Inventory changes lock the medicine
row and update quantity and transaction history in one database transaction.

## Implemented workflows

- Patient self-enrollment and PHC staff enrollment of existing students, faculty and staff.
- Patient list scoping: patients see their own enrollment; authorized staff can see the directory.
- Doctor registration, availability changes, recurring weekly schedule setup and available-doctor
  listing.
- Appointment booking against future scheduled slots, pending/confirmed lifecycle, cancellation,
  status history, and a database uniqueness guard for concurrent requests.
- Consultation and prescription creation for the assigned doctor, with finalized records retained
  and a one-consultation-per-appointment constraint.
- Medicine creation, stock addition/dispensing, insufficient-stock and expired-stock rejection,
  and per-operation inventory history.
- Staff announcements, with read access limited to published notices for general members.

## API surface

All routes are under `/api/v1/phc/` and use the normal IAM session authentication and PHC module
grant. The endpoints are `patients`, `doctors`, `doctors/manage`, `doctors/<id>`, `schedules`,
`appointments`, `appointments/<id>/transition`, `consultations`,
`appointments/<id>/consultation`, `medicines`, `medicines/<id>/stock`, and `announcements`.

## Permission intent

| Actor grant | Access |
|---|---|
| student, faculty, staff | Own patient record, own appointments, appointment booking, published announcements |
| Doctor | Operational appointment and patient workflows; own assigned clinical records and prescriptions |
| Compounder | Patient enrollment, appointment management, inventory reading and announcements |
| PHC Admin | Doctor/staff operations, all clinical records, inventory management and announcements |

Role names are designation strings in the PHC registry and must be assigned to appropriate IAM
accounts before production activation. The registry remains `planned`; activation belongs after
IAM role seeding, deployment migration and operational review.

## Deliberate limitations and dependencies

- No employee/dependent relationship projection or HR contract exists here, so dependents are not
  enrollable. Adding them requires an authoritative relationship validation interface.
- The legacy `health_center` app is listed as deprecated, and the platform vision explicitly
  rejects porting deprecated applications. No legacy data or screens were copied.
- Medicine expiry is stored at medicine-record level, not per stock lot. Lot-level expiry and FIFO
  dispensing require a separate inventory batch model before multiple expiry batches of one
  medicine are operationally safe.
- Existing notification/outbox infrastructure is not part of the current module's smallest scope;
  appointment changes do not yet send notifications.
- Reimbursement, ambulance, referral, complaints, reports, PDF prescriptions and dispensing against
  a specific prescription are not implemented because there is no supporting PHC requirement or
  established integration contract in this repository.
- `openapi/fusion-integrated.v1.yaml` was regenerated with Django and passes spectacular
  validation with warnings treated as errors. The full `make schema-check` target remains to be run.
