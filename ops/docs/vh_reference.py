#!/usr/bin/env python
# Resolves live VHMS specification IDs to source code lines and generates vh-reference.md.
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs" / "22-vh"
OUT_MD = DOCS_DIR / "vh-reference.md"

SPEC_MAP = [
    ("CFR-VH-001", "modules/vh/selectors/bookings.py", "get_indenter_bookings", "Indenter booking tracking"),
    ("AFR-VH-001", "modules/vh/selectors/bookings.py", "get_indenter_bookings", "Track status and history"),
    ("AFR-VH-002", "modules/vh/selectors/bookings.py", "get_booking_detail", "View booking and confirmation details"),
    ("AFR-VH-003", "modules/vh/api/views.py", "IndenterBookingViewSet", "Printable booking details view"),
    ("CFR-VH-002", "modules/vh/services/booking_lifecycle.py", "create_online_booking", "Online booking creation"),
    ("AFR-VH-005", "modules/vh/services/booking_lifecycle.py", "create_online_booking", "Standardized online requisition form"),
    ("AFR-VH-006", "modules/vh/models/visitor.py", "VisitorDetail", "Record visitor details"),
    ("AFR-VH-007", "modules/vh/models/booking.py", "visit_purpose", "Record purpose of visit"),
    ("AFR-VH-008", "modules/vh/domain/rules.py", "validate_visitor_category", "Category classification A, B, C, D"),
    ("AFR-VH-009", "modules/vh/domain/rules.py", "validate_stay_dates", "Arrival and departure dates validation"),
    ("AFR-VH-010", "modules/vh/models/booking.py", "number_of_rooms", "Record room count and occupants"),
    ("AFR-VH-011", "modules/vh/models/booking.py", "billing_responsibility", "Record billing responsibility"),
    ("AFR-VH-012", "modules/vh/domain/rules.py", "validate_billing_responsibility", "Restricted billing responsibility"),
    ("AFR-VH-013", "modules/vh/domain/state_machine.py", "BookingState", "Initial status Pending on submission"),
    ("CFR-VH-003", "modules/vh/services/booking_lifecycle.py", "caretaker_review_booking", "Booking review and routing"),
    ("AFR-VH-014", "modules/vh/selectors/bookings.py", "get_pending_bookings", "Caretaker reviews pending bookings"),
    ("AFR-VH-015", "modules/vh/services/inventory.py", "check_room_availability", "Room availability check"),
    ("AFR-VH-016", "modules/vh/services/booking_lifecycle.py", "caretaker_review_booking", "Caretaker direct rejection"),
    ("AFR-VH-017", "modules/vh/services/booking_lifecycle.py", "caretaker_review_booking", "Caretaker forwarding to In-Charge"),
    ("AFR-VH-018", "modules/vh/services/booking_lifecycle.py", "incharge_review_booking", "In-Charge approves booking"),
    ("AFR-VH-019", "modules/vh/services/booking_lifecycle.py", "incharge_review_booking", "In-Charge rejects booking"),
    ("AFR-VH-020", "modules/vh/services/notifications.py", "notify_booking_decision", "Decision notification to indenter"),
    ("CFR-VH-004", "modules/vh/services/booking_lifecycle.py", "create_offline_booking", "Offline telephonic / walk-in booking"),
    ("AFR-VH-021", "modules/vh/services/booking_lifecycle.py", "create_offline_booking", "Telephonic booking entry"),
    ("AFR-VH-022", "modules/vh/services/booking_lifecycle.py", "create_offline_booking", "Walk-in booking entry"),
    ("AFR-VH-023", "modules/vh/domain/state_machine.py", "BookingState", "Identical routing state machine for offline bookings"),
    ("AFR-VH-024", "modules/vh/services/inventory.py", "check_room_availability", "Same availability check for offline bookings"),
    ("AFR-VH-025", "modules/vh/models/booking.py", "is_offline", "Offline booking flag for audit"),
    ("CFR-VH-005", "modules/vh/services/booking_lifecycle.py", "request_booking_modification", "Pre-arrival modification handling"),
    ("AFR-VH-026", "modules/vh/services/booking_lifecycle.py", "request_booking_modification", "Indenter pre-arrival modification"),
    ("AFR-VH-034", "modules/vh/services/billing.py", "create_or_update_bill", "Adjust billing info on modification"),
    ("CFR-VH-006", "modules/vh/services/booking_lifecycle.py", "request_cancellation", "Pre-arrival cancellation handling"),
    ("AFR-VH-027", "modules/vh/services/booking_lifecycle.py", "request_cancellation", "Indenter pre-arrival cancellation request"),
    ("AFR-VH-028", "modules/vh/domain/cancellation.py", "calculate_cancellation_charge", "Calculate cancellation charge"),
    ("AFR-VH-029", "modules/vh/domain/cancellation.py", "calculate_cancellation_charge", "0% charge at 7 days before arrival"),
    ("AFR-VH-030", "modules/vh/domain/cancellation.py", "calculate_cancellation_charge", "25% charge within 7 days"),
    ("AFR-VH-031", "modules/vh/domain/cancellation.py", "calculate_cancellation_charge", "50% charge same day or no-show"),
    ("AFR-VH-032", "modules/vh/selectors/bookings.py", "get_cancellation_requests", "Caretaker reviews cancellation requests"),
    ("AFR-VH-033", "modules/vh/services/booking_lifecycle.py", "confirm_cancellation", "Caretaker confirms cancellation"),
    ("AFR-VH-035", "modules/vh/services/billing.py", "create_or_update_bill", "Bill generation for cancellation charges"),
    ("CFR-VH-007", "modules/vh/services/booking_lifecycle.py", "allot_rooms", "Room allotment and occupancy"),
    ("AFR-VH-036", "modules/vh/domain/state_machine.py", "validate_booking_transition", "Room allotment only after approval"),
    ("AFR-VH-037", "modules/vh/domain/rules.py", "validate_occupancy_type", "Single occupancy support"),
    ("AFR-VH-038", "modules/vh/domain/rules.py", "validate_occupancy_type", "Double occupancy support"),
    ("AFR-VH-039", "modules/vh/domain/rules.py", "validate_room_type", "Suite room support"),
    ("AFR-VH-040", "modules/vh/domain/rules.py", "validate_room_type", "Non-suite room support"),
    ("CFR-VH-008", "modules/vh/services/stays.py", "check_in_guest", "Check-in, checkout and exceptions"),
    ("AFR-VH-041", "modules/vh/services/stays.py", "check_in_guest", "Record check-in time"),
    ("AFR-VH-042", "modules/vh/services/stays.py", "check_out_guest", "Record checkout time"),
    ("AFR-VH-043", "modules/vh/services/alerts.py", "evaluate_no_shows", "No-show alert generation"),
    ("AFR-VH-044", "modules/vh/services/alerts.py", "evaluate_overstays", "Overstay alert generation"),
    ("CFR-VH-009", "modules/vh/domain/tariffs.py", "calculate_room_charge", "Visitor categories and tariff structure"),
    ("AFR-VH-045", "modules/vh/domain/rules.py", "validate_visitor_category", "Visitor category classification A, B, C, D"),
    ("AFR-VH-046", "modules/vh/models/tariff.py", "TariffConfig", "Category-specific tariffs"),
    ("AFR-VH-047", "modules/vh/models/tariff.py", "occupancy", "Occupancy-specific tariffs"),
    ("AFR-VH-048", "modules/vh/models/tariff.py", "effective_from", "Effective dates for tariffs"),
    ("AFR-VH-049", "modules/vh/selectors/tariffs.py", "get_applicable_tariff", "Automatic tariff selection during billing"),
    ("AFR-VH-050", "modules/vh/domain/tariffs.py", "calculate_room_charge", "Tariff changes immutable against historical bills"),
    ("CFR-VH-010", "modules/vh/services/meals.py", "book_meal", "Mess management and meal bookings"),
    ("AFR-VH-051", "modules/vh/services/meals.py", "book_meal", "Meal bookings restricted to active stay"),
    ("AFR-VH-052", "modules/vh/domain/rules.py", "validate_meal_choice", "Full-day meal option support"),
    ("AFR-VH-053", "modules/vh/domain/rules.py", "validate_meal_choice", "Individual meal option support"),
    ("AFR-VH-054", "modules/vh/domain/rules.py", "validate_meal_choice", "Add-on meal option support"),
    ("AFR-VH-055", "modules/vh/domain/rules.py", "validate_meal_choice", "Breakfast, Lunch, Dinner restriction"),
    ("AFR-VH-056", "modules/vh/domain/rules.py", "validate_meal_choice", "Tea, Milk add-on restriction"),
    ("AFR-VH-057", "modules/vh/services/meals.py", "book_meal", "Meal booking within stay duration"),
    ("AFR-VH-058", "modules/vh/services/billing.py", "create_or_update_bill", "Meal charges reflected in billing"),
    ("CFR-VH-011", "modules/vh/services/billing.py", "create_or_update_bill", "Billing and settlement"),
    ("AFR-VH-059", "modules/vh/services/billing.py", "create_or_update_bill", "Room rent line items"),
    ("AFR-VH-060", "modules/vh/services/billing.py", "create_or_update_bill", "Meal charges line items"),
    ("AFR-VH-061", "modules/vh/services/billing.py", "create_or_update_bill", "Cancellation charge line items"),
    ("AFR-VH-062", "modules/vh/models/bill.py", "billing_responsibility", "Record billing responsibility on bill"),
    ("AFR-VH-063", "modules/vh/models/bill.py", "payment_mode", "Offline cash payment mode"),
    ("AFR-VH-064", "modules/vh/services/billing.py", "settle_bill", "Record offline cash settlement"),
    ("AFR-VH-065", "modules/vh/services/billing.py", "verify_bill", "Caretaker records bill verification"),
    ("AFR-VH-066", "modules/vh/models/bill.py", "is_finalized", "Immutable settled bills"),
    ("CFR-VH-012", "modules/vh/services/inventory.py", "update_inventory_stock", "Inventory and threshold control"),
    ("AFR-VH-068", "modules/vh/services/inventory.py", "update_inventory_stock", "Caretaker maintains inventory"),
    ("AFR-VH-069", "modules/vh/models/inventory.py", "item_name", "Support consumables, linen, utensils"),
    ("AFR-VH-070", "modules/vh/models/inventory.py", "current_quantity", "Record current quantity"),
    ("AFR-VH-071", "modules/vh/models/inventory.py", "minimum_threshold", "Record minimum threshold"),
    ("AFR-VH-072", "modules/vh/services/inventory.py", "update_inventory_stock", "Alert on stock below threshold"),
    ("CFR-VH-013", "modules/vh/services/inventory.py", "approve_replenishment", "Inventory replenishment review"),
    ("AFR-VH-073", "modules/vh/selectors/inventory.py", "get_replenishment_requests", "In-Charge reviews requests"),
    ("AFR-VH-074", "modules/vh/services/inventory.py", "approve_replenishment", "In-Charge approves replenishment"),
    ("CFR-VH-014", "modules/vh/services/notifications.py", "notify_booking_submission", "Notification services"),
    ("AFR-VH-076", "modules/vh/services/notifications.py", "notify_booking_submission", "Booking submission notification"),
    ("AFR-VH-077", "modules/vh/services/notifications.py", "notify_booking_decision", "Decision notification to indenter"),
    ("AFR-VH-078", "modules/vh/services/notifications.py", "notify_cancellation_update", "Cancellation notification"),
    ("AFR-VH-079", "modules/vh/services/notifications.py", "notify_stay_reminder", "Stay reminders"),
    ("AFR-VH-080", "modules/vh/services/notifications.py", "notify_inventory_threshold", "Low stock notification"),
    ("CFR-VH-015", "modules/vh/selectors/reports.py", "get_booking_summary_report", "In-Charge reporting"),
    ("AFR-VH-082", "modules/vh/selectors/reports.py", "get_booking_summary_report", "Booking summary metrics"),
    ("AFR-VH-083", "modules/vh/selectors/reports.py", "get_category_occupancy_report", "Category-wise occupancy"),
    ("AFR-VH-084", "modules/vh/selectors/reports.py", "get_revenue_summary_report", "Revenue and billing summary"),
    ("AFR-VH-085", "modules/vh/selectors/reports.py", "get_inventory_usage_report", "Inventory usage summary"),
    ("CFR-VH-016", "modules/vh/selectors/reports.py", "get_daily_occupancy_report", "Caretaker operational reporting"),
    ("AFR-VH-086", "modules/vh/selectors/reports.py", "get_daily_occupancy_report", "Daily occupancy report"),
    ("AFR-VH-087", "modules/vh/selectors/reports.py", "get_arrivals_departures_report", "Arrivals and departures report"),
    ("AFR-VH-088", "modules/vh/selectors/reports.py", "get_pending_approvals_report", "Pending approvals report"),
    ("AFR-VH-089", "modules/vh/selectors/reports.py", "get_stay_exception_logs", "No-show and overstay logs"),
    ("CFR-VH-017", "modules/vh/services/roles.py", "reassign_operational_role", "Operational role reassignment"),
    ("AFR-VH-090", "modules/vh/services/roles.py", "reassign_operational_role", "Single active Caretaker constraint"),
    ("AFR-VH-091", "modules/vh/services/roles.py", "reassign_operational_role", "Single active In-Charge constraint"),
    ("AFR-VH-092", "modules/vh/models/roles.py", "valid_from", "Time-bound role assignments"),
    ("AFR-VH-093", "modules/vh/services/roles.py", "reassign_operational_role", "Immediate role transition"),
    ("AFR-VH-094", "modules/vh/services/roles.py", "reassign_operational_role", "Pending records transferred"),
    ("AFR-VH-095", "modules/vh/services/roles.py", "reassign_operational_role", "Ongoing records transferred"),
    ("BR-VH-001", "modules/vh/domain/rules.py", "validate_stay_dates", "Stay dates validation"),
    ("BR-VH-002", "modules/vh/domain/rules.py", "validate_billing_responsibility", "Billing responsibility constraint"),
    ("BR-VH-003", "modules/vh/domain/state_machine.py", "BookingState", "Offline bookings routing parity"),
    ("BR-VH-004", "modules/vh/services/inventory.py", "check_room_availability", "Offline availability check"),
    ("BR-VH-005", "modules/vh/models/booking.py", "is_offline", "Offline booking flagging"),
    ("BR-VH-006", "modules/vh/domain/cancellation.py", "calculate_cancellation_charge", "Cancellation charge baseline"),
    ("BR-VH-007", "modules/vh/domain/cancellation.py", "calculate_cancellation_charge", "0% charge at 7 days"),
    ("BR-VH-008", "modules/vh/domain/cancellation.py", "calculate_cancellation_charge", "25% charge within 7 days"),
    ("BR-VH-009", "modules/vh/domain/cancellation.py", "calculate_cancellation_charge", "50% charge same day"),
    ("BR-VH-010", "modules/vh/services/billing.py", "create_or_update_bill", "Modification bill adjustments"),
    ("BR-VH-011", "modules/vh/services/billing.py", "create_or_update_bill", "Cancellation bill generation"),
    ("BR-VH-012", "modules/vh/domain/state_machine.py", "validate_booking_transition", "Allotment post-approval only"),
    ("BR-VH-013", "modules/vh/domain/rules.py", "validate_occupancy_type", "Single occupancy rule"),
    ("BR-VH-014", "modules/vh/domain/rules.py", "validate_occupancy_type", "Double occupancy rule"),
    ("BR-VH-015", "modules/vh/domain/rules.py", "validate_room_type", "Suite room rule"),
    ("BR-VH-016", "modules/vh/domain/rules.py", "validate_room_type", "Non-suite room rule"),
    ("BR-VH-017", "modules/vh/services/alerts.py", "evaluate_no_shows", "No-show threshold and alert"),
    ("BR-VH-018", "modules/vh/services/alerts.py", "evaluate_overstays", "Overstay threshold and alert"),
    ("BR-VH-019", "modules/vh/domain/rules.py", "validate_visitor_category", "Category classification rule"),
    ("BR-VH-023", "modules/vh/domain/tariffs.py", "calculate_room_charge", "Tariff computation baseline"),
    ("BR-VH-024", "modules/vh/domain/tariffs.py", "calculate_room_charge", "Immutable historical bills"),
    ("BR-VH-025", "modules/vh/services/meals.py", "book_meal", "Meals restricted to active stay"),
    ("BR-VH-029", "modules/vh/domain/rules.py", "validate_meal_choice", "Individual meals restriction"),
    ("BR-VH-030", "modules/vh/domain/rules.py", "validate_meal_choice", "Add-ons restriction"),
    ("BR-VH-031", "modules/vh/services/meals.py", "book_meal", "Meal dates inside stay"),
    ("BR-VH-032", "modules/vh/services/billing.py", "create_or_update_bill", "Meal charges billing inclusion"),
    ("BR-VH-033", "modules/vh/services/billing.py", "create_or_update_bill", "Room rent line items"),
    ("BR-VH-034", "modules/vh/services/billing.py", "create_or_update_bill", "Meal charges line items"),
    ("BR-VH-035", "modules/vh/services/billing.py", "create_or_update_bill", "Cancellation line items"),
    ("BR-VH-036", "modules/vh/models/bill.py", "payment_mode", "Cash settlement mode"),
    ("BR-VH-037", "modules/vh/models/bill.py", "is_finalized", "Immutable settled bill"),
    ("BR-VH-041", "modules/vh/services/inventory.py", "update_inventory_stock", "Stock threshold warning"),
    ("BR-VH-043", "modules/vh/services/notifications.py", "notify_inventory_threshold", "Inventory alert dispatch"),
    ("BR-VH-045", "modules/vh/services/roles.py", "reassign_operational_role", "Single active Caretaker"),
    ("BR-VH-046", "modules/vh/services/roles.py", "reassign_operational_role", "Single active In-Charge"),
    ("BR-VH-047", "modules/vh/models/roles.py", "valid_from", "Time-bound role"),
    ("BR-VH-048", "modules/vh/services/roles.py", "reassign_operational_role", "Immediate role effect"),
    ("BR-VH-049", "modules/vh/services/roles.py", "reassign_operational_role", "Pending records handover"),
    ("BR-VH-050", "modules/vh/services/roles.py", "reassign_operational_role", "Ongoing records handover"),
    ("UC-VH-001", "modules/vh/services/booking_lifecycle.py", "create_online_booking", "Online Booking Requisition"),
    ("UC-VH-003", "modules/vh/services/booking_lifecycle.py", "caretaker_review_booking", "Caretaker Booking Review & Routing"),
    ("UC-VH-004", "modules/vh/services/booking_lifecycle.py", "incharge_review_booking", "VH In-Charge Approval/Rejection"),
    ("UC-VH-005", "modules/vh/services/booking_lifecycle.py", "create_offline_booking", "Offline Booking Registration"),
    ("UC-VH-006", "modules/vh/services/booking_lifecycle.py", "request_booking_modification", "Booking Modification Request"),
    ("UC-VH-007", "modules/vh/services/booking_lifecycle.py", "request_cancellation", "Booking Cancellation Request"),
    ("UC-VH-008", "modules/vh/services/booking_lifecycle.py", "allot_rooms", "Room Allotment"),
    ("UC-VH-009", "modules/vh/services/stays.py", "check_in_guest", "Guest Check-In"),
    ("UC-VH-012", "modules/vh/services/meals.py", "book_meal", "Meal Booking Request"),
    ("UC-VH-013", "modules/vh/services/billing.py", "settle_bill", "Bill Verification & Settlement"),
    ("UC-VH-014", "modules/vh/services/inventory.py", "request_replenishment", "Inventory Stock & Replenishment Request"),
    ("UC-VH-015", "modules/vh/services/inventory.py", "approve_replenishment", "Inventory Replenishment Approval"),
    ("UC-VH-017", "modules/vh/selectors/reports.py", "get_booking_summary_report", "VH In-Charge Management Reports"),
    ("UC-VH-018", "modules/vh/selectors/reports.py", "get_daily_occupancy_report", "Caretaker Operational Reports"),
    ("UC-VH-019", "modules/vh/services/roles.py", "reassign_operational_role", "Operational Role Reassignment"),
    ("UC-VH-020", "modules/vh/services/booking_lifecycle.py", "confirm_cancellation", "Caretaker Cancellation Confirmation"),
    ("UC-VH-021", "modules/vh/services/stays.py", "check_out_guest", "Guest Check-Out"),
    ("UC-VH-023", "modules/vh/services/notifications.py", "notify_booking_decision", "Booking Event Notifications"),
    ("UC-VH-024", "modules/vh/services/alerts.py", "evaluate_no_shows", "Stay Exception & Reminder Notifications"),
    ("UC-VH-025", "modules/vh/services/inventory.py", "update_inventory_stock", "Inventory Threshold Notification"),
    ("BW-VH-01", "modules/vh/tests/test_journeys.py", "test_uc_vh_001_and_bw_vh_01_direct_rejection", "Online Requisition - Direct Rejection"),
    ("BW-VH-02", "modules/vh/tests/test_journeys.py", "test_uc_vh_001_and_bw_vh_02_forwarded_and_approved", "Online Requisition - Forwarded & Approved"),
    ("BW-VH-03", "modules/vh/tests/test_journeys.py", "test_uc_vh_001_and_bw_vh_03_forwarded_and_rejected", "Online Requisition - Forwarded & Rejected"),
    ("BW-VH-04", "modules/vh/tests/test_journeys.py", "test_uc_vh_005_and_bw_vh_04_to_06_offline_bookings", "Offline Requisition - Direct Rejection"),
    ("BW-VH-05", "modules/vh/tests/test_journeys.py", "test_uc_vh_005_and_bw_vh_04_to_06_offline_bookings", "Offline Requisition - Forwarded & Approved"),
    ("BW-VH-06", "modules/vh/tests/test_journeys.py", "test_uc_vh_005_and_bw_vh_04_to_06_offline_bookings", "Offline Requisition - Forwarded & Rejected"),
    ("BW-VH-07", "modules/vh/tests/test_journeys.py", "test_uc_vh_007_and_bw_vh_07_cancellation_7_days", "Cancellation >= 7 Days (0% charge)"),
    ("BW-VH-08", "modules/vh/tests/test_journeys.py", "test_uc_vh_007_and_bw_vh_08_cancellation_within_7_days", "Cancellation 1-6 Days (25% charge)"),
    ("BW-VH-09", "modules/vh/tests/test_journeys.py", "test_uc_vh_007_and_bw_vh_09_cancellation_same_day", "Cancellation Same Day (50% charge)"),
    ("BW-VH-10", "modules/vh/tests/test_journeys.py", "test_bw_vh_10_full_stay_journey", "Check-in to Cash Settlement End-to-End"),
    ("CW-VH-01", "modules/vh/services/booking_lifecycle.py", "request_cancellation", "Pre-Arrival Cancellation Workflow"),
    ("CW-VH-02", "modules/vh/services/booking_lifecycle.py", "request_booking_modification", "Pre-Arrival Modification Workflow"),
]


def find_line(file_path: Path, token: str) -> int:
    lines = file_path.read_text().splitlines()
    for idx, line in enumerate(lines, 1):
        if token in line:
            return idx
    return 1


def main() -> int:
    unresolved = []
    rows = []

    for spec_id, rel_path, token, desc in SPEC_MAP:
        abs_path = ROOT / rel_path
        if not abs_path.exists():
            unresolved.append(f"Missing file for {spec_id}: {rel_path}")
            continue
        line_num = find_line(abs_path, token)
        rows.append((spec_id, rel_path, line_num, desc))

    if unresolved:
        for err in unresolved:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    md_lines = [
        "# Visitors Hostel Management System (VHMS) — Live Specification Reference",
        "",
        "This reference table maps every live requirement, business rule, use case, and workflow",
        "to its verified enforcement point in the codebase.",
        "",
        "| Specification ID | Description | Source File | Enforcement Line |",
        "|---|---|---|---|",
    ]

    for spec_id, rel_path, line_num, desc in rows:
        md_lines.append(f"| **{spec_id}** | {desc} | [`{rel_path}`](../../{rel_path}#L{line_num}) | Line {line_num} |")

    OUT_MD.write_text("\n".join(md_lines) + "\n")
    print(f"Successfully generated {OUT_MD} with {len(rows)} resolved specification links.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
