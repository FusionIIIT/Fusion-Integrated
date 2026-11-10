"""PHC permission gates — fine-grained action codes from registry."""
from rest_framework.permissions import BasePermission


class _HasPhcPermission(BasePermission):
    codes: tuple[str, ...] = ()
    message = "You do not have permission to perform this PHC action."

    def has_permission(self, request, view):
        p = getattr(request, "principal", None)
        if p is None:
            return False
        return p.has_any_permission(*self.codes)


def HasPhcPermission(*codes: str):                          # noqa: N802
    return type("HasPhcPermission_" + "_".join(codes).replace(".", "_"),
                (_HasPhcPermission,), {"codes": codes})
