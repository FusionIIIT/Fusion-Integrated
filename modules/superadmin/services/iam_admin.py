"""Allowlisted authenticated requests to IAM administration endpoints."""
from __future__ import annotations

from typing import Any

import requests
from django.conf import settings

from fusion_auth.client import IamUnavailable


class IamAdminError(Exception):
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"IAM returned HTTP {status_code}.")


class IamAdmin:
    """Proxy documented IAM routes without storing identity data locally."""

    def request(self, token: str, method: str, path: str, *, params=None,
                json_body=None, files=None):
        if not token:
            raise ValueError("An authenticated IAM token is required.")
        prefix = settings.IAM_API_PREFIX.strip("/")
        url = f"{settings.IAM_BASE_URL.rstrip('/')}/{prefix}/{path.lstrip('/')}"
        headers = {"Authorization": f"Token {token}", "Accept": "application/json"}
        try:
            response = requests.request(
                method, url, headers=headers, params=params, json=json_body,
                files=files, timeout=settings.IAM_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise IamUnavailable("Identity service is unavailable.") from exc
        try:
            payload = response.json() if response.content else None
        except ValueError:
            payload = {"detail": "Identity service returned an invalid response."}
        if not response.ok:
            raise IamAdminError(response.status_code, payload)
        return payload

    def list_users(self, token: str, user_type: str, filters=None):
        if user_type not in {"student", "faculty", "staff"}:
            raise ValueError("type must be student, faculty, or staff.")
        params = {**(filters or {}), "type": user_type}
        return self.request(token, "GET", "users/", params=params)

    def user_roles(self, token: str, username: str):
        return self.request(token, "GET", "get-user-roles-by-username/",
                            params={"username": username})

    def list_roles(self, token: str):
        return self.request(token, "GET", "view-roles/")

    def create_user(self, token: str, user_type: str, payload: dict):
        if user_type not in {"faculty", "staff"}:
            raise ValueError("IAM documents individual creation only for faculty and staff.")
        return self.request(token, "POST", f"users/add-{user_type}/", json_body=payload)

    def replace_user_roles(self, token: str, username: str, roles: list):
        return self.request(token, "PUT", "update-user-roles/",
                            json_body={"username": username, "roles": roles})

    def reset_password(self, token: str, username: str):
        return self.request(token, "POST", "users/reset_password/",
                            json_body={"username": username})

    def bulk_import(self, token: str, csv_file):
        return self.request(token, "POST", "users/import/", files={"file": csv_file})
