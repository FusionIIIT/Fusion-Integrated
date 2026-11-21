from rest_framework import serializers


class FileCreateSerializer(serializers.Serializer):
    initial_comment = serializers.CharField(required=True)
    attachment_urls = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )

    def validate_initial_comment(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Initial comment cannot be empty or just whitespace."
            )
        return value


class FileEditSerializer(serializers.Serializer):
    new_comment = serializers.CharField(required=True)
    new_attachment_urls = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )

    def validate_new_comment(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "New comment cannot be empty or just whitespace."
            )
        return value


class FileDiscardSerializer(serializers.Serializer):
    pass


class FileForwardSerializer(serializers.Serializer):
    receiver_id = serializers.CharField(required=True)
    movement_comment = serializers.CharField(required=True)
    attachment_urls = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )

    def validate_movement_comment(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Movement comment cannot be empty or just whitespace."
            )
        return value


class FileReturnSerializer(serializers.Serializer):
    movement_comment = serializers.CharField(required=True)
    attachment_urls = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )

    def validate_movement_comment(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Movement comment cannot be empty or just whitespace."
            )
        return value


class FileArchiveSerializer(serializers.Serializer):
    pass


class FtsFileListSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    owner_id = serializers.SerializerMethodField()
    current_holder_id = serializers.SerializerMethodField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_id(self, obj):
        return str(obj.id)

    def get_owner_id(self, obj):
        return str(obj.owner_id)

    def get_current_holder_id(self, obj):
        return str(obj.current_holder_id) if obj.current_holder_id else None


class FtsFileCommentSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    file_id = serializers.SerializerMethodField()
    actor_id = serializers.SerializerMethodField()
    text = serializers.CharField()
    is_initial = serializers.BooleanField()
    created_at = serializers.DateTimeField()

    def get_id(self, obj):
        return str(obj.id)

    def get_file_id(self, obj):
        return str(obj.file_id)

    def get_actor_id(self, obj):
        return str(obj.actor_id)


class FtsFileAttachmentSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    file_id = serializers.SerializerMethodField()
    actor_id = serializers.SerializerMethodField()
    file_url = serializers.CharField()
    created_at = serializers.DateTimeField()

    def get_id(self, obj):
        return str(obj.id)

    def get_file_id(self, obj):
        return str(obj.file_id)

    def get_actor_id(self, obj):
        return str(obj.actor_id)


class FtsFileDetailSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    owner_id = serializers.SerializerMethodField()
    current_holder_id = serializers.SerializerMethodField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    comments = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    def get_id(self, obj):
        return str(obj.id)

    def get_owner_id(self, obj):
        return str(obj.owner_id)

    def get_current_holder_id(self, obj):
        return str(obj.current_holder_id) if obj.current_holder_id else None

    def get_comments(self, obj):
        return FtsFileCommentSerializer(obj.comments.all(), many=True).data

    def get_attachments(self, obj):
        return FtsFileAttachmentSerializer(obj.attachments.all(), many=True).data


class FtsFileMovementSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    file_id = serializers.SerializerMethodField()
    sender_id = serializers.SerializerMethodField()
    receiver_id = serializers.SerializerMethodField()
    comment = serializers.CharField()
    movement_type = serializers.CharField()
    created_at = serializers.DateTimeField()

    def get_id(self, obj):
        return str(obj.id)

    def get_file_id(self, obj):
        return str(obj.file_id)

    def get_sender_id(self, obj):
        return str(obj.sender_id)

    def get_receiver_id(self, obj):
        return str(obj.receiver_id)
