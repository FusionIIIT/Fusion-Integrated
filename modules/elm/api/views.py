from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.domain.rules import ENTITLEMENTS


class LeaveCatalogView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get(self, request):
        return Response({"entitlements": {key: str(value) for key, value in ENTITLEMENTS.items()}})
