"""Explicit fields everywhere; every server-owned field is read-only."""

from rest_framework import serializers

from modules.department.domain.rules import (
    FEEDBACK_CATEGORIES,
    GENERAL_FIELDS,
    OFFICIAL_FIELDS,
    PROFILE_KINDS,
)
from modules.department.models import (
    Announcement,
    Department,
    Feedback,
    FeedbackNote,
    InventoryItem,
    LabResource,
    OfficialChange,
    RoleTenure,
    StockMovement,
    StockRequest,
    TimetableSlot,
)

# Column limits: a larger number is a 400, never a database error (500).
MAX_ID = 2_147_483_647
MAX_QUANTITY = 1_000_000
#: R5-05: a full week for one department; the clash check grows with the square of the batch.
MAX_SLOTS_PER_UPLOAD = 500


def _one_of(values, **kwargs):
    """A choice kept out of the schema's shared enum names, which other modules also use."""

    def check(value):
        if value not in values:
            raise serializers.ValidationError(
                f"Choose one of: {', '.join(v or '(empty)' for v in values)}."
            )

    return serializers.CharField(
        max_length=max(len(v) for v in values), validators=[check], **kwargs
    )


class DeptHeadshipSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(read_only=True)
    display_name = serializers.CharField(read_only=True)


class DeptDepartmentSerializer(serializers.ModelSerializer):
    headship = serializers.SerializerMethodField()
    programmes = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "code", "name", "core_policies", *GENERAL_FIELDS, "headship", "programmes"]
        read_only_fields = fields

    def get_headship(self, obj) -> DeptHeadshipSerializer(allow_null=True):
        return self.context.get("headships", {}).get(obj.pk)

    def get_programmes(self, obj) -> list[str]:
        return self.context.get("programmes", [])


class DeptGeneralUpdateSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    contact_email = serializers.EmailField(required=False, allow_blank=True, max_length=254)
    contact_phone = serializers.CharField(required=False, allow_blank=True, max_length=30)
    office_location = serializers.CharField(required=False, allow_blank=True, max_length=120)
    website = serializers.URLField(required=False, allow_blank=True, max_length=200)
    name = serializers.CharField(required=False, max_length=120)
    core_policies = serializers.CharField(required=False, allow_blank=True)


class DeptOfficialChangeSerializer(serializers.ModelSerializer):
    department = serializers.CharField(source="department.code", read_only=True)

    class Meta:
        model = OfficialChange
        fields = [
            "id",
            "department",
            "field",
            "proposed_value",
            "previous_value",
            "status",
            "proposed_by",
            "decided_by",
            "decided_at",
            "reason",
            "created_at",
        ]
        read_only_fields = fields


class DeptOfficialChangeWriteSerializer(serializers.Serializer):
    field = serializers.ChoiceField(choices=OFFICIAL_FIELDS)
    value = serializers.CharField(allow_blank=True, max_length=10000)


class DeptDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500, default="")


class DeptAnnouncementSerializer(serializers.ModelSerializer):
    department = serializers.CharField(source="department.code", read_only=True)

    class Meta:
        model = Announcement
        fields = [
            "id",
            "department",
            "title",
            "body",
            "audience_role",
            "programme",
            "batch_year",
            "status",
            "author_id",
            "published_at",
            "edited_at",
        ]
        read_only_fields = fields


class DeptAnnouncementWriteSerializer(serializers.Serializer):
    title = serializers.CharField(allow_blank=True, max_length=200)
    body = serializers.CharField(allow_blank=True, max_length=10000)
    audience_role = serializers.CharField(max_length=10)
    programme = serializers.CharField(required=False, allow_blank=True, max_length=40, default="")
    batch_year = serializers.IntegerField(
        required=False, allow_null=True, default=None, min_value=2000, max_value=2100
    )


class DeptAnnouncementEditSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=200)
    body = serializers.CharField(required=False, allow_blank=True, max_length=10000)
    audience_role = serializers.CharField(required=False, max_length=10)
    programme = serializers.CharField(required=False, allow_blank=True, max_length=40)
    batch_year = serializers.IntegerField(
        required=False, allow_null=True, min_value=2000, max_value=2100
    )


class DeptInventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ["id", "name", "unit", "current_quantity", "updated_at"]
        read_only_fields = fields


class DeptInventoryItemWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    unit = serializers.CharField(max_length=20, required=False, default="unit")
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY)
    note = serializers.CharField(required=False, allow_blank=True, max_length=300, default="")


class DeptReceiptSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY)
    note = serializers.CharField(required=False, allow_blank=True, max_length=300, default="")


class DeptStockMovementSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "item",
            "item_name",
            "kind",
            "quantity",
            "actor_id",
            "stock_request",
            "note",
            "created_at",
        ]
        read_only_fields = fields


class DeptStockRequestSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    unit = serializers.CharField(source="item.unit", read_only=True)

    class Meta:
        model = StockRequest
        fields = [
            "id",
            "item",
            "item_name",
            "unit",
            "requester_id",
            "quantity",
            "purpose",
            "status",
            "decided_by",
            "decided_at",
            "reason",
            "issued_by",
            "issued_at",
            "created_at",
        ]
        read_only_fields = fields


class DeptStockRequestWriteSerializer(serializers.Serializer):
    item = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY)
    purpose = serializers.CharField(required=False, allow_blank=True, max_length=300, default="")


class DeptFeedbackNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackNote
        fields = ["id", "author_id", "body", "created_at"]
        read_only_fields = fields


class DeptFeedbackSerializer(serializers.ModelSerializer):
    notes = DeptFeedbackNoteSerializer(many=True, read_only=True)

    class Meta:
        model = Feedback
        fields = [
            "id",
            "subject",
            "body",
            "category",
            "status",
            "submitter_id",
            "submitter_kind",
            "reviewed_at",
            "disposed_at",
            "resolution_note",
            "created_at",
            "notes",
        ]
        read_only_fields = fields


class DeptFeedbackWriteSerializer(serializers.Serializer):
    subject = serializers.CharField(allow_blank=True, max_length=200)
    body = serializers.CharField(allow_blank=True, max_length=10000)


class DeptFeedbackReviewSerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=["", *FEEDBACK_CATEGORIES], required=False, default=""
    )
    disposition = _one_of(("", "resolved", "closed"), required=False, allow_blank=True, default="")
    note = serializers.CharField(required=False, allow_blank=True, max_length=5000, default="")


class DeptFeedbackDisposeSerializer(serializers.Serializer):
    outcome = _one_of(("resolved", "closed"))
    note = serializers.CharField(required=False, allow_blank=True, max_length=5000, default="")


class DeptFeedbackNoteWriteSerializer(serializers.Serializer):
    body = serializers.CharField(allow_blank=True, max_length=5000)


class DeptTimetableSlotSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(read_only=True)

    class Meta:
        model = TimetableSlot
        fields = [
            "id",
            "kind",
            "programme",
            "batch_year",
            "course_code",
            "day_of_week",
            "starts_at",
            "ends_at",
            "room",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class DeptTimetableSlotWriteSerializer(serializers.Serializer):
    kind = _one_of(("class", "lab"))
    programme = serializers.CharField(required=False, allow_blank=True, max_length=40, default="")
    batch_year = serializers.IntegerField(
        required=False, allow_null=True, default=None, min_value=2000, max_value=2100
    )
    course_code = serializers.CharField(max_length=20)
    day_of_week = serializers.IntegerField(min_value=0, max_value=6)
    starts_at = serializers.TimeField()
    ends_at = serializers.TimeField()
    room = serializers.CharField(required=False, allow_blank=True, max_length=40, default="")


class DeptTimetableUploadSerializer(serializers.Serializer):
    slots = DeptTimetableSlotWriteSerializer(many=True, allow_empty=False)

    def validate_slots(self, slots):
        if len(slots) > MAX_SLOTS_PER_UPLOAD:
            raise serializers.ValidationError(
                f"Upload at most {MAX_SLOTS_PER_UPLOAD} slots at a time; split the timetable "
                "into smaller batches."
            )
        return slots


class DeptTimetableSlotEditSerializer(serializers.Serializer):
    kind = _one_of(("class", "lab"), required=False)
    programme = serializers.CharField(required=False, allow_blank=True, max_length=40)
    batch_year = serializers.IntegerField(
        required=False, allow_null=True, min_value=2000, max_value=2100
    )
    course_code = serializers.CharField(required=False, max_length=20)
    day_of_week = serializers.IntegerField(required=False, min_value=0, max_value=6)
    starts_at = serializers.TimeField(required=False)
    ends_at = serializers.TimeField(required=False)
    room = serializers.CharField(required=False, allow_blank=True, max_length=40)


class DeptLabResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabResource
        fields = ["id", "name", "location", "equipment", "capacity", "status", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class DeptLabResourceEditSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    location = serializers.CharField(required=False, allow_blank=True, max_length=120)
    equipment = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    capacity = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=100_000
    )
    status = serializers.ChoiceField(choices=[c for c, _ in LabResource.STATUS], required=False)


class DeptProfileViewSerializer(serializers.Serializer):
    """Output only. Fields beyond the viewer's tier are absent, not null (BR-DEPT-019)."""

    tier = serializers.CharField()
    id = serializers.IntegerField()
    kind = serializers.CharField()
    display_name = serializers.CharField()
    programme = serializers.CharField()
    department = serializers.CharField()
    email = serializers.CharField(required=False)
    office = serializers.CharField(required=False)
    research_interests = serializers.CharField(required=False)
    current_position = serializers.CharField(required=False)
    user_id = serializers.IntegerField(required=False, allow_null=True)
    username = serializers.CharField(required=False)
    discipline = serializers.CharField(required=False)
    batch_year = serializers.IntegerField(required=False, allow_null=True)
    bio = serializers.CharField(required=False)
    graduation_year = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)

    def to_representation(self, instance):
        return dict(instance)


class DeptProfileWriteSerializer(serializers.Serializer):
    kind = _one_of(PROFILE_KINDS)
    user_id = serializers.IntegerField(
        required=False, allow_null=True, default=None, min_value=1, max_value=MAX_ID
    )
    display_name = serializers.CharField(
        required=False, allow_blank=True, max_length=150, default=""
    )
    office = serializers.CharField(required=False, allow_blank=True, max_length=120, default="")
    research_interests = serializers.CharField(
        required=False, allow_blank=True, max_length=5000, default=""
    )
    bio = serializers.CharField(required=False, allow_blank=True, max_length=5000, default="")
    graduation_year = serializers.IntegerField(
        required=False, allow_null=True, default=None, min_value=1990, max_value=2100
    )
    current_position = serializers.CharField(
        required=False, allow_blank=True, max_length=150, default=""
    )


class DeptProfileEditSerializer(serializers.Serializer):
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    office = serializers.CharField(required=False, allow_blank=True, max_length=120)
    research_interests = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    bio = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    graduation_year = serializers.IntegerField(
        required=False, allow_null=True, min_value=1990, max_value=2100
    )
    current_position = serializers.CharField(required=False, allow_blank=True, max_length=150)
    is_active = serializers.BooleanField(required=False)


class DeptRoleTenureSerializer(serializers.ModelSerializer):
    department = serializers.CharField(source="department.code", read_only=True)
    in_effect = serializers.SerializerMethodField()

    class Meta:
        model = RoleTenure
        fields = [
            "id",
            "department",
            "role",
            "user_id",
            "valid_from",
            "valid_to",
            "assigned_by",
            "transition_applied_at",
            "in_effect",
        ]
        read_only_fields = fields

    def get_in_effect(self, obj) -> bool:
        now = self.context["now"]
        return obj.valid_from <= now < obj.valid_to


class DeptRoleTenureWriteSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=12)
    role = serializers.ChoiceField(choices=["hod", "dept_admin"])
    user_id = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    valid_from = serializers.DateTimeField()
    valid_to = serializers.DateTimeField()


class DeptRoleTenureEditSerializer(serializers.Serializer):
    valid_to = serializers.DateTimeField()


class DeptRoleWarningSerializer(serializers.Serializer):
    department = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    problem = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)


class DeptActingSerializer(serializers.Serializer):
    role = serializers.CharField(read_only=True, allow_null=True)
    department = serializers.CharField(read_only=True, allow_null=True)
