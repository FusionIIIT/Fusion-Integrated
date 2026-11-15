"""Permission codes, named once. registry.py declares the same strings and a
test fails if the two ever drift apart."""

MODULE = "visitor_hostel"

# -- Indenter (any faculty, staff or student) ------------------------------------
BOOKING_CREATE = "visitor_hostel.booking.create"
BOOKING_VIEW_SELF = "visitor_hostel.booking.view_self"
MODIFICATION_CREATE = "visitor_hostel.modification.create"
CANCELLATION_CREATE = "visitor_hostel.cancellation.create"

# -- Caretaker -------------------------------------------------------------------
BOOKING_VIEW = "visitor_hostel.booking.view"
BOOKING_REVIEW = "visitor_hostel.booking.review"
OFFLINE_BOOKING_CREATE = "visitor_hostel.offline_booking.create"
CANCELLATION_APPROVE = "visitor_hostel.cancellation.approve"
ROOM_MANAGE = "visitor_hostel.room.manage"
STAY_UPDATE = "visitor_hostel.stay.update"
MEAL_MANAGE = "visitor_hostel.meal.manage"
BILL_MANAGE = "visitor_hostel.bill.manage"
INVENTORY_MANAGE = "visitor_hostel.inventory.manage"
REPLENISHMENT_CREATE = "visitor_hostel.replenishment.create"
OPERATIONS_REPORT_VIEW = "visitor_hostel.operations_report.view"
ALERT_VIEW = "visitor_hostel.alert.view"

# -- VH In-Charge ----------------------------------------------------------------
BOOKING_APPROVE = "visitor_hostel.booking.approve"
BILL_VIEW = "visitor_hostel.bill.view"
INVENTORY_VIEW = "visitor_hostel.inventory.view"
REPLENISHMENT_APPROVE = "visitor_hostel.replenishment.approve"
REPORT_VIEW = "visitor_hostel.report.view"

# -- Both operational roles ------------------------------------------------------
TARIFF_VIEW = "visitor_hostel.tariff.view"
DUTY_VIEW = "visitor_hostel.duty.view"

# -- Authority unresolved by the spec (UC-VH-011/019/022): held by no designation yet
TARIFF_MANAGE = "visitor_hostel.tariff.manage"
DUTY_MANAGE = "visitor_hostel.duty.manage"
MODIFICATION_APPROVE = "visitor_hostel.modification.approve"
