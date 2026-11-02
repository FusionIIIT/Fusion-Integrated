# Department module

This first version adds a Department module to Fusion with targeted announcements, inventory and stock request workflows, confidential feedback review, lab resource profiles, timetable entries, and department details. The backend scopes records to the department assigned to the signed-in person in the IAM directory projection. Identity references are numeric IDs; the module does not own or write user accounts.

## Workflows included

- Faculty, Dept_Admin, and HOD can publish announcements for selected roles, programmes, and academic years. HOD can edit, hide, or soft-delete active announcements.
- Dept_Admin can record stock insertions. Faculty requests available stock, HOD approves or rejects, and Dept_Admin issues approved requests. Insertions and issues append stock movement records; issues decrement the item quantity.
- Students and Faculty can submit feedback and view their own submissions. Dept_Admin performs initial review and categorization. HOD only sees reviewed feedback. Dept_Admin and HOD can resolve or close reviewed feedback.
- Dept_Admin can manage resource profiles and timetable slots. Saving an overlapping slot for the same room and day is blocked.
- Dept_Admin can update general details and submit official detail proposals. HOD approval applies an official change; rejection leaves the effective value unchanged. Headship cannot be edited through this workflow.
- Students can view programme information and timetable entries for their directory programme and batch year.

## Deliberate first-version limits

- Profile management and the full field-level profile visibility matrix are not included. User identities remain owned by IAM, and the baseline does not specify the exact sensitive fields.
- Central, time-bounded HOD and Dept_Admin assignment, immediate IAM access transitions, and Headship synchronization are not included. They require an IAM-side integration that this repo does not currently expose to the Department module.
- System/email notifications are not included because the baseline leaves the delivery channel open and this module has no existing notification adapter.
- Timetable overlap currently means overlapping times in the same room on the same day. The baseline leaves the domain-specific conflict definition open.
- Announcement targeting requires explicit role, programme, and academic-year values. No wildcard interpretation is assumed. Directory `batch_year` is used as the academic-year match in this basic version.
- Department scope uses the directory projection's `department` text value. User records must use the same value for the same department or access will fail closed.
- The module assumes the signed-in principal's `active_role` and the IAM directory designation strings match the lowercase IDs `student`, `faculty`, `dept_admin`, and `hod` used by its grants. Confirm these mappings before enabling access.
- Inventory quantity is checked when a request is submitted. The baseline does not define reservations or a second check at issuance, so multiple pending requests can collectively exceed stock.

## Local setup notes

The module and its API/client routes are registered in Fusion's source configuration. A Department-owned initial migration is supplied for the new tables, but it has not been applied. No existing Fusion database was migrated or edited. The permission manifest and module registry must be seeded by an administrator before users receive access; no seed command was run. The IAM must recognize the `student`, `faculty`, `dept_admin`, and `hod` designations used in `registry.py`.
