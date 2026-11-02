"""Admin configuration endpoints (lane C). Thin: validate, call a service, shape."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.csv import stream
from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.vms.api.admin import serializers as s
from modules.vms.selectors import admin as sel
from modules.vms.services import (
    audit_review,
    blacklist_admin,
    integration,
    policy_admin,
    roles,
    vip,
    zones_admin,
)

MODULE = HasModuleGrant("vms")


def _body(serializer_class, request, **kw):
    ser = serializer_class(data=request.data, **kw)
    ser.is_valid(raise_exception=True)
    return ser.validated_data


# --- roles ------------------------------------------------------------------------

class RoleListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.role.assign")]

    def get(self, request):
        rows = roles.list_active(actor=request.principal)
        return Response(s.RoleAssignmentSerializer(rows, many=True).data)

    def post(self, request):
        d = _body(s.RoleAssignInput, request)
        row = roles.assign(actor=request.principal, **d)
        return Response(s.RoleAssignmentSerializer(row).data, status=status.HTTP_201_CREATED)


class MyRolesView(APIView):
    """Any signed-in user: their own active VMS roles (BR-181)."""
    permission_classes = [MODULE]

    def get(self, request):
        rows = roles.my_roles(request.principal)
        return Response(s.RoleAssignmentSerializer(rows, many=True).data)


class RoleReassignView(APIView):
    permission_classes = [MODULE, HasPermission("vms.role.assign")]

    def post(self, request, pk):
        d = _body(s.RoleReassignInput, request)
        row, counts = roles.reassign(actor=request.principal, assignment_id=pk,
                                     new_user_id=d["user_id"], ends_at=d["ends_at"])
        return Response({**s.RoleAssignmentSerializer(row).data,
                         "handoff": counts.as_dict()}, status=status.HTTP_201_CREATED)


class RoleRevokeView(APIView):
    permission_classes = [MODULE, HasPermission("vms.role.assign")]

    def post(self, request, pk):
        row = roles.revoke(actor=request.principal, assignment_id=pk)
        return Response(s.RoleAssignmentSerializer(row).data)


# --- integrations -----------------------------------------------------------------

class IntegrationListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.integration.manage")]

    def get(self, request):
        return Response(integration.list_all(actor=request.principal))


class IntegrationView(APIView):
    permission_classes = [MODULE, HasPermission("vms.integration.manage")]

    def get(self, request, key):
        return Response(integration.get(actor=request.principal, key=key))

    def put(self, request, key):
        d = _body(s.IntegrationInput, request)
        return Response(integration.set_value(actor=request.principal, key=key,
                                              value=d["value"]))


# --- vip --------------------------------------------------------------------------

class VipListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.vip.manage")]

    def get(self, request):
        rows = vip.list_permissions(actor=request.principal,
                                    active_only=request.query_params.get("active") == "1")
        return Response(s.VipSerializer(rows, many=True).data)

    def post(self, request):
        d = _body(s.VipGrantInput, request)
        row = vip.grant(actor=request.principal, **d)
        return Response(s.VipSerializer(row).data, status=status.HTTP_201_CREATED)


class VipRevokeView(APIView):
    permission_classes = [MODULE, HasPermission("vms.vip.manage")]

    def post(self, request, pk):
        row = vip.revoke(actor=request.principal, vip_id=pk)
        return Response(s.VipSerializer(row).data)


# --- policies ---------------------------------------------------------------------

_POLICY_READ = HasPermission("vms.policy.manage", "vms.policy.publish")


class PolicyListView(APIView):
    def get_permissions(self):
        perm = _POLICY_READ if self.request.method == "GET" \
            else HasPermission("vms.policy.manage")
        return [MODULE(), perm()]

    def get(self, request):
        rows = policy_admin.list_policies(actor=request.principal)
        return Response(s.PolicySerializer(rows, many=True).data)

    def post(self, request):
        d = _body(s.PolicyCreateInput, request)
        row = policy_admin.create_draft(actor=request.principal, base_id=d["base_id"])
        return Response(s.PolicySerializer(row).data, status=status.HTTP_201_CREATED)


class PolicyDetailView(APIView):
    def get_permissions(self):
        perm = _POLICY_READ if self.request.method == "GET" \
            else HasPermission("vms.policy.manage")
        return [MODULE(), perm()]

    def get(self, request, pk):
        return Response(s.PolicySerializer(policy_admin.get(pk)).data)

    def patch(self, request, pk):
        d = dict(_body(s.PolicyUpdateInput, request))
        zone_ids = d.pop("restricted_zone_ids", None)
        row = policy_admin.update_draft(actor=request.principal, policy_id=pk,
                                        changes=d, restricted_zone_ids=zone_ids)
        return Response(s.PolicySerializer(row).data)


class PolicyPublishView(APIView):
    permission_classes = [MODULE, HasPermission("vms.policy.publish")]

    def post(self, request, pk):
        row = policy_admin.publish(actor=request.principal, policy_id=pk)
        return Response(s.PolicySerializer(row).data)


class PolicyDiffView(APIView):
    permission_classes = [MODULE, _POLICY_READ]

    def get(self, request, a, b):
        return Response(policy_admin.diff(actor=request.principal, a_id=a, b_id=b))


# --- blacklist --------------------------------------------------------------------

class BlacklistView(APIView):
    """Flat entry list/add kept from the first version of the API. POST adds to
    the open draft (created if none): nothing is enforced until published (BR-120)."""

    def get_permissions(self):
        return [MODULE(), HasPermission("vms.blacklist.manage")()]

    def get(self, request):
        return Response(s.BlacklistEntrySerializer(sel.blacklist_entries(), many=True).data)

    def post(self, request):
        d = _body(s.BlacklistEntryInput, request)
        draft = blacklist_admin.open_draft(actor=request.principal)
        entry = blacklist_admin.add_entry(actor=request.principal, version_id=draft.pk, **d)
        return Response(s.BlacklistEntrySerializer(entry).data,
                        status=status.HTTP_201_CREATED)


class BlacklistVersionListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.blacklist.manage")]

    def get(self, request):
        return Response(s.BlacklistVersionSerializer(sel.blacklist_versions(),
                                                     many=True).data)

    def post(self, request):
        v = blacklist_admin.create_version(actor=request.principal)
        return Response(s.BlacklistVersionSerializer(v).data, status=status.HTTP_201_CREATED)


class BlacklistEntryListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.blacklist.manage")]

    def get(self, request, pk):
        blacklist_admin.get_version(pk)
        return Response(s.BlacklistEntrySerializer(sel.blacklist_entries(pk),
                                                   many=True).data)

    def post(self, request, pk):
        d = _body(s.BlacklistEntryInput, request)
        entry = blacklist_admin.add_entry(actor=request.principal, version_id=pk, **d)
        return Response(s.BlacklistEntrySerializer(entry).data,
                        status=status.HTTP_201_CREATED)


class BlacklistEntryDetailView(APIView):
    permission_classes = [MODULE, HasPermission("vms.blacklist.manage")]

    def patch(self, request, pk, entry_id):
        ser = s.BlacklistEntryInput(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        entry = blacklist_admin.update_entry(actor=request.principal, version_id=pk,
                                             entry_id=entry_id, **ser.validated_data)
        return Response(s.BlacklistEntrySerializer(entry).data)

    def delete(self, request, pk, entry_id):
        """Deactivates; an entry is never removed."""
        entry = blacklist_admin.deactivate_entry(actor=request.principal, version_id=pk,
                                                 entry_id=entry_id)
        return Response(s.BlacklistEntrySerializer(entry).data)


class BlacklistPublishView(APIView):
    permission_classes = [MODULE, HasPermission("vms.blacklist.publish")]

    def post(self, request, pk):
        v = blacklist_admin.publish(actor=request.principal, version_id=pk)
        return Response(s.BlacklistVersionSerializer(v).data)


# --- safe list --------------------------------------------------------------------

class SafeListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.safelist.manage")]

    def get(self, request):
        rows = sel.safelist(active_only=request.query_params.get("active") == "1")
        return Response(s.SafeListSerializer(rows, many=True).data)

    def post(self, request):
        d = _body(s.SafeListInput, request)
        row = blacklist_admin.add_safelist(
            actor=request.principal, id_doc_number=d["visitor_id_doc_number"],
            reason=d["reason"], expires_at=d["expires_at"])
        return Response(s.SafeListSerializer(row).data, status=status.HTTP_201_CREATED)


class SafeListRevokeView(APIView):
    permission_classes = [MODULE, HasPermission("vms.safelist.manage")]

    def post(self, request, pk):
        row = blacklist_admin.revoke_safelist(actor=request.principal, entry_id=pk)
        return Response(s.SafeListSerializer(row).data)


# --- zones and gates --------------------------------------------------------------

def _patch(serializer_class, request):
    ser = serializer_class(data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    return dict(ser.validated_data)


class ZoneListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.zone.manage")]

    def get(self, request):
        return Response(s.ZoneSerializer(sel.zones(), many=True).data)

    def post(self, request):
        d = _body(s.ZoneInput, request)
        zone = zones_admin.create_zone(
            actor=request.principal, name=d["name"],
            is_restricted=d.get("is_restricted", False),
            parent_zone_id=d.get("parent_zone_id"))
        return Response(s.ZoneSerializer(zone).data, status=status.HTTP_201_CREATED)


class ZoneDetailView(APIView):
    permission_classes = [MODULE, HasPermission("vms.zone.manage")]

    def patch(self, request, pk):
        zone = zones_admin.update_zone(actor=request.principal, zone_id=pk,
                                       **_patch(s.ZoneInput, request))
        return Response(s.ZoneSerializer(zone).data)


class GateListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.zone.manage")]

    def get(self, request):
        return Response(s.GateSerializer(sel.gates(), many=True).data)

    def post(self, request):
        d = _body(s.GateInput, request)
        gate = zones_admin.create_gate(actor=request.principal, name=d["name"],
                                       zone_id=d["zone_id"],
                                       device_id=d.get("device_id", ""))
        return Response(s.GateSerializer(gate).data, status=status.HTTP_201_CREATED)


class GateDetailView(APIView):
    permission_classes = [MODULE, HasPermission("vms.zone.manage")]

    def patch(self, request, pk):
        gate = zones_admin.update_gate(actor=request.principal, gate_id=pk,
                                       **_patch(s.GateInput, request))
        return Response(s.GateSerializer(gate).data)


# --- audit (read only: no write verbs are routed) ---------------------------------

class AuditListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.audit.view")]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        f = s.AuditFilterInput(data=request.query_params)
        f.is_valid(raise_exception=True)
        qs = audit_review.search(actor=request.principal, **f.filters())
        pager = CursorPagination()
        page = pager.paginate_queryset(qs, request, view=self)
        return pager.get_paginated_response(s.AuditRowSerializer(page, many=True).data)


class AuditExportView(APIView):
    permission_classes = [MODULE, HasPermission("vms.audit.view")]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        f = s.AuditFilterInput(data=request.query_params)
        f.is_valid(raise_exception=True)
        rows = audit_review.export_rows(actor=request.principal, **f.filters())
        return stream(filename="vms-audit.csv", header=audit_review.EXPORT_HEADER,
                      rows=rows)
