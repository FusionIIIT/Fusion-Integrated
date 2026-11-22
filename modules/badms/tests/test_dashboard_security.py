"""Regression security tests for BADMS dashboard frontend.

Verifies SEC-FE-001:
- modules/badms/templates/badms/dashboard.html does not assign untrusted API data to innerHTML.
- Template rendering enforces context-safe escaping on user-submitted fields.
- Dynamic DOM generation safely sets textContent rather than string HTML interpolation.
"""

import os
from django.template.loader import render_to_string
from django.test import SimpleTestCase


class DashboardFrontendSecurityTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "templates",
            "badms",
            "dashboard.html",
        )
        with open(cls.template_path, "r", encoding="utf-8") as f:
            cls.template_content = f.read()

    def test_no_inner_html_assignments_in_template(self):
        """Ensure no dynamic assignments to innerHTML exist in client-side scripts."""
        self.assertNotIn(
            ".innerHTML",
            self.template_content,
            "dashboard.html must not use .innerHTML to avoid stored/DOM XSS vulnerabilities.",
        )

    def test_safe_dom_node_and_text_content_used(self):
        """Ensure DOM construction uses document.createElement and textContent."""
        self.assertIn("document.createElement", self.template_content)
        self.assertIn(".textContent", self.template_content)

    def test_server_rendered_user_input_is_autoescaped(self):
        """Ensure Django template autoescaping neutralizes XSS payloads in recent_backups and archival_ledger."""
        malicious_filename = '<script>alert("xss")</script>'
        context = {
            "storage_quota": {
                "used_storage_mb": 100,
                "allocated_storage_mb": 1000,
                "usage_percentage": 10,
            },
            "recent_backups": [
                {
                    "dataset_name": malicious_filename,
                    "backup_type": "FULL",
                    "status": "COMPLETED",
                    "created_at": "2026-11-19",
                    "checksum_sha256": "abc12345",
                }
            ],
            "archival_requests": [
                {
                    "request_number": "REQ-001",
                    "file_name": malicious_filename,
                    "file_size_mb": 25,
                    "department_id": "CSE",
                    "initial_classification": "ROUTINE",
                    "authoritative_classification": "ROUTINE",
                    "status": "APPROVED",
                    "retention_years": 5,
                }
            ],
        }

        rendered = render_to_string("badms/dashboard.html", context)
        self.assertNotIn(
            malicious_filename,
            rendered,
            "Raw unescaped script tag payload must not appear in rendered HTML.",
        )
        self.assertIn(
            "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;",
            rendered,
            "Malicious script tags must be entity-escaped by Django template engine.",
        )
