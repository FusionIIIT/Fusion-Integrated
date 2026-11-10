"""Explicit browser smoke: requires running Vite, Node Playwright, and Chromium.

Run .venv/bin/pytest ops/smoke/test_iaa_browser.py -o addopts='' -q.
Uses an isolated test DB and fake IAM; never exposes a real development login.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import make_session
from modules.iaa.domain.rules import Role
from modules.iaa.models import FinancialRequest
from modules.iaa.tests.conftest import (
    GRANTS,
    PEOPLE,
    world,  # noqa: F401 -- register the shared pytest fixture
)


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("world")
def test_browser_full_expense_lifecycle(live_server, stub_iam, tmp_path):
    fake = stub_iam(users=PEOPLE)

    def resolve(*, auth_token=None, cookies=None):
        uid = int(auth_token.removeprefix("iaa-smoke-"))
        return make_session(
            user_id=uid,
            kind="staff",
            roles=(GRANTS[uid],),
            active_role=GRANTS[uid],
            modules=("institute_accounts_audits",),
            permissions=("institute_accounts_audits.workspace.access",),
        )

    fake.resolve_session = resolve
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(  # noqa: S603 -- fixed local test script, no shell input
        [shutil.which("node"), str(root / "client/e2e/iaa-smoke.cjs")],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env={
            **os.environ,
            "IAA_API_ORIGIN": live_server.url,
            "IAA_SCREENSHOT": str(tmp_path / "iaa-browser.png"),
        },
    )
    assert result.returncode == 0, result.stdout + result.stderr
    req = FinancialRequest.objects.get()
    assert req.status == "recorded"
    assert req.processing_reference == "Browser internal completion"
    assert list(
        req.history.filter(action="approve").order_by("id").values_list("active_role", flat=True)
    ) == [Role.HOD, Role.DEAN, Role.DIRECTOR]
