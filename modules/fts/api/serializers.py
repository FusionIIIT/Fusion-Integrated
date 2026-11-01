from rest_framework import serializers

class FileCreateSerializer(serializers.Serializer):
    initial_comment = serializers.CharField(required=True)
    attachment_urls = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)

    def validate_initial_comment(self, value):
        if not value.strip():
            raise serializers.ValidationError("Initial comment cannot be empty or just whitespace.")
        return value


class FileEditSerializer(serializers.Serializer):
    new_comment = serializers.CharField(required=True)
    new_attachment_urls = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)

    def validate_new_comment(self, value):
        if not value.strip():
            raise serializers.ValidationError("New comment cannot be empty or just whitespace.")
        return value


class FileDiscardSerializer(serializers.Serializer):
    pass


class FileForwardSerializer(serializers.Serializer):
    receiver_id = serializers.CharField(required=True)
    movement_comment = serializers.CharField(required=True)
    attachment_urls = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)

    def validate_movement_comment(self, value):
        if not value.strip():
            raise serializers.ValidationError("Movement comment cannot be empty or just whitespace.")
        return value


class FileReturnSerializer(serializers.Serializer):
    movement_comment = serializers.CharField(required=True)
    attachment_urls = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)

    def validate_movement_comment(self, value):
        if not value.strip():
            raise serializers.ValidationError("Movement comment cannot be empty or just whitespace.")
        return value
