# Employee Leave Management — MVP slice

This version provides a deliberately small end-to-end path:

- list the six supported leave categories (CL, RH, SCL, EL, COL, VL);
- submit a full-day leave request with dates and a reason;
- store it with the authenticated IAM user ID and `pending` status;
- list only the current user's requests and recorded statuses;
- validate dates, required reason, and overlap with an existing pending/approved
  full-day request.

The model intentionally stores `user_id` as an integer, because Fusion users are
owned by the external IAM and are not a local Django user table. The API also
requires the `elm_leave` module grant.

## API

- `GET /api/v1/elm/leave-types`
- `GET /api/v1/elm/applications`
- `POST /api/v1/elm/applications`

Example request body:

```json
{
  "leave_type": "CL",
  "start_date": "2026-11-02",
  "end_date": "2026-11-03",
  "reason": "Personal work"
}
```

The API owns the `user_id` and initial status; client-supplied values cannot
set another owner or approve a request. The employee list is scoped by the
principal returned from IAM.

## Setup

After enabling the app in settings and mounting its URL (already done in this
MVP), run the normal project commands in the configured environment:

```bash
python manage.py migrate
python manage.py seed_modules
```

Grant the `elm_leave` module to the intended user roles in IAM. The existing
client module registry already uses this code and mounts the pages under
`/apply_leave`.

## Intentionally not implemented yet

Approval routing and decisions, entitlement/balance calculations, carry-forward,
holiday-calendar and RH applicability checks, half-day requests, cancellations,
extensions, resumption review, notifications, and SLA reminders are not simulated.
The Apply Leave and Approvals screens explain the relevant limitation; new
requests remain `pending` until a later approval workflow is built. This MVP
therefore must not be treated as a complete policy-compliant leave system.
