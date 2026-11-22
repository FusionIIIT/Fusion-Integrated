# VMS deployment requirements

VMS identity documents are private security data. Deployment is ready only when
the deployment host provides the storage, antivirus, broker and email services
described here. The API fails closed for gate entry while a document is pending,
infected, or could not be scanned.

## Runtime configuration

Set these values in `/etc/fusion/platform.env` (mode `0640`, owned by
`root:fusion`):

```dotenv
VMS_ID_FINGERPRINT_KEY=<independent stable secret>
VMS_ID_UPLOAD_ROOT=/var/lib/fusion/platform/vms-identity
VMS_CLAMD_SOCKET=/run/clamav/clamd.ctl
VMS_PUBLIC_BASE_URL=https://<public-host>
```

`VMS_ID_FINGERPRINT_KEY` is required for stable identity matching and must be
independent from Django's signing key. Provision the identity directory on the
persistent volume writable by the `fusion` service account. The application
creates private directories and files (`0700` and `0600`) and refuses a
production storage root inside the code checkout or Placement storage.

Install and run ClamAV `clamd` on the same host. Configure its local Unix socket
at the selected path and grant the `fusion` account read/write access to that
socket (for example, a dedicated shared group with socket mode `0660`). Keep the
scanner socket local; VMS does not accept a remote scanner endpoint. The worker
and beat units must be enabled. The worker's `default` queue handles document
scan tasks; beat retries pending scans every minute. A missing scanner is a
deployment check failure, and documents remain unavailable for gate access.

Install the Python project dependencies so `pikepdf` is present. Visitor PDFs
are bounded, checked for active/embedded actions, rewritten, and stripped of
document metadata before storage. The scanner performs a ClamAV `INSTREAM`
request against the exact private file. Only clean files are available to
authorized Admin and Security Personnel, as attachments with `no-store` and
`nosniff` headers.

Nginx grants a 6 MB request allowance only to pre-registration and gate walk-in
uploads; the application enforces a 5 MB file cap. Other API bodies remain
limited to 1 MB. Keep both limits aligned if routes or deployment prefixes are
changed.

## Release procedure

The existing `ops/deploy/deploy.sh` runs migrations, module seeding, permission
manifest checks, Django deploy checks, and the platform smoke checks. This
branch adds an initial VMS schema plus additive visitor-document and event-batch
migrations. Configure the environment and scanner before the deploy check; do
not disable a failed scanner check to make deployment pass. Confirm production
SMTP is configured, since host decisions and visitor credentials are delivered
through the transactional outbox.

Before accepting real visitors, the Student 2 review should exercise upload
limits, allowed and mismatched file signatures, PDF active-content rejection,
scanner clean/infected/unavailable outcomes, restricted document downloads,
event guest CSV partial outcomes, idempotent retries, event overflow/rate caps,
and migration from an empty database. This repository work has not run those
spec tests or a production deployment.

## Supported integration boundary

The directory adapter and institutional email path use existing platform
contracts. Other configured integrations remain disabled until the external
system owner supplies its approved API contract, endpoint, service identity,
network policy and credentials. VMS does not guess external write or validation
semantics. A saved integration setting is not evidence that a connector is
available, and runtime gate validation does not trust an unverified setting.

Event guest CSVs contain one `visit_id` column and reference existing visits
that have already been approved by their Host, have a live pass, and have a
clean identity-document scan. Import creates an auditable accepted/rejected row
per visit, assigns accepted passes to the event, and does not bypass the Host
approval process. Security Personnel can view event controls, attendance counts,
and import outcomes; only Admin can change event lifecycle, controls, or imports.
