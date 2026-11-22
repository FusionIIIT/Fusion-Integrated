# Visitors Hostel Management System (VHMS) — Live Specification Reference

This reference table maps every live requirement, business rule, use case, and workflow
to its verified enforcement point in the codebase.

| Specification ID | Description | Source File | Enforcement Line |
|---|---|---|---|
| **CFR-VH-001** | Indenter booking tracking | [`modules/vh/selectors/bookings.py`](../../modules/vh/selectors/bookings.py#L1) | Line 1 |
| **AFR-VH-001** | Track status and history | [`modules/vh/selectors/bookings.py`](../../modules/vh/selectors/bookings.py#L1) | Line 1 |
| **AFR-VH-002** | View booking and confirmation details | [`modules/vh/selectors/bookings.py`](../../modules/vh/selectors/bookings.py#L32) | Line 32 |
| **AFR-VH-003** | Printable booking details view | [`modules/vh/api/views.py`](../../modules/vh/api/views.py#L1) | Line 1 |
| **CFR-VH-002** | Online booking creation | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L35) | Line 35 |
| **AFR-VH-005** | Standardized online requisition form | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L35) | Line 35 |
| **AFR-VH-006** | Record visitor details | [`modules/vh/models/visitor.py`](../../modules/vh/models/visitor.py#L7) | Line 7 |
| **AFR-VH-007** | Record purpose of visit | [`modules/vh/models/booking.py`](../../modules/vh/models/booking.py#L26) | Line 26 |
| **AFR-VH-008** | Category classification A, B, C, D | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L46) | Line 46 |
| **AFR-VH-009** | Arrival and departure dates validation | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L70) | Line 70 |
| **AFR-VH-010** | Record room count and occupants | [`modules/vh/models/booking.py`](../../modules/vh/models/booking.py#L31) | Line 31 |
| **AFR-VH-011** | Record billing responsibility | [`modules/vh/models/booking.py`](../../modules/vh/models/booking.py#L33) | Line 33 |
| **AFR-VH-012** | Restricted billing responsibility | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L37) | Line 37 |
| **AFR-VH-013** | Initial status Pending on submission | [`modules/vh/domain/state_machine.py`](../../modules/vh/domain/state_machine.py#L1) | Line 1 |
| **CFR-VH-003** | Booking review and routing | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L1) | Line 1 |
| **AFR-VH-014** | Caretaker reviews pending bookings | [`modules/vh/selectors/bookings.py`](../../modules/vh/selectors/bookings.py#L1) | Line 1 |
| **AFR-VH-015** | Room availability check | [`modules/vh/services/inventory.py`](../../modules/vh/services/inventory.py#L1) | Line 1 |
| **AFR-VH-016** | Caretaker direct rejection | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L1) | Line 1 |
| **AFR-VH-017** | Caretaker forwarding to In-Charge | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L1) | Line 1 |
| **AFR-VH-018** | In-Charge approves booking | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L1) | Line 1 |
| **AFR-VH-019** | In-Charge rejects booking | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L1) | Line 1 |
| **AFR-VH-020** | Decision notification to indenter | [`modules/vh/services/notifications.py`](../../modules/vh/services/notifications.py#L26) | Line 26 |
| **CFR-VH-004** | Offline telephonic / walk-in booking | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L102) | Line 102 |
| **AFR-VH-021** | Telephonic booking entry | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L102) | Line 102 |
| **AFR-VH-022** | Walk-in booking entry | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L102) | Line 102 |
| **AFR-VH-023** | Identical routing state machine for offline bookings | [`modules/vh/domain/state_machine.py`](../../modules/vh/domain/state_machine.py#L1) | Line 1 |
| **AFR-VH-024** | Same availability check for offline bookings | [`modules/vh/services/inventory.py`](../../modules/vh/services/inventory.py#L1) | Line 1 |
| **AFR-VH-025** | Offline booking flag for audit | [`modules/vh/models/booking.py`](../../modules/vh/models/booking.py#L13) | Line 13 |
| **CFR-VH-005** | Pre-arrival modification handling | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L253) | Line 253 |
| **AFR-VH-026** | Indenter pre-arrival modification | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L253) | Line 253 |
| **AFR-VH-034** | Adjust billing info on modification | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **CFR-VH-006** | Pre-arrival cancellation handling | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L171) | Line 171 |
| **AFR-VH-027** | Indenter pre-arrival cancellation request | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L171) | Line 171 |
| **AFR-VH-028** | Calculate cancellation charge | [`modules/vh/domain/cancellation.py`](../../modules/vh/domain/cancellation.py#L1) | Line 1 |
| **AFR-VH-029** | 0% charge at 7 days before arrival | [`modules/vh/domain/cancellation.py`](../../modules/vh/domain/cancellation.py#L1) | Line 1 |
| **AFR-VH-030** | 25% charge within 7 days | [`modules/vh/domain/cancellation.py`](../../modules/vh/domain/cancellation.py#L1) | Line 1 |
| **AFR-VH-031** | 50% charge same day or no-show | [`modules/vh/domain/cancellation.py`](../../modules/vh/domain/cancellation.py#L1) | Line 1 |
| **AFR-VH-032** | Caretaker reviews cancellation requests | [`modules/vh/selectors/bookings.py`](../../modules/vh/selectors/bookings.py#L1) | Line 1 |
| **AFR-VH-033** | Caretaker confirms cancellation | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L174) | Line 174 |
| **AFR-VH-035** | Bill generation for cancellation charges | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **CFR-VH-007** | Room allotment and occupancy | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L1) | Line 1 |
| **AFR-VH-036** | Room allotment only after approval | [`modules/vh/domain/state_machine.py`](../../modules/vh/domain/state_machine.py#L1) | Line 1 |
| **AFR-VH-037** | Single occupancy support | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L62) | Line 62 |
| **AFR-VH-038** | Double occupancy support | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L62) | Line 62 |
| **AFR-VH-039** | Suite room support | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L54) | Line 54 |
| **AFR-VH-040** | Non-suite room support | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L54) | Line 54 |
| **CFR-VH-008** | Check-in, checkout and exceptions | [`modules/vh/services/stays.py`](../../modules/vh/services/stays.py#L1) | Line 1 |
| **AFR-VH-041** | Record check-in time | [`modules/vh/services/stays.py`](../../modules/vh/services/stays.py#L1) | Line 1 |
| **AFR-VH-042** | Record checkout time | [`modules/vh/services/stays.py`](../../modules/vh/services/stays.py#L1) | Line 1 |
| **AFR-VH-043** | No-show alert generation | [`modules/vh/services/alerts.py`](../../modules/vh/services/alerts.py#L11) | Line 11 |
| **AFR-VH-044** | Overstay alert generation | [`modules/vh/services/alerts.py`](../../modules/vh/services/alerts.py#L34) | Line 34 |
| **CFR-VH-009** | Visitor categories and tariff structure | [`modules/vh/domain/tariffs.py`](../../modules/vh/domain/tariffs.py#L1) | Line 1 |
| **AFR-VH-045** | Visitor category classification A, B, C, D | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L46) | Line 46 |
| **AFR-VH-046** | Category-specific tariffs | [`modules/vh/models/tariff.py`](../../modules/vh/models/tariff.py#L9) | Line 9 |
| **AFR-VH-047** | Occupancy-specific tariffs | [`modules/vh/models/tariff.py`](../../modules/vh/models/tariff.py#L10) | Line 10 |
| **AFR-VH-048** | Effective dates for tariffs | [`modules/vh/models/tariff.py`](../../modules/vh/models/tariff.py#L25) | Line 25 |
| **AFR-VH-049** | Automatic tariff selection during billing | [`modules/vh/selectors/tariffs.py`](../../modules/vh/selectors/tariffs.py#L19) | Line 19 |
| **AFR-VH-050** | Tariff changes immutable against historical bills | [`modules/vh/domain/tariffs.py`](../../modules/vh/domain/tariffs.py#L1) | Line 1 |
| **CFR-VH-010** | Mess management and meal bookings | [`modules/vh/services/meals.py`](../../modules/vh/services/meals.py#L15) | Line 15 |
| **AFR-VH-051** | Meal bookings restricted to active stay | [`modules/vh/services/meals.py`](../../modules/vh/services/meals.py#L15) | Line 15 |
| **AFR-VH-052** | Full-day meal option support | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L1) | Line 1 |
| **AFR-VH-053** | Individual meal option support | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L1) | Line 1 |
| **AFR-VH-054** | Add-on meal option support | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L1) | Line 1 |
| **AFR-VH-055** | Breakfast, Lunch, Dinner restriction | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L1) | Line 1 |
| **AFR-VH-056** | Tea, Milk add-on restriction | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L1) | Line 1 |
| **AFR-VH-057** | Meal booking within stay duration | [`modules/vh/services/meals.py`](../../modules/vh/services/meals.py#L15) | Line 15 |
| **AFR-VH-058** | Meal charges reflected in billing | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **CFR-VH-011** | Billing and settlement | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **AFR-VH-059** | Room rent line items | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **AFR-VH-060** | Meal charges line items | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **AFR-VH-061** | Cancellation charge line items | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **AFR-VH-062** | Record billing responsibility on bill | [`modules/vh/models/bill.py`](../../modules/vh/models/bill.py#L21) | Line 21 |
| **AFR-VH-063** | Offline cash payment mode | [`modules/vh/models/bill.py`](../../modules/vh/models/bill.py#L73) | Line 73 |
| **AFR-VH-064** | Record offline cash settlement | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **AFR-VH-065** | Caretaker records bill verification | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **AFR-VH-066** | Immutable settled bills | [`modules/vh/models/bill.py`](../../modules/vh/models/bill.py#L1) | Line 1 |
| **CFR-VH-012** | Inventory and threshold control | [`modules/vh/services/inventory.py`](../../modules/vh/services/inventory.py#L12) | Line 12 |
| **AFR-VH-068** | Caretaker maintains inventory | [`modules/vh/services/inventory.py`](../../modules/vh/services/inventory.py#L12) | Line 12 |
| **AFR-VH-069** | Support consumables, linen, utensils | [`modules/vh/models/inventory.py`](../../modules/vh/models/inventory.py#L10) | Line 10 |
| **AFR-VH-070** | Record current quantity | [`modules/vh/models/inventory.py`](../../modules/vh/models/inventory.py#L21) | Line 21 |
| **AFR-VH-071** | Record minimum threshold | [`modules/vh/models/inventory.py`](../../modules/vh/models/inventory.py#L22) | Line 22 |
| **AFR-VH-072** | Alert on stock below threshold | [`modules/vh/services/inventory.py`](../../modules/vh/services/inventory.py#L12) | Line 12 |
| **CFR-VH-013** | Inventory replenishment review | [`modules/vh/services/inventory.py`](../../modules/vh/services/inventory.py#L104) | Line 104 |
| **AFR-VH-073** | In-Charge reviews requests | [`modules/vh/selectors/inventory.py`](../../modules/vh/selectors/inventory.py#L1) | Line 1 |
| **AFR-VH-074** | In-Charge approves replenishment | [`modules/vh/services/inventory.py`](../../modules/vh/services/inventory.py#L104) | Line 104 |
| **CFR-VH-014** | Notification services | [`modules/vh/services/notifications.py`](../../modules/vh/services/notifications.py#L9) | Line 9 |
| **AFR-VH-076** | Booking submission notification | [`modules/vh/services/notifications.py`](../../modules/vh/services/notifications.py#L9) | Line 9 |
| **AFR-VH-077** | Decision notification to indenter | [`modules/vh/services/notifications.py`](../../modules/vh/services/notifications.py#L26) | Line 26 |
| **AFR-VH-078** | Cancellation notification | [`modules/vh/services/notifications.py`](../../modules/vh/services/notifications.py#L42) | Line 42 |
| **AFR-VH-079** | Stay reminders | [`modules/vh/services/notifications.py`](../../modules/vh/services/notifications.py#L1) | Line 1 |
| **AFR-VH-080** | Low stock notification | [`modules/vh/services/notifications.py`](../../modules/vh/services/notifications.py#L57) | Line 57 |
| **CFR-VH-015** | In-Charge reporting | [`modules/vh/selectors/reports.py`](../../modules/vh/selectors/reports.py#L100) | Line 100 |
| **AFR-VH-082** | Booking summary metrics | [`modules/vh/selectors/reports.py`](../../modules/vh/selectors/reports.py#L100) | Line 100 |
| **AFR-VH-083** | Category-wise occupancy | [`modules/vh/selectors/reports.py`](../../modules/vh/selectors/reports.py#L112) | Line 112 |
| **AFR-VH-084** | Revenue and billing summary | [`modules/vh/selectors/reports.py`](../../modules/vh/selectors/reports.py#L122) | Line 122 |
| **AFR-VH-085** | Inventory usage summary | [`modules/vh/selectors/reports.py`](../../modules/vh/selectors/reports.py#L142) | Line 142 |
| **CFR-VH-016** | Caretaker operational reporting | [`modules/vh/selectors/reports.py`](../../modules/vh/selectors/reports.py#L14) | Line 14 |
| **AFR-VH-086** | Daily occupancy report | [`modules/vh/selectors/reports.py`](../../modules/vh/selectors/reports.py#L14) | Line 14 |
| **AFR-VH-087** | Arrivals and departures report | [`modules/vh/selectors/reports.py`](../../modules/vh/selectors/reports.py#L39) | Line 39 |
| **AFR-VH-088** | Pending approvals report | [`modules/vh/selectors/reports.py`](../../modules/vh/selectors/reports.py#L70) | Line 70 |
| **AFR-VH-089** | No-show and overstay logs | [`modules/vh/selectors/reports.py`](../../modules/vh/selectors/reports.py#L84) | Line 84 |
| **CFR-VH-017** | Operational role reassignment | [`modules/vh/services/roles.py`](../../modules/vh/services/roles.py#L14) | Line 14 |
| **AFR-VH-090** | Single active Caretaker constraint | [`modules/vh/services/roles.py`](../../modules/vh/services/roles.py#L14) | Line 14 |
| **AFR-VH-091** | Single active In-Charge constraint | [`modules/vh/services/roles.py`](../../modules/vh/services/roles.py#L14) | Line 14 |
| **AFR-VH-092** | Time-bound role assignments | [`modules/vh/models/roles.py`](../../modules/vh/models/roles.py#L16) | Line 16 |
| **AFR-VH-093** | Immediate role transition | [`modules/vh/services/roles.py`](../../modules/vh/services/roles.py#L14) | Line 14 |
| **AFR-VH-094** | Pending records transferred | [`modules/vh/services/roles.py`](../../modules/vh/services/roles.py#L14) | Line 14 |
| **AFR-VH-095** | Ongoing records transferred | [`modules/vh/services/roles.py`](../../modules/vh/services/roles.py#L14) | Line 14 |
| **BR-VH-001** | Stay dates validation | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L70) | Line 70 |
| **BR-VH-002** | Billing responsibility constraint | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L37) | Line 37 |
| **BR-VH-003** | Offline bookings routing parity | [`modules/vh/domain/state_machine.py`](../../modules/vh/domain/state_machine.py#L1) | Line 1 |
| **BR-VH-004** | Offline availability check | [`modules/vh/services/inventory.py`](../../modules/vh/services/inventory.py#L1) | Line 1 |
| **BR-VH-005** | Offline booking flagging | [`modules/vh/models/booking.py`](../../modules/vh/models/booking.py#L13) | Line 13 |
| **BR-VH-006** | Cancellation charge baseline | [`modules/vh/domain/cancellation.py`](../../modules/vh/domain/cancellation.py#L1) | Line 1 |
| **BR-VH-007** | 0% charge at 7 days | [`modules/vh/domain/cancellation.py`](../../modules/vh/domain/cancellation.py#L1) | Line 1 |
| **BR-VH-008** | 25% charge within 7 days | [`modules/vh/domain/cancellation.py`](../../modules/vh/domain/cancellation.py#L1) | Line 1 |
| **BR-VH-009** | 50% charge same day | [`modules/vh/domain/cancellation.py`](../../modules/vh/domain/cancellation.py#L1) | Line 1 |
| **BR-VH-010** | Modification bill adjustments | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **BR-VH-011** | Cancellation bill generation | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **BR-VH-012** | Allotment post-approval only | [`modules/vh/domain/state_machine.py`](../../modules/vh/domain/state_machine.py#L1) | Line 1 |
| **BR-VH-013** | Single occupancy rule | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L62) | Line 62 |
| **BR-VH-014** | Double occupancy rule | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L62) | Line 62 |
| **BR-VH-015** | Suite room rule | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L54) | Line 54 |
| **BR-VH-016** | Non-suite room rule | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L54) | Line 54 |
| **BR-VH-017** | No-show threshold and alert | [`modules/vh/services/alerts.py`](../../modules/vh/services/alerts.py#L11) | Line 11 |
| **BR-VH-018** | Overstay threshold and alert | [`modules/vh/services/alerts.py`](../../modules/vh/services/alerts.py#L34) | Line 34 |
| **BR-VH-019** | Category classification rule | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L46) | Line 46 |
| **BR-VH-023** | Tariff computation baseline | [`modules/vh/domain/tariffs.py`](../../modules/vh/domain/tariffs.py#L1) | Line 1 |
| **BR-VH-024** | Immutable historical bills | [`modules/vh/domain/tariffs.py`](../../modules/vh/domain/tariffs.py#L1) | Line 1 |
| **BR-VH-025** | Meals restricted to active stay | [`modules/vh/services/meals.py`](../../modules/vh/services/meals.py#L15) | Line 15 |
| **BR-VH-029** | Individual meals restriction | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L1) | Line 1 |
| **BR-VH-030** | Add-ons restriction | [`modules/vh/domain/rules.py`](../../modules/vh/domain/rules.py#L1) | Line 1 |
| **BR-VH-031** | Meal dates inside stay | [`modules/vh/services/meals.py`](../../modules/vh/services/meals.py#L15) | Line 15 |
| **BR-VH-032** | Meal charges billing inclusion | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **BR-VH-033** | Room rent line items | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **BR-VH-034** | Meal charges line items | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **BR-VH-035** | Cancellation line items | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **BR-VH-036** | Cash settlement mode | [`modules/vh/models/bill.py`](../../modules/vh/models/bill.py#L73) | Line 73 |
| **BR-VH-037** | Immutable settled bill | [`modules/vh/models/bill.py`](../../modules/vh/models/bill.py#L1) | Line 1 |
| **BR-VH-041** | Stock threshold warning | [`modules/vh/services/inventory.py`](../../modules/vh/services/inventory.py#L12) | Line 12 |
| **BR-VH-043** | Inventory alert dispatch | [`modules/vh/services/notifications.py`](../../modules/vh/services/notifications.py#L57) | Line 57 |
| **BR-VH-045** | Single active Caretaker | [`modules/vh/services/roles.py`](../../modules/vh/services/roles.py#L14) | Line 14 |
| **BR-VH-046** | Single active In-Charge | [`modules/vh/services/roles.py`](../../modules/vh/services/roles.py#L14) | Line 14 |
| **BR-VH-047** | Time-bound role | [`modules/vh/models/roles.py`](../../modules/vh/models/roles.py#L16) | Line 16 |
| **BR-VH-048** | Immediate role effect | [`modules/vh/services/roles.py`](../../modules/vh/services/roles.py#L14) | Line 14 |
| **BR-VH-049** | Pending records handover | [`modules/vh/services/roles.py`](../../modules/vh/services/roles.py#L14) | Line 14 |
| **BR-VH-050** | Ongoing records handover | [`modules/vh/services/roles.py`](../../modules/vh/services/roles.py#L14) | Line 14 |
| **UC-VH-001** | Online Booking Requisition | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L35) | Line 35 |
| **UC-VH-003** | Caretaker Booking Review & Routing | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L1) | Line 1 |
| **UC-VH-004** | VH In-Charge Approval/Rejection | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L1) | Line 1 |
| **UC-VH-005** | Offline Booking Registration | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L102) | Line 102 |
| **UC-VH-006** | Booking Modification Request | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L253) | Line 253 |
| **UC-VH-007** | Booking Cancellation Request | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L171) | Line 171 |
| **UC-VH-008** | Room Allotment | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L1) | Line 1 |
| **UC-VH-009** | Guest Check-In | [`modules/vh/services/stays.py`](../../modules/vh/services/stays.py#L1) | Line 1 |
| **UC-VH-012** | Meal Booking Request | [`modules/vh/services/meals.py`](../../modules/vh/services/meals.py#L15) | Line 15 |
| **UC-VH-013** | Bill Verification & Settlement | [`modules/vh/services/billing.py`](../../modules/vh/services/billing.py#L1) | Line 1 |
| **UC-VH-014** | Inventory Stock & Replenishment Request | [`modules/vh/services/inventory.py`](../../modules/vh/services/inventory.py#L81) | Line 81 |
| **UC-VH-015** | Inventory Replenishment Approval | [`modules/vh/services/inventory.py`](../../modules/vh/services/inventory.py#L104) | Line 104 |
| **UC-VH-017** | VH In-Charge Management Reports | [`modules/vh/selectors/reports.py`](../../modules/vh/selectors/reports.py#L100) | Line 100 |
| **UC-VH-018** | Caretaker Operational Reports | [`modules/vh/selectors/reports.py`](../../modules/vh/selectors/reports.py#L14) | Line 14 |
| **UC-VH-019** | Operational Role Reassignment | [`modules/vh/services/roles.py`](../../modules/vh/services/roles.py#L14) | Line 14 |
| **UC-VH-020** | Caretaker Cancellation Confirmation | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L174) | Line 174 |
| **UC-VH-021** | Guest Check-Out | [`modules/vh/services/stays.py`](../../modules/vh/services/stays.py#L1) | Line 1 |
| **UC-VH-023** | Booking Event Notifications | [`modules/vh/services/notifications.py`](../../modules/vh/services/notifications.py#L26) | Line 26 |
| **UC-VH-024** | Stay Exception & Reminder Notifications | [`modules/vh/services/alerts.py`](../../modules/vh/services/alerts.py#L11) | Line 11 |
| **UC-VH-025** | Inventory Threshold Notification | [`modules/vh/services/inventory.py`](../../modules/vh/services/inventory.py#L12) | Line 12 |
| **BW-VH-01** | Online Requisition - Direct Rejection | [`modules/vh/tests/test_journeys.py`](../../modules/vh/tests/test_journeys.py#L14) | Line 14 |
| **BW-VH-02** | Online Requisition - Forwarded & Approved | [`modules/vh/tests/test_journeys.py`](../../modules/vh/tests/test_journeys.py#L43) | Line 43 |
| **BW-VH-03** | Online Requisition - Forwarded & Rejected | [`modules/vh/tests/test_journeys.py`](../../modules/vh/tests/test_journeys.py#L76) | Line 76 |
| **BW-VH-04** | Offline Requisition - Direct Rejection | [`modules/vh/tests/test_journeys.py`](../../modules/vh/tests/test_journeys.py#L105) | Line 105 |
| **BW-VH-05** | Offline Requisition - Forwarded & Approved | [`modules/vh/tests/test_journeys.py`](../../modules/vh/tests/test_journeys.py#L105) | Line 105 |
| **BW-VH-06** | Offline Requisition - Forwarded & Rejected | [`modules/vh/tests/test_journeys.py`](../../modules/vh/tests/test_journeys.py#L105) | Line 105 |
| **BW-VH-07** | Cancellation >= 7 Days (0% charge) | [`modules/vh/tests/test_journeys.py`](../../modules/vh/tests/test_journeys.py#L135) | Line 135 |
| **BW-VH-08** | Cancellation 1-6 Days (25% charge) | [`modules/vh/tests/test_journeys.py`](../../modules/vh/tests/test_journeys.py#L160) | Line 160 |
| **BW-VH-09** | Cancellation Same Day (50% charge) | [`modules/vh/tests/test_journeys.py`](../../modules/vh/tests/test_journeys.py#L184) | Line 184 |
| **BW-VH-10** | Check-in to Cash Settlement End-to-End | [`modules/vh/tests/test_journeys.py`](../../modules/vh/tests/test_journeys.py#L208) | Line 208 |
| **CW-VH-01** | Pre-Arrival Cancellation Workflow | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L171) | Line 171 |
| **CW-VH-02** | Pre-Arrival Modification Workflow | [`modules/vh/services/booking_lifecycle.py`](../../modules/vh/services/booking_lifecycle.py#L253) | Line 253 |
