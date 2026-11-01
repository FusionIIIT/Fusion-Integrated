# Backup and Database Archive Management System (BADMS)

BADMS is a prototype Fusion module for on-demand database snapshots and the
secure archival request path.

## Included workflow

- SysAdmin and Super Admin can create a compressed JSON snapshot of the current
  Django database. Each run records its timestamp, result, SHA-256 checksum,
  size, and audit event. Only those roles can download snapshot files.
- Students, faculty, and staff can submit archival requests with the required
  metadata and attachment. Attachments are encrypted at rest with AES-256-GCM;
  the original file is returned only through an authenticated, scope-checked API.
- HoDs can approve or reject requests from their IAM-provided department.
- SysAdmins assign authoritative classifications. Sensitive items enter a
  security review queue for IT Security before the request reaches Archived.
- The dashboard shows authorized backup and request history, with recent audit
  activity for roles that hold the audit permission.

## Local setup

Apply the `badms` migration and configure `BADMS_ARCHIVE_ENCRYPTION_KEY` as a
64-character hexadecimal value (32 random bytes) before storing any data that
must survive outside a local development environment. When unset, the app
derives a development key from Django's `SECRET_KEY`; changing that secret will
make previously uploaded attachments unreadable.

The current prototype intentionally keeps the request workflow and backup
execution small. It does not run scheduled backups, restore database snapshots,
manage global/local schedules, implement quota accounting or storage extensions,
or deliver email notifications and failure escalations. These remain follow-up
work for the remaining BADMS requirements.
