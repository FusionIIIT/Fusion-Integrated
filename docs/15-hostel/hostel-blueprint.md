# Hostel Management (`hostel`) — Module Blueprint

**Specification Reference:** `15-Hostel-Management` v1.4_FINAL_SYNCHRONIZED  
**Module Code:** `hostel`  
**Django App:** `modules.hostel`  

---

## 1. Traceability Table

### 1.1 Business Rules Traceability (BR-HM-001 to BR-HM-035)

| Rule ID | What it Requires | Layer | Enforcement Point | Notes |
|---|---|---|---|---|
| `BR-HM-001` | Hostel-specific Warden and Caretaker role bindings & change recording | `models`, `services` | `HostelRoleBinding`, `svc.manage_role_binding` | Super Admin maintains bindings |
| `BR-HM-002` | Student hostel-specific access basis | `domain`, `selectors` | `rules.validate_student_access`, `sel.get_assigned_hostel_ids` | Scoped to allocated hostel |
| `BR-HM-003` | Super Admin institution-level access boundary | `selectors` | `sel.is_super_admin`, `sel.visible_hostels` | Unrestricted cross-hostel scope |
| `BR-HM-004` | Time-bound role validity boundary | `models`, `services` | `HostelRoleBinding.valid_from/to` | Dates recorded when configured |
| `BR-HM-005` | RBAC data and function restriction | `api`, `selectors` | `HasModuleGrant`, `HasPermission`, selectors | Failed check returns 403 / 404 |
| `BR-HM-006` | Role reassignment pending-record visibility | `selectors` | `sel.visible_leaves`, `sel.visible_complaints` | New role holder sees pending items |
| `BR-HM-007` | Operational handover boundary | `services` | Responsibility records in system | Handover outside system out of scope |
| `BR-HM-008` | Allotment algorithm boundary | `services` | `svc.record_allotment_decision` | Records decisions without forced algorithm |
| `BR-HM-009` | Room assignment history retention | `models`, `services` | `RoomAllotment` status `vacated`/`exchanged` | Full history retained for audit |
| `BR-HM-010` | Room capacity limit enforcement | `domain`, `services` | `rules.validate_room_capacity` | Rejects allotments exceeding capacity |
| `BR-HM-011` | Attendance record retention | `models` | `AttendanceRecord` table | Retained for review and reporting |
| `BR-HM-012` | Attendance procedure boundary | `services` | Batch attendance entry | Procedure details outside system scope |
| `BR-HM-013` | Leave history retention | `models` | `LeaveRequest` table | Historical records permanently stored |
| `BR-HM-014` | External leave policy boundary | `services` | `svc.submit_leave_request` | External leave policy out of HM scope |
| `BR-HM-015` | Complaint core data capture | `domain`, `models` | `rules.validate_complaint_data` | Category & description mandatory |
| `BR-HM-016` | Hostel-related complaint scope | `domain` | `rules.validate_complaint_data` | Must match valid hostel categories |
| `BR-HM-017` | Central complaint integration boundary | `services`, `models` | `HostelComplaint.escalated_to_user_id` | Escalation to Warden supported |
| `BR-HM-018` | Guest-room booking history retention | `models` | `GuestRoomBooking` table | Retained for audit and security |
| `BR-HM-019` | Guest-room booking scope boundary | `services` | Booking request & decision only | Check-in/out & charges out of scope |
| `BR-HM-020` | Extended-stay charge recording boundary | `models`, `services` | `ExtendedStayRequest.charge_amount` | Recorded with decision |
| `BR-HM-021` | Extended-stay compliance recording boundary | `models`, `services` | `compliance_status`, `payment_deadline` | Tracks payment/deadline status |
| `BR-HM-022` | Extended-stay application window boundary | `services` | Flexible submission window | External window policy out of scope |
| `BR-HM-023` | Extended-stay payment processing boundary | `models` | Recorded status only | Actual financial processing out of scope |
| `BR-HM-024` | Extended-stay appeal & expedited handling boundary | `services` | Direct approval/rejection only | Formal appeals out of scope |
| `BR-HM-025` | Fine mandatory data fields | `domain`, `models` | `rules.validate_fine_fields` | Student, positive amount, reason, date |
| `BR-HM-026` | Fine lifecycle and policy boundary | `models`, `services` | `HostelFine` status `recorded` | Payment/waiver accounting out of scope |
| `BR-HM-027` | Inventory & staff coordination boundary and logging | `models`, `services` | `HostelInventoryItem`, `HostelStaffDutyLog` | Operational logs only; HR out of scope |
| `BR-HM-028` | Security scope boundary | `models`, `services` | `SecurityGuardShift` table | Shifts only; security HR out of scope |
| `BR-HM-029` | Assigned-hostel notice publishing | `domain`, `services` | `rules.validate_notice_publication` | Warden/Caretaker restricted to assigned |
| `BR-HM-030` | Notice history retention | `models` | `HostelNotice` table | Notice archive permanently preserved |
| `BR-HM-031` | Authorized notice board visibility | `selectors` | `sel.visible_notices` | Campus & assigned hostel notices shown |
| `BR-HM-032` | Predefined HM reports boundary | `selectors` | `sel.generate_hostel_report` | Predefined operational summaries |
| `BR-HM-033` | Advanced analytics exclusion | `selectors` | Predefined queries only | Advanced predictive analysis excluded |
| `BR-HM-034` | Configured notification event scope | `services` | `svc.notify_user`, `HostelNotification` | Emits updates on key workflow events |
| `BR-HM-035` | Caretaker assigned hostel & shift context | `domain`, `selectors` | `rules.validate_caretaker_access` | Restricts operations to assigned hostel |

---

### 1.2 Use Cases Traceability (HM-UC-001 to HM-UC-039)

| Use Case ID | Name | Primary Actor | Layer | Planned Implementation |
|---|---|---|---|---|
| `HM-UC-001` | Create Hostel Record | Super Admin | `services`, `api` | `svc.create_hostel`, `HostelListCreateView` |
| `HM-UC-002` | Activate or Deactivate Hostel Record | Super Admin | `services`, `api` | `svc.set_hostel_active_status`, `HostelDetailView` |
| `HM-UC-003` | Manage Warden Role Binding | Super Admin | `services`, `api` | `svc.manage_role_binding`, `RoleBindingListCreateView` |
| `HM-UC-004` | Manage Caretaker Role Binding | Super Admin | `services`, `api` | `svc.manage_role_binding`, `RoleBindingListCreateView` |
| `HM-UC-005` | Submit Hostel Accommodation Request | Student | `services`, `api` | `svc.submit_accommodation_request`, `AccommodationRequestListCreateView` |
| `HM-UC-006` | Record Hostel and Room Allotment Decisions | Super Admin | `services`, `api` | `svc.record_allotment_decision`, `BatchAllotmentDecisionView` |
| `HM-UC-007` | Central Re-allotment or Room Vacation | Super Admin | `services`, `api` | `svc.record_room_vacation`, `RoomVacationView` |
| `HM-UC-008` | View Room Allocation Information | Student | `selectors`, `api` | `sel.visible_allotments`, `AllotmentListView` |
| `HM-UC-009` | Maintain Room Availability and Occupancy | Caretaker | `services`, `api` | `RoomListCreateView`, `RoomDetailView` |
| `HM-UC-010` | Record Individual Room Exchange | Caretaker | `services`, `api` | `svc.record_room_exchange`, `RoomExchangeView` |
| `HM-UC-011` | Review Room Assignments and Occupancy | Warden | `selectors`, `api` | `sel.visible_allotments`, `sel.visible_rooms` |
| `HM-UC-012` | Record and Monitor Student Attendance | Caretaker | `services`, `api` | `svc.record_attendance`, `AttendanceListView` |
| `HM-UC-013` | View Own Attendance Information | Student | `selectors`, `api` | `sel.visible_attendance`, `AttendanceListView` |
| `HM-UC-014` | Submit Leave Request | Student | `services`, `api` | `svc.submit_leave_request`, `LeaveRequestListCreateView` |
| `HM-UC-015` | Review and Record Leave Decision | Caretaker | `services`, `api` | `svc.record_leave_decision`, `LeaveDecideView` |
| `HM-UC-016` | View Own Leave Status and History | Student | `selectors`, `api` | `sel.visible_leaves`, `LeaveRequestListCreateView` |
| `HM-UC-017` | Submit Hostel-Related Complaint | Student | `services`, `api` | `svc.submit_complaint`, `ComplaintListCreateView` |
| `HM-UC-018` | Review, Update, and Escalate Complaint | Caretaker | `services`, `api` | `svc.update_complaint_status`, `ComplaintUpdateView` |
| `HM-UC-019` | Monitor Complaint Status and History | Warden | `selectors`, `api` | `sel.visible_complaints`, `ComplaintListCreateView` |
| `HM-UC-020` | Submit Guest Room Booking Request | Student | `services`, `api` | `svc.submit_guest_room_booking`, `GuestRoomBookingListCreateView` |
| `HM-UC-021` | Review Guest Room Booking Request | Caretaker | `services`, `api` | `svc.record_guest_room_decision`, `GuestRoomDecideView` |
| `HM-UC-022` | View Own Guest-Room Booking Status | Student | `selectors`, `api` | `sel.visible_guest_bookings`, `GuestRoomBookingListCreateView` |
| `HM-UC-023` | Submit Extended-Stay Request | Student | `services`, `api` | `svc.submit_extended_stay`, `ExtendedStayListCreateView` |
| `HM-UC-024` | Review and Record Extended-Stay Decision | Warden | `services`, `api` | `svc.record_extended_stay_decision`, `ExtendedStayDecideView` |
| `HM-UC-025` | Record Extended-Stay Charge / Compliance | System / Event | `services`, `models` | Integrated into extended stay decision fields |
| `HM-UC-026` | Record Hostel Fine | Caretaker | `services`, `api` | `svc.record_hostel_fine`, `FineListCreateView` |
| `HM-UC-027` | View Own Fine Records and History | Student | `selectors`, `api` | `sel.visible_fines`, `FineListCreateView` |
| `HM-UC-028` | Maintain Hostel Inventory Records | Caretaker | `services`, `api` | `InventoryListCreateView`, `HostelInventoryItem` |
| `HM-UC-029` | Maintain Staff Duty Coordination Log | Caretaker | `services`, `api` | `StaffDutyLogListCreateView`, `HostelStaffDutyLog` |
| `HM-UC-030` | Maintain Security Guard Shift Schedule | Warden | `services`, `api` | `SecurityGuardShiftListCreateView` |
| `HM-UC-031` | Publish Hostel Notice or Announcement | Caretaker/Warden | `services`, `api` | `svc.publish_notice`, `NoticeListCreateView` |
| `HM-UC-032` | View Hostel Notices | All authorized | `selectors`, `api` | `sel.visible_notices`, `NoticeListCreateView` |
| `HM-UC-033` | Generate Reports and Operational Summaries | Caretaker/Warden/Admin | `selectors`, `api` | `sel.generate_hostel_report`, `OperationalReportView` |
| `HM-UC-034` | Issue HM Notifications / Updates | System / Event | `services`, `api` | `svc.notify_user`, `NotificationListView` |
| `HM-UC-036` | Review Attendance Summaries and Exceptions | Warden | `selectors`, `api` | `sel.visible_attendance` |
| `HM-UC-037` | Review Leave Information and Summaries | Warden | `selectors`, `api` | `sel.visible_leaves` |
| `HM-UC-038` | Review Fine Summaries and Disciplinary Patterns | Warden | `selectors`, `api` | `sel.visible_fines` |
| `HM-UC-039` | Review Staff Assignments and Shift Info | Warden/Admin | `selectors`, `api` | `sel.visible_staff_logs` |

---

## 2. Domain Model & Database Schema

All models inherit from `TimeStampedModel`. External users are referenced by plain integer `user_id`s (IAM `erp_user_id`), guaranteeing zero cross-module foreign keys.

- `Hostel`: `code` (unique, varchar 32), `name`, `gender_type`, `total_floors`, `total_rooms`, `capacity`, `is_active` (db_index).
- `HostelRoleBinding`: `hostel` (FK), `user_id` (indexed int), `role` ("warden"/"caretaker"), `shift`, `is_active`, `valid_from`, `valid_to`. Index: `(user_id, role, is_active)`.
- `Room`: `hostel` (FK), `room_number`, `floor`, `capacity`, `current_occupancy`, `status`, `room_type`. Unique: `(hostel, room_number)`.
- `AccommodationRequest`: `student_user_id` (indexed int), `preferred_hostel` (FK nullable), `academic_year`, `semester`, `preferences`, `status`, `remarks`.
- `RoomAllotment`: `student_user_id` (indexed int), `hostel` (FK), `room` (FK), `status` (active/vacated/reallotted/exchanged), `allotted_at`, `allotment_round`, `vacated_at`, `allotted_by_user_id`.
- `RoomExchange`: `hostel` (FK), `student_a_user_id`, `room_a` (FK), `student_b_user_id`, `room_b` (FK), `status`, `reason`, `processed_by_user_id`.
- `AttendanceRecord`: `hostel` (FK), `student_user_id` (indexed int), `date` (indexed date), `status` (present/absent/on_leave/late), `recorded_by_user_id`. Unique: `(student_user_id, date)`.
- `LeaveRequest`: `hostel` (FK), `student_user_id` (indexed int), `leave_type`, `start_date`, `end_date`, `reason`, `destination`, `supporting_document`, `status`, `decision_by_user_id`, `decision_at`, `decision_remarks`.
- `HostelComplaint`: `hostel` (FK), `student_user_id` (indexed int), `category`, `room` (FK nullable), `description`, `attachment`, `status`, `action_taken`, `resolved_at`, `escalated_to_user_id`, `escalated_at`, `handled_by_user_id`.
- `GuestRoomBooking`: `hostel` (FK), `room` (FK nullable), `student_user_id` (indexed int), `guest_name`, `guest_relation`, `guest_contact`, `check_in_date`, `check_out_date`, `status`, `decision_by_user_id`, `decision_at`, `decision_remarks`.
- `ExtendedStayRequest`: `hostel` (FK), `student_user_id` (indexed int), `stay_reason`, `start_date`, `end_date`, `status`, `decision_by_user_id`, `decision_at`, `decision_remarks`, `charge_amount`, `payment_deadline`, `compliance_status`.
- `HostelFine`: `hostel` (FK), `student_user_id` (indexed int), `amount`, `reason`, `imposed_date`, `status`, `issued_by_user_id`, `remarks`.
- `HostelInventoryItem`: `hostel` (FK), `item_name`, `category`, `quantity`, `condition`, `location`, `last_inspected_date`, `updated_by_user_id`, `notes`.
- `HostelStaffDutyLog`: `hostel` (FK), `staff_name`, `role`, `shift`, `date`, `duty_notes`, `recorded_by_user_id`.
- `SecurityGuardShift`: `hostel` (FK), `guard_name`, `shift`, `shift_date`, `gate_post`, `status`, `scheduled_by_user_id`, `notes`.
- `HostelNotice`: `hostel` (FK nullable), `title`, `content`, `priority`, `published_by_user_id` (indexed int), `published_at`, `is_active` (indexed bool).
- `HostelNotification`: `recipient_user_id` (indexed int), `event_type`, `title`, `message`, `is_read`.

---

## 3. Declarative State-Transition Tables

### 3.1 BW-HM-01: Accommodation Request Allotment
| From State | Event / Trigger | Actor | Guard / Condition | Resulting State |
|---|---|---|---|---|
| `[None]` | Submit Request | Student | Valid preferences & session | `submitted` |
| `submitted` | Record Allotment | Super Admin | Room occupancy < capacity (`BR-HM-010`) | `allotted` |

### 3.2 CW-HM-01: Leave Request Decision
| From State | Event / Trigger | Actor | Guard / Condition | Resulting State |
|---|---|---|---|---|
| `[None]` | Submit Leave | Student | Valid dates & reason | `submitted` |
| `submitted` | Approve Leave | Caretaker | Assigned hostel scope (`BR-HM-035`) | `approved` |
| `submitted` | Reject Leave | Caretaker | Assigned hostel scope (`BR-HM-035`) | `rejected` |

### 3.3 CW-HM-02: Complaint Handling & Escalation
| From State | Event / Trigger | Actor | Guard / Condition | Resulting State |
|---|---|---|---|---|
| `[None]` | Submit Complaint | Student | Valid category & description (`BR-HM-015`, `016`) | `submitted` |
| `submitted` | Resolve | Caretaker | Action taken recorded | `resolved` |
| `submitted` | Update Unresolved | Caretaker | Progress noted without resolution | `unresolved` |
| `submitted` / `unresolved` | Escalate | Caretaker | Supervisory issue identified (`BR-HM-017`) | `escalated` |
| `escalated` | Resolve | Caretaker / Warden | Final resolution recorded | `resolved` |

### 3.4 CW-HM-03: Guest Room Booking Decision
| From State | Event / Trigger | Actor | Guard / Condition | Resulting State |
|---|---|---|---|---|
| `[None]` | Submit Booking | Student | Valid guest details & check-in/out | `submitted` |
| `submitted` | Approve Booking | Caretaker | Guest room available | `approved` |
| `submitted` | Reject Booking | Caretaker | Lack of room availability or policy | `rejected` |

### 3.5 CW-HM-04: Extended Stay Decision
| From State | Event / Trigger | Actor | Guard / Condition | Resulting State |
|---|---|---|---|---|
| `[None]` | Submit Extended Stay | Student | Valid vacation/break dates | `submitted` |
| `submitted` | Approve Stay | Warden | Assigned hostel scope (`BR-HM-020`, `021`) | `approved` |
| `submitted` | Reject Stay | Warden | Assigned hostel scope | `rejected` |

---

## 4. Permission List & IAM Registry

### 4.1 Module Manifest
- **Code:** `hostel`
- **Label:** `Hostel Management`
- **Icon:** `FaBuilding`
- **Base Path:** `/hostel`
- **Nav Section:** `Services`
- **Status:** `active`

### 4.2 Role Grants
- **Student**: `hostel.allotment.view`, `hostel.accommodation.create`, `hostel.attendance.view_self`, `hostel.leave.create`, `hostel.leave.view_self`, `hostel.complaint.create`, `hostel.complaint.view_self`, `hostel.guestroom.create`, `hostel.guestroom.view_self`, `hostel.extendedstay.create`, `hostel.extendedstay.view_self`, `hostel.fine.view_self`, `hostel.notice.view`, `hostel.notification.view`.
- **Hostel Caretaker**: `hostel.allotment.view`, `hostel.occupancy.manage`, `hostel.occupancy.view`, `hostel.attendance.record`, `hostel.attendance.view_self`, `hostel.leave.review`, `hostel.complaint.manage`, `hostel.guestroom.manage`, `hostel.fine.record`, `hostel.inventory.manage`, `hostel.staff.manage`, `hostel.staff.view`, `hostel.notice.publish`, `hostel.notice.view`, `hostel.notification.view`, `hostel.report.view`.
- **Hostel Warden**: `hostel.allotment.view`, `hostel.occupancy.view`, `hostel.attendance.review`, `hostel.leave.oversight`, `hostel.complaint.oversight`, `hostel.extendedstay.review`, `hostel.fine.record`, `hostel.fine.oversight`, `hostel.staff.view`, `hostel.security.manage`, `hostel.notice.publish`, `hostel.notice.view`, `hostel.notification.view`, `hostel.report.view`.
- **Super Admin**: Full administrative permissions across all hostels (`hostel.hostel.manage`, `hostel.allotment.manage`, plus all operational and supervisory permissions).
