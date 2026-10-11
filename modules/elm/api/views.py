from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import DomainError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.elm.api import serializers as s
from modules.elm.selectors import queries as q
from modules.elm.services import administration as admin
from modules.elm.services import workflow as w

MODULE = HasModuleGrant("elm")
READ = HasPermission("elm.application.self", "elm.task.act", "elm.record.manage")


class ScopedView(generics.GenericAPIView):
    def get_serializer_context(self):
        return {**super().get_serializer_context(), "actor": getattr(self.request, "principal", None)}


class Applications(ScopedView, generics.ListAPIView):
    permission_classes = [MODULE, READ]
    serializer_class = s.ApplicationSerializer

    def get_queryset(self):
        return q.applications_for(getattr(self.request, "principal", None))

    @extend_schema(request=s.SubmitSerializer, responses={201: s.ApplicationSerializer})
    def post(self, request):
        payload = s.SubmitSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = w.submit(actor=request.principal, data=payload.validated_data)
        return Response(self.get_serializer(q.applications_for(request.principal).get(pk=app.pk)).data, status=201)


class ApplicationDetail(ScopedView, generics.RetrieveAPIView):
    permission_classes = [MODULE, READ]
    serializer_class = s.ApplicationSerializer

    def get_queryset(self):
        return q.applications_for(getattr(self.request, "principal", None))


class Action(ScopedView):
    permission_classes = [MODULE, HasPermission("elm.application.self", "elm.task.act")]
    serializer_class = s.ActionSerializer

    @extend_schema(responses=s.ApplicationSerializer)
    def post(self, request, pk):
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        action = data.pop("action")
        if action == "withdraw":
            app = w.withdraw(actor=request.principal, application_id=pk, revision=data["revision"])
        elif action == "replace_substitute":
            if "substitute_id" not in data:
                raise DomainError("Choose a replacement substitute.")
            app = w.replace_substitute(actor=request.principal, application_id=pk,
                                       revision=data["revision"], substitute_id=data["substitute_id"])
        else:
            data.pop("substitute_id", None)
            app = w.act(actor=request.principal, application_id=pk, action=action, **data)
        return Response(s.ApplicationSerializer(q.applications_for(request.principal).get(pk=app.pk),
                                                context=self.get_serializer_context()).data)


class Lifecycle(ScopedView):
    permission_classes = [MODULE, HasPermission("elm.application.self")]
    serializer_class = s.LifecycleSerializer

    @extend_schema(responses={201: s.ApplicationSerializer})
    def post(self, request, pk):
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = w.lifecycle(actor=request.principal, application_id=pk, **payload.validated_data)
        return Response(s.ApplicationSerializer(q.applications_for(request.principal).get(pk=app.pk),
                                                context=self.get_serializer_context()).data, status=201)


class Tasks(ScopedView, generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("elm.task.act")]
    serializer_class = s.TaskSerializer

    def get_queryset(self):
        return q.tasks_for(getattr(self.request, "principal", None))


class Accounts(APIView):
    permission_classes = [MODULE, HasPermission("elm.application.self")]

    @extend_schema(responses=s.AccountSerializer(many=True))
    def get(self, request):
        w.ensure_current_account(request.principal)
        return Response(s.AccountSerializer(q.accounts_for(request.principal), many=True).data)


class Ledger(ScopedView, generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("elm.application.self")]
    serializer_class = s.LedgerSerializer

    def get_queryset(self):
        return q.entries_for(getattr(self.request, "principal", None))


class Notifications(ScopedView, generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("elm.notification.self")]
    serializer_class = s.NotificationSerializer

    def get_queryset(self):
        return q.notifications_for(getattr(self.request, "principal", None))


class ReadNotification(APIView):
    permission_classes = [MODULE, HasPermission("elm.notification.self")]

    @extend_schema(request=None, responses={204: None})
    def post(self, request, pk):
        w.mark_notification_read(request.principal, pk)
        return Response(status=204)


class Employees(APIView):
    permission_classes = [MODULE, READ, HasPermission("elm.application.self", "elm.configuration.manage")]

    @extend_schema(responses={200: None})
    def get(self, request):
        people = directory.get_employees()
        return Response([{"user_id": p.user_id, "display_name": p.display_name, "kind": p.kind}
                         for p in people])


class Configuration(APIView):
    permission_classes = [MODULE, HasPermission("elm.configuration.manage")]

    @extend_schema(responses={200: None})
    def get(self, request):
        data = q.configuration()
        return Response({"policy": s.PolicySerializer(data["policy"]).data if data["policy"] else None,
                         "employees": s.EmployeeConfigurationSerializer(data["employees"], many=True).data,
                         "calendars": s.CalendarSerializer(data["calendars"], many=True).data,
                         "attendance_outbox": s.OutboxSerializer(data["attendance_outbox"], many=True).data})

    @extend_schema(request=s.ConfigurationSerializer, responses={204: None})
    def put(self, request):
        payload = s.ConfigurationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        admin.save_configuration(request.principal, payload.validated_data)
        return Response(status=204)


class Calendars(APIView):
    permission_classes = [MODULE, HasPermission("elm.configuration.manage")]

    @extend_schema(request=s.CalendarSerializer, responses={201: s.CalendarSerializer})
    def post(self, request):
        payload = s.CalendarSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        values = dict(payload.validated_data)
        for key in ("holidays", "restricted_holidays"):
            values[key] = [day.isoformat() for day in values[key]]
        calendar = admin.save_calendar(request.principal, values)
        return Response(s.CalendarSerializer(calendar).data, status=201)


class Offline(APIView):
    permission_classes = [MODULE, HasPermission("elm.record.manage")]

    @extend_schema(request=s.OfflineSerializer, responses={201: s.ApplicationSerializer})
    def post(self, request):
        payload = s.OfflineSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = admin.offline_entry(request.principal, payload.validated_data)
        return Response(s.ApplicationSerializer(app).data, status=201)


class Correction(APIView):
    permission_classes = [MODULE, HasPermission("elm.record.manage")]

    @extend_schema(request=s.CorrectionSerializer, responses=s.ApplicationSerializer)
    def post(self, request, pk):
        payload = s.CorrectionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = admin.correct_reference(request.principal, pk, **payload.validated_data)
        return Response(s.ApplicationSerializer(app).data)


class Export(APIView):
    permission_classes = [MODULE, HasPermission("elm.application.self")]

    @extend_schema(responses={(200, "text/plain"): str})
    def get(self, request, pk):
        app = q.applications_for(request.principal).filter(pk=pk, user_id=request.principal.user_id).first()
        if app is None:
            raise NotFoundError()
        text = (f"Employee Leave Application #{app.pk}\nCategory: {app.category}\n"
                f"Period: {app.start_date} to {app.effective_end_date}\nHalf: {app.half}\n"
                f"Status: {app.status}\nPurpose: {app.reason}\nStation leave: {app.station_details}\n")
        response = HttpResponse(text, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="leave-{app.pk}.txt"'
        return response
