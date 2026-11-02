# Assignment 7A — Hostel Management System (HM)

This directory (`7a/`) contains the complete, self-contained implementation of **Assignment 7A – Hostel Management** for the Fusion ERP platform, developed using **Assignment 6B** as reference for project architecture, coding style, and integration conventions.

---

## 1. Design & Simulation Principles (Qwen 2.5 3B)

The implementation developed using **Qwen 2.5 3B**:
- **Simple and beginner-friendly:** Clear, readable Python code with standard Django and DRF idioms.
- **Basic programming logic:** No overengineered meta-classes or complicated abstractions.
- **Small, understandable functions:** Each function in `services.py` corresponds directly to a specific documented use case or business rule.
- **Strict adherence to boundaries:** Adheres to Fusion ERP architectural rules (e.g., integer IAM references, no cross-module foreign keys, clean role separation).
- **Concise footprint:** The complete implementation stays strictly within the **1,000-line code generation limit**.

---

## 2. Implemented Functional Areas & Requirements

| S.No | Functional Area | Documented Scope / Use Cases | Implemented In |
|---|---|---|---|
| 1 | **Hostel Master & Role Bindings** | Super Admin creates/activates hostels, assigns Warden & Caretaker bindings with optional time validity (UC-001–004, CFR-HM-001/002, BR-HM-001/004) | `models.Hostel`, `models.HostelRoleBinding`, `services.create_hostel`, `services.assign_hostel_role` |
| 2 | **Accommodation & Room Allotment** | Student requests accommodation, Super Admin allots room enforcing room capacity limits (UC-005, 006, BW-HM-01, BR-HM-010) | `models.AccommodationRequest`, `models.Room`, `services.allot_room` |
| 3 | **Room Reallotment, Vacation & Exchange** | Reallotment, formal vacation, and student-to-student room exchange within assigned hostel (UC-007, 010, BR-HM-009/010) | `models.RoomAllocationHistory`, `services.exchange_rooms`, `services.vacate_room` |
| 4 | **Attendance Management** | Caretaker records attendance (Present/Absent), student queries own attendance records (UC-012, 013, CFR-HM-009/010, BR-HM-011) | `models.AttendanceRecord`, `services.record_student_attendance` |
| 5 | **Leave Management** | Student submits leave request, Caretaker reviews and approves/rejects with status update notifications (UC-014–016, BW-HM-02/03, CW-HM-01, BR-HM-013) | `models.LeaveRequest`, `services.submit_leave_request`, `services.review_leave_request` |
| 6 | **Complaint Management & Escalation** | Student submits complaints with category/description; Caretaker resolves or escalates to Warden (UC-017–019, BW-HM-04/05, CW-HM-02, BR-HM-015/016) | `models.HostelComplaint`, `services.submit_hostel_complaint`, `services.update_complaint_status` |
| 7 | **Guest Room Booking** | Student books guest room; Caretaker reviews and approves/rejects (UC-020–022, BW-HM-06/07, CW-HM-03, BR-HM-018/019) | `models.GuestRoomBooking`, `services.submit_guest_room_booking`, `services.review_guest_room_booking` |
| 8 | **Extended-Stay Management** | Student submits vacation extended-stay; system records fee, deadline, and compliance status; Warden approves/rejects (UC-023–025, BW-HM-08/09, CW-HM-04, BR-HM-020/021) | `models.ExtendedStayRequest`, `services.record_extended_stay_compliance`, `services.review_extended_stay_request` |
| 9 | **Fine Management** | Caretaker records fines with mandatory fields (student, reason, amount, date); student views fine history (UC-026, 027, BR-HM-025) | `models.HostelFine`, `services.record_hostel_fine` |
| 10 | **Hostel Operational Inventory** | Caretaker maintains operational inventory; changes logged for accountability (UC-028, 029, BR-HM-027) | `models.HostelInventory`, `models.InventoryLog`, `services.update_hostel_inventory` |
| 11 | **Security Guard Shift Management** | Warden schedules and reviews security guard shifts (UC-030, BR-HM-028) | `models.SecurityGuardShift`, `services.schedule_guard_shift` |
| 12 | **Hostel Notices & Notice Board** | Caretaker & Warden publish notices; student views hostel notice board (UC-031, 032, BR-HM-029/030/031) | `models.HostelNotice`, `services.publish_hostel_notice`, `services.get_hostel_notices` |
| 13 | **Reports & Operational Summaries** | Predefined summaries for occupancy, complaints, fines, and hostel operations (UC-033, BR-HM-032) | `services.generate_hostel_summary_report`, `views.OperationalReportView` |
| 14 | **Event Notifications** | System emits notifications for room allotment, leave decisions, complaint updates, guest bookings, extended stays, and fines (UC-034, BR-HM-034) | `models.Notification`, `services.send_notification` |

---

## 3. Directory Structure

```
7a/
├── __init__.py        # Module package initializer with Django module aliasing
├── apps.py            # Django AppConfig (HostelManagementConfig)
├── models.py          # Data models with BaseModel and app_label definition
├── services.py        # Business logic, validation, workflows, and notification helpers
├── serializers.py     # Django REST Framework serializers
├── views.py           # DRF APIViews exposing endpoints for all actors
├── urls.py            # URL routing for REST API
├── tests.py           # Standalone and in-memory automated test suite (13 tests)
└── README.md          # Assignment documentation and report
```

---

## 4. How to Run the Tests

To run the complete test suite:

```bash
# Using python directly:
python 7a/tests.py

# Or via the virtual environment:
.venv/Scripts/python.exe 7a/tests.py
```

The test runner initializes an in-memory SQLite database, runs migrations, executes 13 comprehensive unit and API test cases, and outputs test execution results.

