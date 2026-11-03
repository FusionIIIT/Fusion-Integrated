"""PMS antivirus scanning adapter. It fails closed when no scanner is configured."""

import logging
import shlex
import subprocess

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from modules.pms.models import ApplicationDocument, PmsAuditEvent

log = logging.getLogger("fusion.pms.scan")


def scan_document(document_id: int) -> str:
    with transaction.atomic():
        doc = (
            ApplicationDocument.objects.select_for_update()
            .select_related("application")
            .get(pk=document_id)
        )
        if doc.malware_scan_status != "pending":
            return doc.malware_scan_status
        command = getattr(settings, "PMS_MALWARE_SCAN_COMMAND", "")
        if not command:
            doc.malware_scan_status = "unavailable"
            doc.save(update_fields=["malware_scan_status"])
            PmsAuditEvent.objects.create(
                application=doc.application,
                action="document_scan_unavailable",
                metadata={"document_id": doc.pk, "reason": "scanner_not_configured"},
            )
            return doc.malware_scan_status
        try:
            file_path = doc.file.path
            result = subprocess.run(  # noqa: S603  # Admin-configured scanner, no shell.
                [*shlex.split(command), "--no-summary", file_path],
                check=False,
                capture_output=True,
                text=True,
                timeout=90,
            )
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            doc.malware_scan_status = "unavailable"
            doc.save(update_fields=["malware_scan_status"])
            PmsAuditEvent.objects.create(
                application=doc.application,
                action="document_scan_unavailable",
                metadata={"document_id": doc.pk, "reason": type(exc).__name__},
            )
            log.warning("pms.scan.unavailable document=%s reason=%s", doc.pk, type(exc).__name__)
            return doc.malware_scan_status
        if result.returncode == 0:
            doc.malware_scan_status = "clean"
            action = "document_scan_clean"
        elif result.returncode == 1:
            doc.malware_scan_status = "infected"
            action = "document_scan_infected"
        else:
            doc.malware_scan_status = "unavailable"
            action = "document_scan_unavailable"
        doc.save(update_fields=["malware_scan_status"])
        PmsAuditEvent.objects.create(
            application=doc.application,
            action=action,
            metadata={
                "document_id": doc.pk,
                "scanner_exit_code": result.returncode,
                "scanned_at": timezone.now().isoformat(),
            },
        )
        return doc.malware_scan_status


def scan_pending_documents(limit=100):
    ids = list(
        ApplicationDocument.objects.filter(malware_scan_status="pending")
        .order_by("uploaded_at")
        .values_list("pk", flat=True)[:limit]
    )
    return sum(scan_document(pk) in ("clean", "infected") for pk in ids)
