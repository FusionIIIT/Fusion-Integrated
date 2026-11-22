# Visitor Hostel Blueprint

**Module Name:** Visitors Hostel Management System (VHMS)  
**Module Code:** `visitor_hostel`  
**Docs Number (NN):** `09`  
**Spec ID Prefix:** `VH-` (`AFR-VH-`, `CFR-VH-`, `UC-VH-`, `BR-VH-`, `BW-VH-` / `WF-VH-`)  
**Environment:** `module-only`  
**Approved by Student 2 (in writing):** Abhay Kumar Singh on 2026-11-20 (Approved as part of Phase 2 gate).

---

## Step 3.1 (a) — Traceability Table

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| `AFR-VH-001` | Indenter submits online hostel booking request | API / Domain | `views.BookingRequestViewSet.create`, `models.BookingRequest` | Enforces IAM identity scoping, sets initial status to `pending`. |
| `AFR-VH-002` | Indenter views only their own booking requests | Selector / Scoping | `views.BookingRequestViewSet.get_queryset` | Filtered strictly by `indenter_id == request.user.user_id`. |
| `AFR-VH-003` | Access requires module grant and active institute identity | Authorization | `permissions.HasHostelModuleGrant` | Checks IAM token active modules and kind. |
| `AFR-VH-004` | Caretaker/In-Charge staff actions restricted from standard users | Authorization | `permissions.HasHostelRole` | Staff endpoints require active caretaker or in-charge role. |
| `AFR-VH-005` | Indenter lists submitted bookings | Selector | `views.BookingRequestViewSet.list` | Paginated, scoped list of user's own bookings. |
| `AFR-VH-006` | Anonymous unauthenticated access blocked | Authentication | Global DRF / `IsAuthenticated` | 401 Unauthorized for missing/invalid credentials. |
| `AFR-VH-007` | Mass-assignment of internal workflow fields blocked | Serializer | `serializers.BookingRequestSerializer` | Fields `status`, `indenter_id`, `is_offline` marked `read_only`. |
| `AFR-VH-008` | Requisition input validation (dates, occupancy, room counts) | Serializer / Model | `serializers.BookingRequestSerializer.validate`, DB constraints | Positive room/occupant count, check-out after check-in, valid category. |
| `AFR-VH-009` | Arrival and departure planned times persistence | Model / DB | `models.BookingRequest.check_in_time`, `check_out_time` | Stored as TimeField. |
| `AFR-VH-010` | Explicit occupant count tracked | Model / DB | `models.BookingRequest.number_of_occupants` | Positive integer, validates room occupancy capacity. |
| `AFR-VH-011` | Caretaker offline booking entry | API / Domain | `views.BookingRequestViewSet.offline` | Direct booking creation by caretaker for walk-in/paper indenters. |
| `BR-VH-001` | Time-bound role appointments | Domain / IAM | `models.RoleAssignment`, `permissions.HasHostelRole` | Appointment date bounds strictly checked; expired grants revoked. |
| `BR-VH-002` | Single active operator per staff role | Model / DB | `models.RoleAssignment.save`, DB UniqueConstraint | Re-assignment immediately revokes prior operator access. |
| `BR-VH-004` | Forwarding requires available capacity | Domain Service | `services.validate_capacity_for_forward` | Rejects forward action if inventory of requested room type is zero. |
| `BR-VH-009` | No-show detection and penalty assessment | Celery Task / Service | `tasks.generate_alerts`, `views.BookingRequestViewSet.no_show` | Daily beat task alerts caretaker; no-show assessed 50% 1-day rate. |
| `BR-VH-011` | Tiered cancellation charges | Domain Service | `services.cancellation_charge` | >=7 days: 0%; 1-6 days: 25%; same-day/no-show: 50% of first night rate. |
| `BR-VH-015` | Booking modification requires caretaker review | Domain Service | `views.BookingRequestViewSet.modify` | Puts request into modification state; releases room allotment upon approval. |
| `BR-VH-023` | Tariff effective on check-in arrival date | Domain Service | `services.tariff_for` | Resolves applicable rate with `effective_from <= check_in_date`. |
| `BR-VH-024` | Meals only available for current residents | Domain / API | `views.BookingRequestViewSet.meals` | Booking status must be `checked_in`. |
| `BR-VH-025` | Meals date within stay bounds and non-negative rate | Model / Validation | `models.MealBooking.clean` | Validates date in stay range and positive rate. |
| `BR-VH-031` | Atomic checkout with required tariff | Domain / DB | `services.generate_checkout_bill`, `views.BookingRequestViewSet.check_out` | All-or-nothing checkout in `@transaction.atomic`; fails safely without tariff. |
| `BR-VH-035` | Bill immutability | Model / DB | `models.Bill.clean`, DB trigger / immutable constraint | Generated bill amounts cannot be repriced or deleted. |
| `BR-VH-041` | Strict inventory replenishment threshold | Model / Service | `models.InventoryItem.is_below_threshold` | Strict less-than (`quantity < minimum_threshold`). |
| `BR-VH-043` | Idempotent notification delivery | Celery Task | `tasks.deliver_notifications` | Deduplicated queue with exponential backoff on failure. |
| `UC-VH-001` | Complete guest stay lifecycle | Multi-layer | Full Booking to Checkout workflow | Online submission -> routing -> approval -> allotment -> checkin -> checkout -> cash settlement. |
| `UC-VH-008` | Inventory replenishment workflow | Domain / API | `views.InventoryViewSet.replenish` | Caretaker requests replenishment; only in-charge can approve. |
| `BW-VH-01` | Two-stage approval sequencing | State Machine | `models.BookingRequest.route`, `models.BookingRequest.decide` | Indenter -> Caretaker Forward -> In-Charge Approve. |
| `BW-VH-02` | Availability check before forward | State Machine | `views.BookingRequestViewSet.route` | Caretaker must confirm capacity before forwarding. |
| `BW-VH-03` | Rejection requires reason | State Machine | `views.BookingRequestViewSet.route`, `decide` | Non-empty reason mandatory on rejection. |
| `BW-VH-04` | Atomic room allotment | Domain Service | `services.allot_rooms` | Room list validation, duplicate checks, transaction rollback. |
| `BW-VH-05` | Conflicting allotment blocking | DB / Lock | `services.allot_rooms`, `models.RoomAllotment` | Select for update row locking prevents concurrent double-booking. |
| `BW-VH-06` | Check-in/out state guards | State Machine | `models.BookingRequest.check_in`, `check_out` | Must be `confirmed` for check-in; `checked_in` for check-out. |
| `BW-VH-07` | Partial allotment rollback | Domain / DB | `services.allot_rooms` | If any room in request fails, all revert atomically. |
| `BW-VH-08` | Maintenance room restriction | Domain / Validation | `models.RoomAllotment.clean` | Room with status `maintenance` cannot be allotted. |

---

## Step 3.2 (b) — Domain Model

### Entities & Relationships
1. **`Room`**:
   - `room_number`: string (Unique, e.g. `VH-101`)
   - `room_type`: `single`, `double`, `suite`
   - `status`: `available`, `occupied`, `maintenance`
   - Invariants: Cannot allot if in `maintenance` or already occupied for overlapping dates.
2. **`VisitorCategoryTariff`**:
   - `category`: `A`, `B`, `C`, `D`
   - `room_type`: `single`, `double`, `suite`
   - `occupancy`: `single`, `double`
   - `daily_rate`: Decimal(10, 2) (> 0)
   - `effective_from`: Date (defaults to today)
   - Constraint: `UniqueConstraint(fields=['category', 'room_type', 'occupancy', 'effective_from'])`
3. **`BookingRequest`**:
   - `indenter_id`: BigInteger (IAM user_id; null if offline)
   - `legacy_indenter_id`: Integer (for legacy migrations)
   - `visitor_name`: string
   - `visitor_category`: `A`, `B`, `C`, `D`
   - `purpose`: text
   - `check_in_date`, `check_out_date`: Date (check_out > check_in)
   - `check_in_time`, `check_out_time`: Time (defaults to standard 12:00)
   - `room_type`: `single`, `double`, `suite`
   - `occupancy`: `single`, `double`
   - `number_of_rooms`: Integer (>= 1)
   - `number_of_occupants`: Integer (>= 1)
   - `billing_responsibility`: `Institute`, `Project`, `Visitor`
   - `status`: `pending`, `forwarded`, `approved`, `rejected`, `confirmed`, `checked_in`, `checked_out`, `cancelled`
   - `is_offline`: Boolean
   - Constraints: `CheckConstraint(check=Q(number_of_rooms__gt=0))`
4. **`RoomAllotment`**:
   - `booking`: ForeignKey to `BookingRequest`
   - `room`: ForeignKey to `Room`
   - `actual_check_in`: DateTime (null until check-in)
   - `actual_check_out`: DateTime (null until check-out)
   - Constraint: `UniqueConstraint(fields=['booking', 'room'])`
5. **`MealBooking`**:
   - `booking`: ForeignKey to `BookingRequest`
   - `date`: Date (must fall between check_in and check_out)
   - `meal_type`: `breakfast`, `lunch`, `dinner`
   - `quantity`: Integer (>= 1)
   - `rate`: Decimal(10, 2) (>= 0)
6. **`Bill`**:
   - `booking`: OneToOneField to `BookingRequest`
   - `room_charge`: Decimal(10, 2)
   - `meal_charge`: Decimal(10, 2)
   - `cancellation_charge`: Decimal(10, 2)
   - `total_amount`: Decimal(10, 2)
   - `is_settled_offline`: Boolean
   - `settlement_date`: DateTime
   - `receipt_number`: string
   - `is_immutable`: Boolean (True once saved)
7. **`InventoryItem`**:
   - `name`: string (Unique)
   - `quantity`: Integer (>= 0)
   - `minimum_threshold`: Integer (>= 0)
8. **`InventoryReplenishment`**:
   - `item`: ForeignKey to `InventoryItem`
   - `requested_quantity`: Integer (> 0)
   - `status`: `pending`, `approved`, `rejected`
9. **`RoleAssignment`**:
   - `role`: `vh_caretaker`, `vh_in_charge` (Unique per role)
   - `user_id`: BigInteger
   - `email`: string
   - `starts_at`, `ends_at`: DateTime
10. **`Notification`**:
    - `event`: string
    - `recipient_role`: string
    - `booking`: ForeignKey to `BookingRequest` (optional)
    - `delivered_at`: DateTime (null until sent)
    - `attempts`: Integer

---

## Step 3.3 (c) — Declarative State Machine

| Current State | Event | Actor | Next State | Condition |
|---|---|---|---|---|
| *None* | `submit_online` | `student`, `faculty`, `staff` | `pending` | Valid payload |
| *None* | `submit_offline` | `vh_caretaker` | `pending` | Valid payload, `is_offline=True` |
| `pending` | `forward` | `vh_caretaker` | `forwarded` | Capacity available for room type |
| `pending` | `reject` | `vh_caretaker` | `rejected` | Non-empty rejection reason |
| `pending` | `cancel` | `owner` / `vh_caretaker` | `cancelled` | Booking cancelled |
| `forwarded` | `approve` | `vh_in_charge` | `approved` | Capacity confirmed |
| `forwarded` | `reject` | `vh_in_charge` | `rejected` | Non-empty rejection reason |
| `approved` | `allot_rooms` | `vh_caretaker` | `confirmed` | All requested rooms assigned & available |
| `confirmed` | `check_in` | `vh_caretaker` | `checked_in` | Current time within stay interval |
| `confirmed` | `cancel_request`| `owner` | `confirmed` | Needs caretaker confirmation |
| `confirmed` | `cancel_confirm`| `vh_caretaker` | `cancelled` | Releases allotments; applies cancellation charge |
| `confirmed` | `no_show` | `vh_caretaker` | `cancelled` | Date past arrival; assesses 50% 1-day tariff |
| `checked_in` | `check_out` | `vh_caretaker` | `checked_out` | Generates immutable bill, releases rooms |
| `checked_out`| `settle_cash` | `vh_caretaker` | `checked_out` | Marks bill settled, logs receipt |

---

## Step 3.4 (d) — Permission List & RBAC

```python
MODULE = "visitor_hostel"

PERMISSIONS = (
    "visitor_hostel.booking.request",
    "visitor_hostel.booking.manage",
    "visitor_hostel.booking.approve",
    "visitor_hostel.inventory.manage",
    "visitor_hostel.inventory.approve",
    "visitor_hostel.tariff.manage",
)

ROLE_GRANTS = {
    "student": ("visitor_hostel.booking.request",),
    "faculty": ("visitor_hostel.booking.request",),
    "staff": ("visitor_hostel.booking.request",),
    "vh_caretaker": (
        "visitor_hostel.booking.request",
        "visitor_hostel.booking.manage",
        "visitor_hostel.inventory.manage",
    ),
    "vh_in_charge": (
        "visitor_hostel.booking.request",
        "visitor_hostel.booking.approve",
        "visitor_hostel.inventory.approve",
        "visitor_hostel.tariff.manage",
    ),
}
```

---

## Step 3.5 (e) — Endpoint List

- `POST /api/v1/visitor-hostel/bookings/`: Submit online booking request (`visitor_hostel.booking.request`)
- `GET /api/v1/visitor-hostel/bookings/`: List own/managed booking requests (`visitor_hostel.booking.request`)
- `GET /api/v1/visitor-hostel/bookings/{id}/`: Retrieve booking details (Owner or Caretaker/In-Charge)
- `POST /api/v1/visitor-hostel/bookings/offline/`: Create offline booking (`visitor_hostel.booking.manage`)
- `POST /api/v1/visitor-hostel/bookings/{id}/route/`: Caretaker forward or reject (`visitor_hostel.booking.manage`)
- `POST /api/v1/visitor-hostel/bookings/{id}/decision/`: In-Charge approve or reject (`visitor_hostel.booking.approve`)
- `POST /api/v1/visitor-hostel/bookings/{id}/allot/`: Allot rooms to approved booking (`visitor_hostel.booking.manage`)
- `POST /api/v1/visitor-hostel/bookings/{id}/check-in/`: Check-in guest (`visitor_hostel.booking.manage`)
- `POST /api/v1/visitor-hostel/bookings/{id}/check-out/`: Check-out guest and generate bill (`visitor_hostel.booking.manage`)
- `POST /api/v1/visitor-hostel/bookings/{id}/cancel/`: Request cancellation (`visitor_hostel.booking.request`)
- `POST /api/v1/visitor-hostel/bookings/{id}/cancel/confirm/`: Confirm cancellation (`visitor_hostel.booking.manage`)
- `POST /api/v1/visitor-hostel/bookings/{id}/no-show/`: Record no-show (`visitor_hostel.booking.manage`)
- `POST /api/v1/visitor-hostel/bookings/{id}/modify/`: Request booking modification (`visitor_hostel.booking.request`)
- `POST /api/v1/visitor-hostel/bookings/{id}/modify/decision/`: Caretaker decide modification (`visitor_hostel.booking.manage`)
- `POST /api/v1/visitor-hostel/bookings/{id}/meals/`: Record meal consumption (`visitor_hostel.booking.manage`)
- `POST /api/v1/visitor-hostel/bookings/{id}/settle/`: Offline cash settlement (`visitor_hostel.booking.manage`)
- `GET /api/v1/visitor-hostel/rooms/`: List hostel rooms (`visitor_hostel.booking.manage`)
- `GET /api/v1/visitor-hostel/tariffs/`: List tariffs (`visitor_hostel.booking.request`)
- `POST /api/v1/visitor-hostel/tariffs/`: Configure new tariff (`visitor_hostel.tariff.manage`)
- `GET /api/v1/visitor-hostel/inventory/`: List inventory items (`visitor_hostel.inventory.manage`)
- `POST /api/v1/visitor-hostel/inventory/`: Add inventory item (`visitor_hostel.inventory.manage`)
- `POST /api/v1/visitor-hostel/inventory/replenish/`: Request replenishment (`visitor_hostel.inventory.manage`)
- `POST /api/v1/visitor-hostel/inventory/replenish/{id}/decision/`: Decide replenishment (`visitor_hostel.inventory.approve`)
- `GET /api/v1/visitor-hostel/reports/`: Executive and occupancy reporting (`visitor_hostel.booking.approve`)

### Sidebar Entry for `Fusion-client`
```json
{
  "id": "visitor_hostel",
  "label": "Visitor Hostel",
  "icon": "BuildingOffice2Icon",
  "to": "/visitor-hostel",
  "section": "Services"
}
```

---

## Step 3.6 (f) — Public Contracts

Exported in `modules/visitor_hostel/contracts.py`:
- `get_booking_summaries(booking_ids: Sequence[int]) -> dict[int, BookingSummaryDTO]`
- `get_hostel_no_dues_clearances(user_ids: Sequence[int]) -> dict[int, HostelNoDuesClearanceDTO]`

All getters accept plural `Sequence[int]` to eliminate N+1 queries.

---

## Step 3.7 (g) — Scheduled Work (Celery Beat)

1. `vh-no-show-overstay-alerts`: Runs daily at 02:00. Scans bookings where current time exceeds check-in without arrival (no-show alert) or exceeds check-out without departure (overstay alert).
   - Real-world impact if not run: Unattended rooms remain indefinitely reserved or occupied; revenue leakage and unalerted operational delays occur.
2. `vh-deliver-notifications`: Runs every 5 minutes. Drains the outbox table with idempotent retry backoff.
   - Real-world impact if not run: Requisition and approval notifications are delayed, slowing down administrative approval workflows.

---

## Step 3.8 (h) — Open Questions & Approvals

1. **Role Appointment Scoping:** Approved to model `RoleAssignment` locally with time bounds, synced with IAM designation grants.
2. **Bill Immutability:** Approved to enforce immutable bills with database and model validations to prevent post-checkout tampering.
3. **Cancellation Tier Calculations:** Approved 3-tier boundary (>=7 days 0%, 1-6 days 25%, same-day 50%) based on first night rate multiplied by room count.

