from rest_framework.permissions import BasePermission


class IsLeaveRequestOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        actor_id = getattr(getattr(request, "principal", None), "user_id", None)
        if actor_id is None:
            actor_id = getattr(request.user, "user_id", getattr(request.user, "id", None))
        return obj.user_id == actor_id
