# Complaint submission

This module implements the frozen CMS submission slice. A signed-in user submits a category and description, with optional multipart file attachments, at `POST /api/v1/complaints/`. The response includes a unique UUID reference and the recorded submission time. Submission and its pending confirmation notification record commit atomically.

Attachments stream to `COMPLAINT_ATTACHMENT_ROOT`, outside the repository, with private directory and file permissions. Each stored file has a random storage key and SHA-256 digest. The exact accepted content types, maximum file size, and maximum file count are institutional settings: configure `COMPLAINT_ATTACHMENT_CONTENT_TYPES` as a comma-separated list, `COMPLAINT_ATTACHMENT_MAX_BYTES` as an integer, and `COMPLAINT_ATTACHMENT_MAX_COUNT` as an integer. An unset constraint is not applied. Startup checks reject a storage path inside the project tree.

The confirmation event is stored in the CMS notification outbox in the submission transaction. `complaints.deliver_notifications` sends it using Django's configured email backend, retries failures up to `COMPLAINT_NOTIFICATION_MAX_ATTEMPTS`, and is scheduled once per minute on the notifications queue. A missing email address remains an actionable failed notification after retries; configure IAM email data and the deployment mail backend for delivery.

The implementation traces CFR-CMS-001, AFR-CMS-001–009, UC-CMS-001, BR-CMS-001–006, and BW-CMS-01 step 1 to the `ComplaintSubmitView`, `submit` service, `deliver_pending` service, and complaint models. The full CMS lifecycle remains outside the submission slice.
