"""OpenAPI security schemes for the two credential pools.

Without these, every view carrying a custom authenticator is emitted with no
scheme at all, and the docs read as though the endpoint is open.
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension


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
