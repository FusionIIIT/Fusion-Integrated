"""API views for MMS endpoints."""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.mms.models import (
    MessRegistrationWindow,
    MessMenu,
    MessAnnouncement,
)
from modules.mms.api.serializers import (
    MessRegistrationWindowSerializer,
    MessRegistrationSerializer,
    MessDeregistrationSerializer,
    MessMenuSerializer,
    MessRebateSerializer,
    SpecialFoodRequestSerializer,
    MessBillSerializer,
    MessAnnouncementSerializer,
    MessFeedbackSerializer,
)
from modules.mms.selectors import scoping


class MenuListView(APIView):
    serializer_class = MessMenuSerializer

    def get(self, request):
        actor = getattr(request, "principal", None) or request.user
        qs = scoping.visible_menus(actor)
        return Response(MessMenuSerializer(qs, many=True).data)


class AnnouncementListView(APIView):
    serializer_class = MessAnnouncementSerializer

    def get(self, request):
        actor = getattr(request, "principal", None) or request.user
        qs = scoping.visible_announcements(actor)
        return Response(MessAnnouncementSerializer(qs, many=True).data)


class RegistrationListView(APIView):
    serializer_class = MessRegistrationSerializer

    def get(self, request):
        actor = getattr(request, "principal", None) or request.user
        qs = scoping.visible_registrations(actor)
        return Response(MessRegistrationSerializer(qs, many=True).data)


class DeregistrationListView(APIView):
    serializer_class = MessDeregistrationSerializer

    def get(self, request):
        actor = getattr(request, "principal", None) or request.user
        qs = scoping.visible_deregistrations(actor)
        return Response(MessDeregistrationSerializer(qs, many=True).data)


class RebateListView(APIView):
    serializer_class = MessRebateSerializer

    def get(self, request):
        actor = getattr(request, "principal", None) or request.user
        qs = scoping.visible_rebates(actor)
        return Response(MessRebateSerializer(qs, many=True).data)


class SpecialFoodListView(APIView):
    serializer_class = SpecialFoodRequestSerializer

    def get(self, request):
        actor = getattr(request, "principal", None) or request.user
        qs = scoping.visible_special_food_requests(actor)
        return Response(SpecialFoodRequestSerializer(qs, many=True).data)


class BillListView(APIView):
    serializer_class = MessBillSerializer

    def get(self, request):
        actor = getattr(request, "principal", None) or request.user
        qs = scoping.visible_bills(actor)
        return Response(MessBillSerializer(qs, many=True).data)


class FeedbackListView(APIView):
    serializer_class = MessFeedbackSerializer

    def get(self, request):
        actor = getattr(request, "principal", None) or request.user
        qs = scoping.visible_feedback(actor)
        return Response(MessFeedbackSerializer(qs, many=True).data)
