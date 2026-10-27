TITLE: Rename ApplySerializer so it does not collide with placement's in the OpenAPI schema
FORMAT: diff
EDIT: modules/leave/api/serializers.py modules/leave/api/views.py
LIMIT: 600
POST: none
---
After task 015 the only remaining schema warning is: Encountered 2 components with identical names "Apply" and different identities modules.placement.api.serializers.ApplySerializer and modules.leave.api.serializers.ApplySerializer. drf-spectacular names components after the class, so rename the leave class. Fix only this, with SEARCH/REPLACE edits:

1. In modules/leave/api/serializers.py rename `class ApplySerializer(serializers.Serializer):` to `class LeaveApplySerializer(serializers.Serializer):`.
2. In modules/leave/api/views.py replace every use of the name ApplySerializer (in the import list, in the @extend_schema(request=...) decorator and in the post method) with LeaveApplySerializer.

Do not change anything else.
