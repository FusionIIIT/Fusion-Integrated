from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from core.api.exceptions import PermissionDeniedError
from modules.oap import models, services
from . import serializers as s

def actor(request): return request.principal
def require(request, permission):
    if not actor(request).has_permission(permission): raise PermissionDeniedError()

class MineList(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    permission = ""
    def get_queryset(self): return self.model.objects.filter(student_user_id=actor(self.request).user_id).order_by("-created_at")
    def perform_create(self, serializer):
        require(self.request, self.permission)
        serializer.save(student_user_id=actor(self.request).user_id)

class LeaveList(MineList):
    model, serializer_class, permission = models.LeaveApplication, s.LeaveSerializer, "oap.leave.self"
class BonafideList(MineList):
    model, serializer_class, permission = models.BonafideRequest, s.BonafideSerializer, "oap.bonafide.self"
class ClaimList(MineList):
    model, serializer_class, permission = models.AssistantshipClaim, s.ClaimSerializer, "oap.assistantship.self"
    def perform_create(self, serializer):
        require(self.request, self.permission)
        uid = actor(self.request).user_id
        try:
            thesis = models.ThesisSupervisorAssignment.objects.get(student_user_id=uid)
            ta = models.TaSupervisorAssignment.objects.get(student_user_id=uid)
        except (models.ThesisSupervisorAssignment.DoesNotExist, models.TaSupervisorAssignment.DoesNotExist):
            from core.api.exceptions import ConflictError
            raise ConflictError("supervisor_assignments_required")
        serializer.save(student_user_id=uid, thesis_supervisor_user_id=thesis.supervisor_user_id, ta_supervisor_user_id=ta.supervisor_user_id)
class SeminarList(MineList):
    model, serializer_class, permission = models.GraduateSeminar, s.SeminarSerializer, "oap.seminar.self"

class NoDuesList(MineList):
    model, serializer_class, permission = models.NoDuesRequest, s.NoDuesSerializer, "oap.no_dues.self"
    def perform_create(self, serializer):
        require(self.request, self.permission)
        request = services.start_no_dues(student_user_id=actor(self.request).user_id)
        serializer.instance = request
