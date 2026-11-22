# Visitors Hostel module blueprint

## Approval record

Status: awaiting Student 2 written approval before application code changes.

## Step 3.1 (a) - Traceability table

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| CFR-VH-001 | Controlled Indenter access to own booking status, history, details, confirmation and printing | API, selectors | `BookingListView`, `BookingDetailView`, `bookings_for`, `bookings_detailed` | Own-row scope only |
| CFR-VH-002 | Create standardized online booking in Pending state | domain, service, API | `RequisitionSerializer`, `domain.requisition.validate`, `submit_online`, `BookingListView` | |
| CFR-VH-003 | Caretaker review/routing and In-Charge final decision | domain, service, API | declarative state machine, `review`, `decide` | Forwarded rows are owned by the active duty holders |
| CFR-VH-004 | Record offline bookings through the same routing and availability rules | domain, service, API | `record_offline`, `BookingAvailabilityView` | Offline source must be telephonic or walk-in |
| CFR-VH-005 | Request booking modifications before arrival | domain, service, API | `ModificationRequestView`, `ModificationRequest` | Confirmation authority is unresolved |
| CFR-VH-006 | Pre-arrival cancellation and stated charge handling | domain, service, API | `domain.cancellation`, `CancellationRequestView`, `CancellationConfirmView` | |
| CFR-VH-007 | Allot rooms only after approval and maintain occupancy records | domain, service, API | `allot`, `RoomAllotment`, `BookingAllotView` | |
| CFR-VH-008 | Record check-in/check-out and no-show/overstay exceptions | service, scheduled task, API | `stays`, `scan_stays`, `send_stay_reminders` | |
| CFR-VH-009 | Maintain category and effective dated tariffs | domain, models, API | `tariffs`, `RoomTariff`, `MealTariff` | Historical bill snapshots required |
| CFR-VH-010 | Record guest meals for the stay and bill them | service, models, API | `MealBooking`, `record_meals`, bill generation | |
| CFR-VH-011 | Generate bills and record offline settlement and verification | service, models, API | `billing.generate`, `BillSettleView`, `BillVerifyView` | No online payment processing |
| CFR-VH-012 | Maintain inventory and threshold alerts | domain, service, API | `inventory`, `InventoryListView`, `InventoryAdjustView` | |
| CFR-VH-013 | Review/approve replenishment requirements | service, API | `ReplenishmentApproveView` | |
| CFR-VH-014 | Trigger booking, stay and inventory notifications | outbox, Celery, API-free service | `notifications`, beat schedule | Central delivery infrastructure is out of scope |
| CFR-VH-015 | In-Charge reports | selectors, API | `InChargeReportView`, `reports.py` | |
| CFR-VH-016 | Caretaker reports | selectors, API | `OperationsReportView`, `reports.py` | |
| CFR-VH-017 | Enforce active duty holders and time-bound reassignment | domain, service, scheduled task | `duty`, `vh_assign_duty`, `close_lapsed_duty` | Authority for reassignment is unresolved |
| CFR-VH-018 | Preserve visitor and system actor boundaries | API, architecture | no visitor login or VH system actor | |
| CFR-VH-019 | Preserve external-service and execution exclusions | architecture | no payment gateway, accounting, HR, procurement or central stock implementation | |
| CFR-VH-020 | Limit VH role assignment to VH access configuration | registry, IAM command usage | `registry.ROLE_GRANTS`, `vh_assign_duty` | No role administration table in the module |
| CFR-VH-021 | Preserve authoritative audit records | models, services | append-only transitions and bill lines | |
| CFR-VH-022 | Apply institute policies and integrity/role boundaries | domain, database, services | database constraints and permission gates | No dynamic discount/pricing |
| AFR-VH-001 | Indenter tracks own booking status/history | API, selectors | `BookingDetailView`, booking transitions | |
| AFR-VH-002 | Indenter views own booking details | API, selectors | `BookingDetailView` | |
| AFR-VH-003 | Indenter prints/exports own confirmed booking information | frontend/API | booking detail view plus printable UI | Final UI implementation required |
| AFR-VH-004 | Visitors have no direct VHMS account | architecture | no visitor auth route | |
| AFR-VH-005 | Standardized online booking | API, service | `RequisitionSerializer`, `submit_online` | |
| AFR-VH-006 | Capture required visitor and stay data | domain, API | requisition validation and model fields | |
| AFR-VH-007 | Capture permitted billing responsibility | domain, API | `BILLING_RESPONSIBILITIES`, `BR-VH-002` | |
| AFR-VH-008 | Submit only valid booking dates/counts | domain, database | `req.validate`, database constraints | |
| AFR-VH-009 | Place successful online request in Pending | state machine, service | `_create`, Pending state | |
| AFR-VH-010 | Authorized Indenter is required | IAM permission gate | `BOOKING_CREATE` | |
| AFR-VH-011 | Capture arrival/departure details | API, model | booking fields | |
| AFR-VH-012 | Capture room and occupant counts | API, model | booking fields and database constraints | |
| AFR-VH-013 | Confirmed request carries the Pending state | state machine | Pending transition audit | |
| AFR-VH-014 | Caretaker reviews pending requests | API, service | `review` | |
| AFR-VH-015 | Caretaker checks availability | selector, API | `available_rooms` | |
| AFR-VH-016 | Caretaker may reject directly | state machine | Caretaker reject transition | |
| AFR-VH-017 | Caretaker may forward | state machine | Caretaker forward transition | |
| AFR-VH-018 | In-Charge approves forwarded requests | state machine | In-Charge approve transition | |
| AFR-VH-019 | In-Charge rejects forwarded requests | state machine | In-Charge reject transition | |
| AFR-VH-020 | Final decision is communicated through notifications | outbox, Celery | `booking_event` | |
| AFR-VH-021 | Caretaker records telephonic/walk-in booking | API, service | `record_offline` | |
| AFR-VH-022 | Offline booking is flagged | model, API | `is_offline`, `source` | |
| AFR-VH-023 | Offline booking follows availability checking | service | `available_rooms` | |
| AFR-VH-024 | Offline booking follows approval routing | state machine | shared status machine | |
| AFR-VH-025 | Offline booking remains separately identifiable | database, API | source/offline fields | |
| AFR-VH-026 | Indenter can request modification before arrival | API, service | `ModificationRequestView` | |
| AFR-VH-027 | Indenter can request pre-arrival cancellation | API, service | `CancellationRequestView` | |
| AFR-VH-028 | Cancellation charge schedule is calculated | domain | `domain.cancellation` | |
| AFR-VH-029 | Cancellation 7+ days has 0 charge | domain | charge schedule | |
| AFR-VH-030 | 1-6 days has 25% | domain | charge schedule | |
| AFR-VH-031 | Same day has 50% | domain | charge schedule | |
| AFR-VH-032 | Caretaker confirms cancellation | service | `CancellationConfirmView` | |
| AFR-VH-033 | Cancellation billing is adjusted only after confirmation | service | cancellation effect | |
| AFR-VH-034 | Modification billing adjusts only after confirmed outcome | service | pending confirmation model | |
| AFR-VH-035 | Cancellation adjustment preserves immutable history | bill model | append-only bill lines | |
| AFR-VH-036 | Allotment only after approval | state/service guard | `allot` | |
| AFR-VH-037 | Maintain room allotment records | model | `RoomAllotment` | |
| AFR-VH-038 | Maintain occupancy record | model/API | occupancy field | |
| AFR-VH-039 | Maintain room type record | model/API | room type | |
| AFR-VH-040 | Release and availability behavior remains recorded | service | allotment data and availability selector | |
| AFR-VH-041 | Record check-in time | API/service | `check_in` | |
| AFR-VH-042 | Record check-out time | API/service | `check_out` | |
| AFR-VH-043 | Generate no-show alert | scheduled task | `scan_stays` | |
| AFR-VH-044 | Generate overstay alert | scheduled task | `scan_stays` | |
| AFR-VH-045 | Maintain visitor categories A-D | tariff/domain | category choices | |
| AFR-VH-046 | Maintain institute-defined tariffs | effective-dated model | RoomTariff | |
| AFR-VH-047 | Select applicable tariff for billing | billing service | tariff selector | |
| AFR-VH-048 | Protect historical bill from tariff edits | immutable bill snapshot | generated bill values | |
| AFR-VH-049 | Support effective category/occupancy tariff | domain/model | effective-dated version | |
| AFR-VH-050 | Avoid dynamic discount/pricing | billing domain | no unsupported discount | |
| AFR-VH-051 | Record meal bookings for VH guests | model/API | MealBooking | |
| AFR-VH-052 | Limit individual meal options | domain/database | `meals.PRICED_ITEMS` | |
| AFR-VH-053 | Limit add-ons to Tea and Milk | domain | meal choices | |
| AFR-VH-054 | Link meals to stay duration | service validation | stay-date guard | |
| AFR-VH-055 | Reflect room rent in bill | billing | bill room line | |
| AFR-VH-056 | Reflect meal consumption in bill | billing | bill meal line | |
| AFR-VH-057 | Reflect cancellation charges in bill | billing | cancellation line | |
| AFR-VH-058 | Support breakfast/lunch/dinner/add-ons | domain/API | meals | |
| AFR-VH-059 | Generate bill from room, meal and cancellation data | billing service | `generate_bill` | |
| AFR-VH-060 | Record billing responsibility | booking/bill model | responsibility fields | |
| AFR-VH-061 | Record offline cash settlement | bill model/API | settlement fields | |
| AFR-VH-062 | Support bill verification at checkout | API/service | `BillVerifyView` | |
| AFR-VH-063 | Preserve immutable billing history | database/service | bill record and append-only lines | |
| AFR-VH-064 | Billing summary reporting | selectors/API | report kinds | |
| AFR-VH-065 | Guest bill verification is recorded by Caretaker | API/service | verify endpoint | No visitor login |
| AFR-VH-066 | No online payment processing | architecture | out of scope | |
| AFR-VH-067 | No accounting ledger posting | architecture | out of scope | |
| AFR-VH-068 | Maintain inventory quantity and status | model/API | InventoryItem | |
| AFR-VH-069 | Maintain minimum threshold | model/API | threshold field | |
| AFR-VH-070 | Generate threshold alert below threshold | domain/task/API | inventory alert | |
| AFR-VH-071 | Allow caretaker inventory adjustment | API/service | `adjust_inventory` | |
| AFR-VH-072 | Preserve inventory audit | model/service | inventory adjustment audit | |
| AFR-VH-073 | Record replenishment requirements | model/API/service | ReplenishmentRequirement | |
| AFR-VH-074 | In-Charge approves requirement | API/service | approval endpoint | |
| AFR-VH-075 | Procurement/purchase execution excluded | architecture | out of scope | |
| AFR-VH-076 | Booking lifecycle notifications | outbox | `booking_event` | |
| AFR-VH-077 | Modification/cancellation notifications | outbox | booking events | |
| AFR-VH-078 | Stay reminders | scheduled task | `send_stay_reminders` | |
| AFR-VH-079 | No-show/overstay notifications | scheduled task/outbox | `stay_alert` | |
| AFR-VH-080 | Inventory threshold notifications | outbox/task | replenishment/threshold alert | |
| AFR-VH-081 | Central email delivery infrastructure excluded | architecture | local notification outbox only | |
| AFR-VH-082 | In-Charge booking report | API/selector | report kind | |
| AFR-VH-083 | In-Charge occupancy report | API/selector | report kind | |
| AFR-VH-084 | In-Charge revenue/billing summary | API/selector | report kind | |
| AFR-VH-085 | In-Charge inventory usage report | API/selector | report kind | |
| AFR-VH-086 | Caretaker daily occupancy report | API/selector | operations report | |
| AFR-VH-087 | Caretaker arrivals/departures report | API/selector | operations report | |
| AFR-VH-088 | Caretaker pending approval report | API/selector | operations report | |
| AFR-VH-089 | Caretaker no-show/overstay report | API/selector | operations report | |
| AFR-VH-090 | One active Caretaker | duty service/database | active assignment checks | |
| AFR-VH-091 | One active VH In-Charge | duty service/database | active assignment checks | |
| AFR-VH-092 | Time-bound assignments | duty model/service | effective/expiry fields and task | |
| AFR-VH-093 | Authorized reassignment applies immediately | duty service | assignment update | |
| AFR-VH-094 | Pending/ongoing records transfer | duty assignment fields and reassignment | in-charge/caretaker holders | |
| AFR-VH-095 | Reassignment remains audited | duty assignment audit | DutyAssignment rows | |
| AFR-VH-096 | VH-specific role assignment only | registry/IAM | no platform admin role grant | |
| AFR-VH-097 | No HR master data administration | architecture | no HR writes | |
| AFR-VH-098 | No platform account administration | architecture | no auth tables or account writes | |
| AFR-VH-099 | Booking is authoritative in VHMS | database/service | booking records | |
| AFR-VH-100 | Approval is authoritative/auditable | transition table | append-only transitions | |
| AFR-VH-101 | Room allotment is authoritative/auditable | allotment model | allotment rows | |
| AFR-VH-102 | Stay is authoritative/auditable | booking times/transition | timestamps | |
| AFR-VH-103 | Billing is authoritative/auditable | bill/bill lines | immutable history | |
| AFR-VH-104 | Inventory is authoritative/auditable | inventory/adjustments | audit fields | |
| AFR-VH-105 | Notification is authoritative/auditable | notification outbox | outbox rows | |
| AFR-VH-106 | Reassignment audit is preserved | duty assignments | effective-dated rows | |
| AFR-VH-107 | Institute norms only when represented | domain/configuration | effective policy values | |
| AFR-VH-108 | Effective tariff pricing | tariff model/billing | effective-dated tariff | |
| AFR-VH-109 | Role-bounded access and integrity | permission gates/scoping/constraints | every write/read | |
| AFR-VH-110 | System is not primary use-case actor | architecture | event-triggered tasks only | |
| AFR-VH-111 | Platform security responsibility excluded | architecture/IAM | no platform auth implementation | |
| AFR-VH-112 | Visitor has no direct login | architecture | no visitor portal route | |
| AFR-VH-113 | No dynamic discounts beyond tariffs | billing | tariff-only pricing | |
| AFR-VH-114 | Central notification infrastructure excluded | architecture | outbox only | |
| AFR-VH-115 | HR/payroll/procurement/physical services excluded | architecture | out of scope | |

Live UC rows: UC-VH-001 Submit Online Booking; UC-VH-002 Track/View/Print; UC-VH-003 Review/Route; UC-VH-004 Approve/Reject Forwarded; UC-VH-005 Offline Booking; UC-VH-006 Modification Request; UC-VH-007 Cancellation Request; UC-VH-008 Allot Rooms; UC-VH-009 Check-In; UC-VH-011-configuration provisional; UC-VH-012 Meals; UC-VH-013 Bill/Settlement; UC-VH-014 Inventory; UC-VH-015 Replenishment Approval; UC-VH-017 In-Charge Reports; UC-VH-018 Caretaker Reports; UC-VH-019 reassignment provisional; UC-VH-020 Cancellation Confirmation; UC-VH-021 Checkout/Verification; UC-VH-022 modification confirmation provisional; UC-VH-023 booking notifications; UC-VH-024 stay alerts; UC-VH-025 inventory threshold alert.

Live BR rows: BR-VH-002, 003, 004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014, 015, 016, 017, 018, 019, 023, 024, 025, 029, 030, 031, 032, 033, 034, 035, 036, 037, 041, 042, 043, 044, 047, 090, 091, 092, 093, 094, 095 from the synchronized registry. Retired/non-rule and superseded IDs are not live obligations.

Live workflow rows: BW-VH-01 Direct Rejection; BW-VH-02 Forwarded Approved; BW-VH-03 Forwarded Rejected; BW-VH-04 Offline Direct Rejection; BW-VH-05 Offline Forwarded Approved; BW-VH-06 Offline Forwarded Rejected; BW-VH-07 Cancellation 7-Day; BW-VH-08 Cancellation 25%; BW-VH-09 Cancellation 50%; BW-VH-10 Approved Stay; CW-VH-01 Composite Booking Approval; CW-VH-02 Composite Cancellation/Billing.

## Step 3.2 (b) - Domain model

- `Booking`: plain `indenter_user_id`, `recorded_by_user_id`, visitor/stay fields, effective billing responsibility, status, active Caretaker/In-Charge owner, check-in/out timestamps.
- `BookingTransition`: append-only status and confirmed modification audit.
- `CancellationRequest`: one-to-one booking request, charge schedule snapshot, confirmation actor/time.
- `ModificationRequest`: booking changes and previous snapshot, confirmation actor/time.
- `Room`, `RoomAllotment`, `RoomTariff`, `MealTariff`, `MealBooking`.
- `Bill`, `BillLine`: immutable generated totals and offline settlement/checkout verification fields.
- `InventoryItem`, `InventoryAdjustment`, `ReplenishmentRequirement`.
- `DutyAssignment`, `StayAlert`, `NotificationOutbox`.

Database invariants include status and category/occupancy choices, departure >= arrival, positive counts, offline/source consistency, online has an Indenter, checked-in/out timestamp consistency, charge non-negativity, one active duty role, effective tariff uniqueness and immutable bill protection.

## Step 3.3 (c) - State machine

The implementation will use `domain/state_machine.py`'s declarative transition table for booking states and actor lanes. States include Pending, Forwarded, Approved, Rejected, Room Allotted, Checked In and Checked Out. Illegal transitions and actor mismatches are resolved through one transition choke point and cannot be bypassed.

## Step 3.4 (d) - Permission list

The module grants only VH operational designations:

- Indenters: `student`, `faculty`, `staff`
- Caretaker: `VhCaretaker`
- VH In-Charge: `VhIncharge`

Permission strings use the closed `create/view/manage/approve/review/update/settle/verify/allocate/check` list as appropriate. `SYSTEM_PERMISSIONS` covers unresolved authority actions and scheduled work. `SCOPE_PERMISSIONS` contains `visitor_hostel.booking.view`; selected-read scoping must return 404 for out-of-scope row ids.

The exact `registry.py` content is the authoritative implementation detail and will include no auth/user-role models.

## Step 3.5 (e) - API and frontend

- Mount backend at `/api/v1/visitorhostel/`.
- React routes under `/visitorhostel/*`, guarded by exact module permissions.
- Indenter pages: booking form and own bookings/details.
- Caretaker pages: review queue, offline booking, allotment/stays, billing, inventory, operations reports.
- VH In-Charge pages: forwarded decisions, replenishment approval, reports.

## Step 3.6 (f) - Scheduled operations

Celery beat will deliver the notification outbox, scan no-show/overstay conditions every 15 minutes, send daily stay reminders, and close lapsed duty assignments.

## Step 3.7 (g) - Testing

- Existing module unit/integration tests will remain under `modules/visitor_hostel/tests/` and be supplemented for any uncovered live rule.
- Student 2 will freeze independent FR/UC/BR/WF designs under `docs/P-01-visitor_hostel/spec-tests/`, then executable spec tests under `modules/visitor_hostel/tests/spec/`.
- Frontend Vitest and Playwright coverage will exercise role routes and core flows.

## Step 3.8 (h) - Known gaps and approvals

Open until approved:

1. UC-VH-011: tariff configuration authority is not established.
2. UC-VH-019: operational role reassignment authority is not established.
3. UC-VH-022: confirmed modification authority is not established.
4. Visitor category/tariff policy values are institute-defined inputs, not invented values.
5. Shared-file changes will be limited to module registration, URL mounting, Celery assembly, frontend registry/routes and generated schema/permissions files.
6. No new dependency is planned.

The implementation will provide no-op/guarded behavior for unresolved authority where the existing module deliberately keeps the permission system-only, and will not invent a role or decision authority.
