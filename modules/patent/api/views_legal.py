from rest_framework import generics, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from fusion_auth.permissions import HasModuleGrant, HasPermission

from ..models import (
    PatentApplication, AttorneyAssignment, PatentabilityOpinion,
    Budget, Filing, OfficeAction, MaintenanceRecord, ApplicationHistory
)
from ..services.legal import (
    assign_attorney, respond_to_assignment, record_opinion, propose_budget, decide_budget,
    record_filing
)
from ..services.post_filing import (
    record_office_action, prepare_response, approve_response, submit_response,
    record_grant, schedule_maintenance, decide_renewal
)


# --- Permission Classes ---

class AttorneyAssignmentListMixin(generics.ListAPIView):
    """Base mixin for list views that filter by the requesting principal."""
    
    permission_classes = [HasModuleGrant("patent")]
    
    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if not principal:
            return AttorneyAssignment.objects.none()
        
        # Filter based on user kind/role logic (simplified for this step)
        user_kind = getattr(principal, 'kind', None)
        
        if user_kind == 'student':  # Applicant
            # Applicants can see assignments for their own applications
            return AttorneyAssignment.objects.filter(
                application__applicant_id=principal.user_id
            ).order_by('-created_at')
        elif user_kind == 'director':
            # Directors can see assignments for applications assigned to them
            return AttorneyAssignment.objects.filter(
                application__assigned_director_id=principal.user_id
            ).order_by('-created_at')
        elif user_kind == 'admin':  # PCC_ADMIN
            return AttorneyAssignment.objects.all().order_by('-created_at')
        else:  # Default to self or all if logic is complex, here we assume admin access for safety in this snippet context or extend based on specific role checks
            return AttorneyAssignment.objects.all().order_by('-created_at')


# --- Legal Service Views ---

class AssignAttorneyView(generics.UpdateAPIView):
    """Assign an attorney to an approved application."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.legal.review")]
    
    def put(self, request, *args, **kwargs):
        try:
            app = PatentApplication.objects.get(pk=kwargs['pk'])
            
            data = request.data
            admin_id = request.principal.user_id if hasattr(request, 'principal') else None
            attorney_id = data.get('attorney_id')
            
            # Validate and assign via service
            assignment = assign_attorney(
                admin_id=admin_id,
                application_id=app.id,
                attorney_id=attorney_id
            )
            
            return Response({'id': assignment.id, 'status': assignment.status}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RespondToAssignmentView(generics.UpdateAPIView):
    """Record an attorney's response to an assignment."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.legal.review")]
    
    def put(self, request, *args, **kwargs):
        try:
            assignment = AttorneyAssignment.objects.get(pk=kwargs['pk'])
            
            data = request.data
            attorney_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and respond via service
            application = respond_to_assignment(
                attorney_id=attorney_id,
                assignment_id=assignment.id,
                accept=data.get('accept', False),
                reason=data.get('reason', '')
            )
            
            return Response({'id': application.id, 'status': application.status}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MyAttorneyAssignmentsView(AttorneyAssignmentListMixin):
    """Retrieve attorney assignments for the current user's applications."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.legal.review")]
    
    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if not principal:
            return AttorneyAssignment.objects.none()
        
        user_kind = getattr(principal, 'kind', None)
        
        if user_kind == 'student':  # Applicant
            return AttorneyAssignment.objects.filter(
                application__applicant_id=principal.user_id
            ).order_by('-created_at')
        elif user_kind == 'director':
            return AttorneyAssignment.objects.filter(
                application__assigned_director_id=principal.user_id
            ).order_by('-created_at')
        elif user_kind == 'admin':  # PCC_ADMIN
            return AttorneyAssignment.objects.all().order_by('-created_at')
        else:
            return AttorneyAssignment.objects.none()


# --- Legal Service Views (Opinion & Budget) ---

class RecordOpinionView(generics.CreateAPIView):
    """Record a patentability opinion by the assigned attorney."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.legal.review")]
    
    def create(self, request, *args, **kwargs):
        try:
            app = PatentApplication.objects.get(pk=kwargs['pk'])
            
            data = request.data
            attorney_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and record opinion via service
            opinion = record_opinion(
                attorney_id=attorney_id,
                application_id=app.id,
                novelty=data.get('novelty', False),
                non_obviousness=data.get('non_obviousness', False),
                utility=data.get('utility', False),
                recommendation=data.get('recommendation'),
                text=data.get('text', '')
            )
            
            return Response(PatentabilityOpinionSerializer(opinion).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProposeBudgetView(generics.CreateAPIView):
    """Propose a budget for an approved application."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.legal.review")]
    
    def create(self, request, *args, **kwargs):
        try:
            app = PatentApplication.objects.get(pk=kwargs['pk'])
            
            data = request.data
            admin_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and propose budget via service
            budget = propose_budget(
                admin_id=admin_id,
                application_id=app.id,
                filing_fee=data.get('filing_fee', 0),
                attorney_fee=data.get('attorney_fee', 0),
                admin_cost=data.get('admin_cost', 0)
            )
            
            return Response(BudgetSerializer(budget).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DecideBudgetView(generics.UpdateAPIView):
    """Decide on a budget proposal."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.budget.approve")]
    
    def put(self, request, *args, **kwargs):
        try:
            budget = Budget.objects.get(pk=kwargs['pk'])
            
            data = request.data
            director_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and decide via service
            updated_budget, escalated = decide_budget(
                director_id=director_id,
                budget_id=budget.id,
                approve=data.get('approve', False),
                justification=data.get('justification', ''),
                threshold=data.get('threshold', 0)
            )
            
            return Response(BudgetSerializer(updated_budget).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- Legal Service Views (Filing) ---

class RecordFilingView(generics.CreateAPIView):
    """Record an external patent filing."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.filing.record")]
    
    def create(self, request, *args, **kwargs):
        try:
            app = PatentApplication.objects.get(pk=kwargs['pk'])
            
            data = request.data
            attorney_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and record filing via service
            filing = record_filing(
                attorney_id=attorney_id,
                application_id=app.id,
                office=data.get('office', ''),
                filing_number=data.get('filing_number', ''),
                filing_date=data.get('filing_date'),
                international=data.get('international', False)
            )
            
            return Response(FilingSerializer(filing).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- Post-Filing Service Views ---

class RecordOfficeActionView(generics.CreateAPIView):
    """Record an office action received from the patent office."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.filing.record")]
    
    def create(self, request, *args, **kwargs):
        try:
            app = PatentApplication.objects.get(pk=kwargs['pk'])
            
            data = request.data
            attorney_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and record OA via service
            oa = record_office_action(
                attorney_id=attorney_id,
                application_id=app.id,
                received_date=data.get('received_date'),
                response_due_date=data.get('response_due_date'),
                description=data.get('description', '')
            )
            
            return Response(OfficeActionSerializer(oa).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PrepareResponseView(generics.UpdateAPIView):
    """Prepare an office action response."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.filing.record")]
    
    def put(self, request, *args, **kwargs):
        try:
            oa = OfficeAction.objects.get(pk=kwargs['pk'])
            
            data = request.data
            attorney_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and prepare response via service
            updated_oa = prepare_response(
                attorney_id=attorney_id,
                office_action_id=oa.id,
                response_text=data.get('response_text', ''),
                needs_applicant_approval=data.get('needs_applicant_approval', False)
            )
            
            return Response(OfficeActionSerializer(updated_oa).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ApproveResponseView(generics.UpdateAPIView):
    """Approve an office action response."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.filing.record")]
    
    def put(self, request, *args, **kwargs):
        try:
            oa = OfficeAction.objects.get(pk=kwargs['pk'])
            
            # Validate and approve response via service
            updated_oa = approve_response(
                applicant_id=request.principal.user_id if hasattr(request, 'principal') else None,
                office_action_id=oa.id
            )
            
            return Response(OfficeActionSerializer(updated_oa).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SubmitResponseView(generics.UpdateAPIView):
    """Submit an office action response."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.filing.record")]
    
    def put(self, request, *args, **kwargs):
        try:
            oa = OfficeAction.objects.get(pk=kwargs['pk'])
            
            # Validate and submit response via service
            updated_oa = submit_response(
                attorney_id=request.principal.user_id if hasattr(request, 'principal') else None,
                office_action_id=oa.id
            )
            
            return Response(OfficeActionSerializer(updated_oa).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RecordGrantView(generics.UpdateAPIView):
    """Record a patent grant."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.filing.record")]
    
    def put(self, request, *args, **kwargs):
        try:
            app = PatentApplication.objects.get(pk=kwargs['pk'])
            
            data = request.data
            attorney_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and record grant via service
            updated_app = record_grant(
                attorney_id=attorney_id,
                application_id=app.id,
                grant_number=data.get('grant_number', ''),
                grant_date=data.get('grant_date')
            )
            
            return Response(PatentApplicationSerializer(updated_app).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ScheduleMaintenanceView(generics.CreateAPIView):
    """Schedule a maintenance fee payment."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.maintenance.manage")]
    
    def create(self, request, *args, **kwargs):
        try:
            app = PatentApplication.objects.get(pk=kwargs['pk'])
            
            data = request.data
            attorney_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and schedule maintenance via service
            record = schedule_maintenance(
                attorney_id=attorney_id,
                application_id=app.id,
                due_date=data.get('due_date'),
                fee=data.get('fee', 0)
            )
            
            return Response(MaintenanceRecordSerializer(record).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DecideRenewalView(generics.UpdateAPIView):
    """Make a renewal decision for a maintenance record."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.maintenance.manage")]
    
    def put(self, request, *args, **kwargs):
        try:
            record = MaintenanceRecord.objects.get(pk=kwargs['pk'])
            
            data = request.data
            director_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and decide renewal via service
            updated_record = decide_renewal(
                director_id=director_id,
                record_id=record.id,
                renew=data.get('renew', False),
                justification=data.get('justification', '')
            )
            
            return Response(MaintenanceRecordSerializer(updated_record).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- Helper Classes for NotFoundResponse ---

class NotFoundResponse(Exception):
    pass
