"""Blacklist and policy endpoints. TODO lane C: replace with
services/blacklist_admin.py and services/policy_admin.py."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasPermission
from modules.vms.api.admin.serializers import BlacklistSerializer, PolicySerializer
from modules.vms.models import AccessPolicy, BlacklistEntry
from modules.vms.services import blacklist, policy


class BlacklistView(APIView):
    permission_classes = [HasPermission("vms.blacklist.manage")]

    def get(self, request):
        rows = BlacklistEntry.objects.order_by("-id")
        return Response(BlacklistSerializer(rows, many=True).data)

    def post(self, request):
        ser = BlacklistSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        entry = blacklist.add_entry(actor=request.principal, **ser.validated_data)
        return Response(BlacklistSerializer(entry).data, status=status.HTTP_201_CREATED)


class PolicyListView(APIView):
    permission_classes = [HasPermission("vms.policy.publish")]

    def get(self, request):
        rows = AccessPolicy.objects.order_by("-version")
        return Response(PolicySerializer(rows, many=True).data)


class PolicyPublishView(APIView):
    permission_classes = [HasPermission("vms.policy.publish")]

    def post(self, request, pk):
        published = policy.publish(policy_id=pk, actor=request.principal)
        if published is None:
            raise NotFoundError("Policy not found.")
        return Response(PolicySerializer(published).data)
