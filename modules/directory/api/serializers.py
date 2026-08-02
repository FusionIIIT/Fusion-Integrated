"""Wire shapes for the directory's read endpoints."""
from rest_framework import serializers


class UserRefSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    display_name = serializers.CharField(allow_blank=True)
    kind = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    department = serializers.CharField(allow_blank=True)
    programme = serializers.CharField(allow_blank=True)
    discipline = serializers.CharField(allow_blank=True)
    batch_year = serializers.IntegerField(allow_null=True)


class UserSearchResultSerializer(serializers.Serializer):
    results = UserRefSerializer(many=True)
