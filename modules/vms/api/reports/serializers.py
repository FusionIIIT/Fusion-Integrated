"""Query-string input for reports. Validation lives in services.reports.validate."""
from rest_framework import serializers


class ReportQuery(serializers.Serializer):
    date = serializers.DateField(required=False)
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)
    zone = serializers.IntegerField(required=False, min_value=1)
    # A ChoiceField, not a BooleanField: DRF reads an absent boolean in a query
    # string as False, which would switch anonymisation off by default.
    anonymize = serializers.ChoiceField(choices=["true", "false"], required=False)
    granularity = serializers.ChoiceField(choices=["day", "week", "month"], required=False)
    top = serializers.IntegerField(required=False, min_value=1)
    visitor_id = serializers.IntegerField(required=False, min_value=1)

    def params(self) -> dict:
        return dict(self.validated_data)
