from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from fusion_auth.permissions import HasModuleGrant, HasPermission

from ..models import (
    PatentApplication, Inventor, ApplicationDocument,
    AttorneyAssignment, PatentabilityOpinion, Budget, Filing,
    OfficeAction, MaintenanceRecord, Appeal, ApplicationHistory
)
from ..services.applications import (
    submit_application, assign_director, review_application, resubmit_application,
    withdraw_application, expire_overdue_resubmissions, file_appeal, decide_appeal
)


# --- Permission Classes ---

class PatentApplicationListMixin(generics.ListAPIView):
    """Base mixin for list views that filter by the requesting principal."""
    
    permission_classes = [HasModuleGrant("patent")]
    
    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if not principal:
            return PatentApplication.objects.none()
        
        # Filter based on user kind/role logic (simplified for this step)
        # In a real system, this would check roles against registry.py ROLE_GRANTS
        user_kind = getattr(principal, 'kind', None)
        
        if user_kind == 'student':  # Applicant
            return PatentApplication.objects.filter(applicant_id=principal.user_id)
        elif user_kind == 'director':
            # Directors can review applications assigned to them
            return PatentApplication.objects.filter(assigned_director_id=principal.user_id)
        elif user_kind == 'admin':  # PCC_ADMIN
            return PatentApplication.objects.all()
        else:  # Default to self or all if logic is complex, here we assume admin access for safety in this snippet context or extend based on specific role checks
            # For simplicity in this step, assuming Admin sees all, others see self or assigned
            # A robust implementation would check registry.py ROLE_GRANTS explicitly
            return PatentApplication.objects.all()


# --- Application Views ---

class ApplicationListView(PatentApplicationListMixin):
    """List applications for the current user."""
    
    permission_classes = [HasModuleGrant("patent")]
    
    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if not principal:
            return PatentApplication.objects.none()
        
        user_kind = getattr(principal, 'kind', None)
        
        if user_kind == 'student':  # Applicant
            return PatentApplication.objects.filter(applicant_id=principal.user_id).order_by('-created_at')
        elif user_kind == 'director':
            return PatentApplication.objects.filter(assigned_director_id=principal.user_id).order_by('-created_at')
        elif user_kind == 'admin':  # PCC_ADMIN
            return PatentApplication.objects.all().order_by('-created_at')
        else:
            # Fallback for other roles if not explicitly handled above, default to self or empty
            # Assuming only Student/Director/Admin exist based on context
            return PatentApplication.objects.none()


class ApplicationDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve and update application details."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.application.manage")]
    
    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if not principal:
            return PatentApplication.objects.none()
        
        user_kind = getattr(principal, 'kind', None)
        
        if user_kind == 'student':  # Applicant
            return PatentApplication.objects.filter(applicant_id=principal.user_id)
        elif user_kind == 'director':
            return PatentApplication.objects.filter(assigned_director_id=principal.user_id)
        elif user_kind == 'admin':
            return PatentApplication.objects.all()
        else:
            return PatentApplication.objects.none()

    def get_object(self):
        queryset = self.get_queryset()
        try:
            return queryset.get(pk=self.kwargs['pk'])
        except PatentApplication.DoesNotExist:
            raise NotFoundResponse("Application not found.")


class ApplicationHistoryView(generics.RetrieveAPIView):
    """Retrieve application history."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.application.manage")]
    
    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if not principal:
            return ApplicationHistory.objects.none()
        
        user_kind = getattr(principal, "kind", None)
        
        if user_kind == 'student':  # Applicant
            return PatentApplication.objects.filter(applicant_id=principal.user_id).order_by('-created_at')
        elif user_kind == 'director':
            return PatentApplication.objects.filter(assigned_director_id=principal.user_id).order_by('-created_at')
        elif user_kind == 'admin':
            return PatentApplication.objects.all().order_by('-created_at')
        else:
            return PatentApplication.objects.none()

    def get_object(self):
        queryset = self.get_queryset()
        try:
            return queryset.get(pk=self.kwargs['pk'])
        except PatentApplication.DoesNotExist:
            raise NotFoundResponse("Application not found.")


# --- Action Views ---

class SubmitApplicationView(generics.CreateAPIView):
    """Submit a new patent application."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.application.create")]
    
    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            applicant_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and submit via service
            app = submit_application(
                applicant_id=applicant_id,
                data=data,
                inventors=request.data.get('inventors', []),
                documents=request.data.get('documents', []),
                actor_id=applicant_id
            )
            
            return Response(PatentApplicationSerializer(app).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AssignDirectorView(generics.UpdateAPIView):
    """Assign a director to an application."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.application.manage")]
    
    def put(self, request, *args, **kwargs):
        try:
            app = PatentApplication.objects.get(pk=kwargs['pk'])
            
            data = request.data
            director_id = data.get('director_id')
            admin_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and assign via service
            app = assign_director(
                admin_id=admin_id,
                application_id=app.id,
                director_id=director_id
            )
            
            return Response(PatentApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReviewApplicationView(generics.UpdateAPIView):
    """Record a director's review decision."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.application.review")]
    
    def put(self, request, *args, **kwargs):
        try:
            app = PatentApplication.objects.get(pk=kwargs['pk'])
            
            data = request.data
            director_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and review via service
            app = review_application(
                director_id=director_id,
                application_id=app.id,
                decision=data.get('decision'),
                justification=data.get('justification')
            )
            
            return Response(PatentApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ResubmitApplicationView(generics.UpdateAPIView):
    """Resubmit an application after revision."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.application.manage")]
    
    def put(self, request, *args, **kwargs):
        try:
            app = PatentApplication.objects.get(pk=kwargs['pk'])
            
            data = request.data
            applicant_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and resubmit via service
            app = resubmit_application(
                applicant_id=applicant_id,
                application_id=app.id,
                changes=data.get('changes', {}),
                response_to_feedback=data.get('response_to_feedback'),
                actor_id=applicant_id
            )
            
            return Response(PatentApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WithdrawApplicationView(generics.UpdateAPIView):
    """Withdraw an application."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.application.manage")]
    
    def put(self, request, *args, **kwargs):
        try:
            app = PatentApplication.objects.get(pk=kwargs['pk'])
            
            data = request.data
            applicant_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and withdraw via service
            app = withdraw_application(
                applicant_id=applicant_id,
                application_id=app.id,
                reason=data.get('reason')
            )
            
            return Response(PatentApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FileAppealView(generics.CreateAPIView):
    """File an appeal against a rejection."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.application.manage")]
    
    def create(self, request, *args, **kwargs):
        try:
            app = PatentApplication.objects.get(pk=kwargs['pk'])
            
            data = request.data
            applicant_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and file appeal via service
            appeal = file_appeal(
                applicant_id=applicant_id,
                application_id=app.id,
                grounds=data.get('grounds')
            )
            
            return Response({'id': appeal.id, 'status': appeal.status}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DecideAppealView(generics.UpdateAPIView):
    """Record a director's decision on an appeal."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.appeal.review")]
    
    def put(self, request, *args, **kwargs):
        try:
            appeal = Appeal.objects.get(pk=kwargs['pk'])
            
            data = request.data
            director_id = request.principal.user_id if hasattr(request, 'principal') else None
            
            # Validate and decide via service
            appeal = decide_appeal(
                director_id=director_id,
                appeal_id=appeal.id,
                outcome=data.get('outcome'),
                justification=data.get('justification')
            )
            
            return Response({'id': appeal.id, 'status': appeal.status}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- Admin Views ---

class ExpireOverdueResubmissionsView(generics.GenericAPIView):
    """Set status to Expired for applications where resubmission deadline has passed."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.admin.manage")]
    
    def post(self, request):
        today = request.data.get('today')
        if not today:
            from datetime import date
            today = date.today()
        
        expired_apps = expire_overdue_resubmissions(today)
        
        return Response({
            'count': len(expired_apps),
            'expired_applications': [app.APPLICATION_NUMBER for app in expired_apps]
        }, status=status.HTTP_200_OK)


class AdminApplicationListView(PatentApplicationListMixin):
    """Admin list of all submitted applications."""
    
    permission_classes = [HasModuleGrant("patent"), HasPermission("patent.admin.manage")]
    
    def get_queryset(self):
        return PatentApplication.objects.all().order_by('-created_at')


class NotFoundResponse(Exception):
    pass
