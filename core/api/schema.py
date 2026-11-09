"""OpenAPI security schemes for the two credential pools.

Without these, every view carrying a custom authenticator is emitted with no
scheme at all, and the docs read as though the endpoint is open.
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView


class IamSessionScheme(OpenApiAuthenticationExtension):
    target_class = "fusion_auth.authentication.IamSessionAuthentication"
    name = "iamSession"

    def get_security_definition(self, auto_schema):
        # Declared as the header form: the one a generated client can set.
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": (
                "`Token <value>` from the IAM, or the httpOnly "
                "`auth_token` cookie the SPA carries."),
        }


class RecruiterScheme(OpenApiAuthenticationExtension):
    target_class = "modules.placement.authentication.RecruiterAuthentication"
    name = "recruiterSession"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": (
                "`Recruiter <value>` for an external company account, or the "
                "httpOnly `recruiter_session` cookie set at portal login. "
                "A separate pool from institute users."),
        }


class VisitorSessionScheme(OpenApiAuthenticationExtension):
    target_class = "modules.vms.auth.VisitorSessionAuthentication"
    name = "visitorSession"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "vms_visitor",
            "description": (
                "OTP-verified visitor session cookie (not an IAM principal). "
                "Mutating calls also carry the CSRF header."),
        }


class UntypedBodyAutoSchema(AutoSchema):
    """AutoSchema that stays quiet for a bare APIView with no serializer hook.

    Several modules hand-build their JSON payloads (the VMS service layer
    returns dicts). Those views are still listed, path and auth included, with
    an untyped body, instead of failing `spectacular --fail-on-warn` once per
    method. A view that declares a serializer or `@extend_schema` is unaffected.
    """

    def _get_serializer(self):
        view = self.view
        if (not isinstance(view, GenericAPIView) and isinstance(view, APIView)
                and not any(hasattr(view, a) for a in (
                    "get_serializer", "get_serializer_class", "serializer_class"))):
            return None
        return super()._get_serializer()
