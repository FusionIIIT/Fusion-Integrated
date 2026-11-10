"""Local conftest for WF strategy."""


from conftest import make_session


def _login(stub_iam, user_id, kind="student", roles=("student",), permissions=()):
    session = make_session(
        user_id=user_id,
        kind=kind,
        roles=roles,
        permissions=permissions,
        modules=("lms",),
    )
    stub_iam(session)
    from rest_framework.test import APIClient

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token tok-{user_id}")
    return c
