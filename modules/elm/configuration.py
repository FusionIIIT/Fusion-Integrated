from django.db import transaction
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from fusion_auth.permissions import HasModuleGrant, HasPermission, IsAuthenticatedPrincipal

from .models import AuthorityRoute, CalendarDay, LeaveEvent
from .serializers import AuthorityRouteSerializer, CalendarDaySerializer

# modules/elm/configuration.py


class AuthorityRouteViewSet(ModelViewSet):
    queryset = AuthorityRoute.objects.all().order_by("employee", "id")
    serializer_class = AuthorityRouteSerializer
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("elm"),
        HasPermission("elm.leave_policies.manage"),
    ]

    @transaction.atomic
    def perform_create(self, serializer):
        obj = serializer.save()
        self._audit(obj.pk, "CREATE")

    @transaction.atomic
    def perform_update(self, serializer):
        obj = serializer.save()
        self._audit(obj.pk, "UPDATE")

    @transaction.atomic
    def perform_destroy(self, instance):
        pk = instance.pk
        instance.delete()
        self._audit(pk, "DELETE")

    def _audit(self, pk, operation):
        uid = self.request.principal.user_id
        LeaveEvent.objects.create(
            employee=uid,
            actor=uid,
            action="CONFIGURATION_CHANGED",
            details={"entity": "AuthorityRoute", "id": pk, "operation": operation},
        )


class CalendarDayViewSet(ReadOnlyModelViewSet):
    queryset = CalendarDay.objects.all().order_by("date", "id")
    serializer_class = CalendarDaySerializer

    def get_permissions(self):
        if self.action == "publish":
            return [
                IsAuthenticatedPrincipal(),
                HasModuleGrant("elm")(),
                HasPermission("elm.leave_policies.manage")(),
            ]
        return [
            IsAuthenticatedPrincipal(),
            HasModuleGrant("elm")(),
            HasPermission("elm.leave_types.view")(),
        ]

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def publish(self, request):
        from rest_framework.exceptions import ValidationError

        year = serializers.IntegerField(min_value=2000, max_value=2100).run_validation(
            request.data.get("year")
        )
        kind = serializers.ChoiceField(choices=["CLOSED", "RH"]).run_validation(
            request.data.get("kind")
        )
        dates = serializers.ListField(
            child=serializers.DateField(), allow_empty=True
        ).run_validation(request.data.get("dates"))
        source = serializers.CharField(allow_blank=False).run_validation(request.data.get("source"))

        if any(d.year != year for d in dates):
            raise ValidationError("Date year mismatch")
        if len(set(dates)) != len(dates):
            raise ValidationError("Duplicate dates found")

        CalendarDay.objects.filter(date__year=year, kind=kind, published=True).update(
            published=False
        )

        for day in dates:
            CalendarDay.objects.update_or_create(
                date=day, kind=kind, defaults={"published": True, "source": source}
            )

        LeaveEvent.objects.create(
            employee=request.principal.user_id,
            actor=request.principal.user_id,
            action="CALENDAR_PUBLISHED",
            details={
                "year": year,
                "kind": kind,
                "dates": [d.isoformat() for d in dates],
                "source": source,
            },
        )

        return Response({"year": year, "kind": kind, "published": len(dates)})
