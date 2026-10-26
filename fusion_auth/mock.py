"""Mock IAM client for local development when Fusion_System_Administrator is not running."""
from __future__ import annotations

import contextlib
import json
from collections.abc import Sequence
from pathlib import Path

from django.conf import settings

from fusion_auth.client import IamSession, UserRef


class DevMockIamClient:
    """Mock IAM client that resolves logins and sessions locally during development."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: int | None = None,
    ):
        self._active_roles: dict[str, str] = {}
        self._tokens: dict[str, str] = {}

    def _get_all_permissions(self) -> frozenset[str]:
        manifest_path = Path(settings.BASE_DIR) / "registry" / "permissions.json"
        perms: set[str] = set()
        if manifest_path.exists():
            with contextlib.suppress(Exception):
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                for mod in data.get("modules", {}).values():
                    for p in mod.get("permissions", []):
                        perms.add(p["code"])
        perms.update([
            "placement_cell.job_posting.view",
            "placement_cell.job_posting.manage",
            "placement_cell.application.review",
            "placement_cell.application.view",
            "placement_cell.announcement.publish",
            "placement_cell.report.view",
            "placement_cell.academic_directory.view",
            "elm.leave.apply",
            "elm.leave.cancel",
            "elm.leave.view",
            "elm.leave.substitute_action",
            "elm.leave.recommend",
            "elm.leave.sanction",
            "elm.leave.admin",
            "directory.user.search",
        ])
        return frozenset(perms)

    def login(self, username: str, password: str) -> str | None:
        username = (username or "").strip()
        if not username:
            return None
        token = f"dev-mock-tok-{username}"
        self._tokens[token] = username
        return token

    def logout(self, auth_token: str) -> None:
        self._tokens.pop(auth_token, None)

    def set_active_role(self, auth_token: str, role: str) -> None:
        self._active_roles[auth_token] = role

    def resolve_session(
        self,
        *,
        auth_token: str | None = None,
        cookies: dict | None = None,
    ) -> IamSession | None:
        token = auth_token or (cookies or {}).get(settings.IAM_AUTH_COOKIE_NAME)
        if not token:
            return None

        username = self._tokens.get(token)
        if not username and token.startswith("dev-mock-tok-"):
            username = token.removeprefix("dev-mock-tok-")
        if not username:
            username = "admin"

        user_id = 9001
        display_name = username.capitalize()
        kind = "faculty"
        email = f"{username}@iiitdmj.ac.in"
        discipline = "CSE"
        batch_year = 2023

        with contextlib.suppress(Exception):
            from modules.directory.models import UserRef as UserRefModel

            user_obj = UserRefModel.objects.filter(username=username).first()
            if not user_obj and username.isdigit():
                user_obj = UserRefModel.objects.filter(user_id=int(username)).first()
            if not user_obj and username.startswith("u") and username[1:].isdigit():
                user_obj = UserRefModel.objects.filter(user_id=int(username[1:])).first()

            if user_obj:
                user_id = user_obj.user_id
                display_name = user_obj.display_name or username
                kind = user_obj.kind or "student"
                email = user_obj.email or email
                discipline = user_obj.discipline or discipline
                batch_year = user_obj.batch_year or batch_year
            elif username == "admin":
                user_id = 9001
                display_name = "System Admin (Dr. Meera Nair)"
                kind = "faculty"

        roles = ("admin", "faculty", "student", "placement_officer", "HOD", "Dean Academic")
        active_role = self._active_roles.get(token, "faculty" if kind != "student" else "student")

        return IamSession(
            user_id=user_id,
            username=username,
            display_name=display_name,
            kind=kind,
            email=email,
            active_role=active_role,
            roles=roles,
            permissions=self._get_all_permissions(),
            modules=("placement_cell", "elm"),
            navigation=(),
        )

    def get_users(self, user_ids: Sequence[int]) -> dict[int, UserRef]:
        result = {}
        with contextlib.suppress(Exception):
            from modules.directory.models import UserRef as UserRefModel

            for obj in UserRefModel.objects.filter(user_id__in=user_ids):
                result[obj.user_id] = UserRef(
                    user_id=obj.user_id,
                    username=obj.username,
                    display_name=obj.display_name,
                    kind=obj.kind,
                    email=obj.email,
                    department=obj.department,
                    programme=obj.programme,
                    discipline=obj.discipline,
                    batch_year=obj.batch_year,
                    is_active=obj.is_active,
                    resume_link=obj.resume_link,
                    profile_completed=obj.profile_completed,
                )
        return result

    def search_users(
        self,
        q: str = "",
        kind: str | None = None,
        limit: int = 25,
    ) -> list[UserRef]:
        with contextlib.suppress(Exception):
            from modules.directory.models import UserRef as UserRefModel

            qs = UserRefModel.objects.all()
            if kind:
                qs = qs.filter(kind=kind)
            if q:
                qs = qs.filter(display_name__icontains=q)
            return [
                UserRef(
                    user_id=obj.user_id,
                    username=obj.username,
                    display_name=obj.display_name,
                    kind=obj.kind,
                    email=obj.email,
                    department=obj.department,
                    programme=obj.programme,
                    discipline=obj.discipline,
                    batch_year=obj.batch_year,
                    is_active=obj.is_active,
                )
                for obj in qs[:limit]
            ]
        return []

    def count_employees(self) -> int:
        with contextlib.suppress(Exception):
            from modules.directory.models import UserRef as UserRefModel

            return UserRefModel.objects.filter(
                kind__in=("faculty", "staff"),
                is_active=True,
            ).count()
        return 0

    def iter_employees(self, *, page_size: int = 500):
        with contextlib.suppress(Exception):
            from modules.directory.models import UserRef as UserRefModel

            for obj in UserRefModel.objects.filter(
                kind__in=("faculty", "staff"),
                is_active=True,
            ):
                yield UserRef(
                    user_id=obj.user_id,
                    username=obj.username,
                    display_name=obj.display_name,
                    kind=obj.kind,
                    email=obj.email,
                    department=obj.department,
                    programme=obj.programme,
                    discipline=obj.discipline,
                    batch_year=obj.batch_year,
                    is_active=obj.is_active,
                )

    def academic_directory(self, **filters):
        return {"count": 0, "results": []}

    def academic_filters(self):
        return {
            "disciplines": ["CSE", "ECE", "ME"],
            "batch_years": [2022, 2023, 2024],
            "programmes": ["B.Tech", "M.Tech"],
        }

    def get_academic_standings(self, user_ids):
        return {}
