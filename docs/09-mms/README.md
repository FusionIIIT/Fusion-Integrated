# Mess Management System (MMS) Module Documentation
**Module Code**: `mms`  
**Base Path**: `/mms`  
**API Prefix**: `/api/v1/mms/`  
**Pair**: 16B  
**Student 1 (Builder)**: Vishvajeet  
**Student 2 (Reviewer/Tester)**: Shaheen  

---

## 1. Overview
The Mess Management System (MMS) provides digital management of student dining operations, dietary accommodations, billing, leaves (rebates), feedback, vacation food continuity surveys, and announcements for the institute.

---

## 2. Actors & Access Rights

| Actor | IAM Designation | Role Grant | Key Capabilities |
| :--- | :--- | :--- | :--- |
| **Student** | `student` | `student` | Submit registrations, deregistrations, rebates, special food requests, feedback; respond to vacation surveys; view weekly menus and monthly bills. |
| **Mess Caretaker** | `caretaker` | `Mess Caretaker` | Open registration windows; review and decide registrations, deregistrations, rebates, and special food requests; manage weekly menus; generate, finalize, and publish monthly bills; launch vacation surveys; publish announcements; view operational reports. |
| **Mess Warden** | `warden` | `Mess Warden` | View menus, announcement history, student feedback; inspect vacation survey summaries; view supervisory financial and participation reports; publish supervisory announcements. |
| **Mess Admin** | `mess_admin` | `Mess Admin` | Assign and reassign the active Mess Caretaker and Mess Warden. Mid-cycle reassignments take immediate effect. Strictly isolated from operational food/billing data. |

---

## 3. Architecture & Standards Compliance

- **Framework**: Django 5.2 + Django REST Framework + Celery + React 18 + Mantine 7.13 + TanStack Query 5.
- **Pure Python Domain**: `modules/mms/domain/` contains zero framework imports (`django`, `rest_framework`, `celery`). All state transitions and guard validations are declarative and pure.
- **Contract Boundary**: Modules interact strictly via plural getters in `modules/mms/contracts.py`.
- **Zero Cross-Module Foreign Keys**: User references are plain `IntegerField` (`user_id`, `employee_user_id`, `student_user_id`).
- **Transactional Outbox**: Notifications commit in the exact transaction of the triggering event via `NotificationOutbox` and are delivered asynchronously with exponential backoff and deduplication.

---

## 4. API Endpoints

| Method | Endpoint | Description | Permission |
| :--- | :--- | :--- | :--- |
| `GET` / `POST` | `/api/v1/mms/registration-requests/` | List or submit mess registration requests | `mms.registration.create` / `review` |
| `POST` | `/api/v1/mms/registration-requests/<id>/decision/` | Approve or reject registration request | `mms.registration.review` |
| `GET` / `POST` | `/api/v1/mms/registration-window/` | View or open registration windows | `mms.registration.window.manage` |
| `GET` / `POST` | `/api/v1/mms/deregistration-requests/` | List or submit deregistration requests | `mms.deregistration.create` / `review` |
| `POST` | `/api/v1/mms/deregistration-requests/<id>/decision/` | Approve or reject deregistration | `mms.deregistration.review` |
| `GET` / `POST` | `/api/v1/mms/rebate-requests/` | List or submit rebate requests (min 3 days) | `mms.rebate.create` / `review` |
| `POST` | `/api/v1/mms/rebate-requests/<id>/decision/` | Approve or reject rebate request | `mms.rebate.review`, `mms.rebate.update` |
| `GET` / `POST` | `/api/v1/mms/special-food-requests/` | List or submit special food requests (>= 1 day lead) | `mms.special_food.create` / `review` |
| `POST` | `/api/v1/mms/special-food-requests/<id>/decision/` | Approve or reject special food request | `mms.special_food.review` |
| `POST` | `/api/v1/mms/special-food-requests/<id>/fulfill/` | Record Served or Cancelled fulfillment | `mms.special_food.update` |
| `GET` | `/api/v1/mms/menu/` | View weekly breakfast, lunch, dinner menu | `mms.menu.view` |
| `POST` / `DELETE`| `/api/v1/mms/menu/items/` | Add or delete menu items | `mms.menu.manage` |
| `GET` | `/api/v1/mms/bills/` | View monthly bills (scoped) | `mms.billing.view_self` / `review` |
| `POST` | `/api/v1/mms/bills/generate/` | Generate monthly bills for registered students | `mms.billing.manage` |
| `POST` | `/api/v1/mms/bills/<id>/finalize/` | Finalize generated monthly bill | `mms.billing.approve` |
| `POST` | `/api/v1/mms/bills/<id>/publish/` | Publish finalized monthly bill | `mms.billing.publish` |
| `GET` / `POST` | `/api/v1/mms/feedback/` | Submit or review student feedback | `mms.feedback.create` / `view` |
| `GET` / `POST` | `/api/v1/mms/surveys/` | View or create vacation continuity surveys | `mms.survey.create` |
| `POST` | `/api/v1/mms/surveys/<id>/respond/` | Respond Yes or No to survey | `mms.survey_response.create` |
| `GET` | `/api/v1/mms/survey-summary/` | Aggregated Yes/No/Default-No counts | `mms.survey.view_summary` |
| `GET` / `POST` | `/api/v1/mms/announcements/` | View or publish announcements | `mms.announcement.publish` / `view` |
| `GET` | `/api/v1/mms/announcements/history/` | Historical archive of all announcements | `mms.announcement.view` |
| `GET` | `/api/v1/mms/reports/operational/` | Caretaker operational summary metrics | `mms.report.operational` |
| `GET` | `/api/v1/mms/reports/supervisory/` | Warden financial & participation metrics | `mms.report.supervisory` |
| `GET` / `POST` | `/api/v1/mms/roles/` | List or assign active Caretaker and Warden | `mms.role.assign` |
| `GET` | `/api/v1/mms/requests/` | Unified student requests overview | `mms.request.view_self` |

---

## 5. Scheduled Tasks & Worker Queues

- `mms.deliver_notifications`: Drains `NotificationOutbox` every 60 seconds (queue: `notifications`).
- `mms.default_reject_special_food`: Automatically rejects requests past `decision_due_at` every 5 minutes (queue: `default`).
- `mms.default_vacation_response`: Automatically records `default_no` for non-responding students upon survey deadline expiration (queue: `default`).
- `mms.activate_deregistration`: Makes approved deregistrations effective on next calendar day at 00:05 UTC (queue: `default`).
- `mms.generate_monthly_bills`: Monthly billing event on the 1st of each calendar month at 01:00 UTC (queue: `billing`).
- `mms.send_vacation_reminder`: Daily reminder enqueuer for open vacation surveys at 09:00 UTC (queue: `default`).

---

## 6. Management Commands

- `python manage.py send_mms_notifications [--status] [--limit N] [--retry-failed]`: Drains or inspects the MMS outbox.
- `python manage.py mms_scheduled_work_status [--max-lag SECONDS]`: Assesses outbox lag, overdue special food decisions, and expired surveys.
