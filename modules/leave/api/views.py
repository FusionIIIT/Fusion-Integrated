from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from modules.accesscontrol.middleware import HasModuleGrant, HasPermission
from modules.leave.api.serializers import (
    LeaveRequestSerializer,
    LeaveRequestTransitionSerializer,
    CancellationRequestSerializer,
    ExtensionRequestSerializer,
)
from modules.leave.selectors.scoping import requests_for
from modules.leave.models.requests import (
    LeaveRequest,
    LeaveRequestTransition,
    CancellationRequest,
    ExtensionRequest,
)
from modules.leave.services.requests import (
    apply_for_leave,
    withdraw_request,
    respond_substitute,
    transition,
)
from modules.leave.services.actions import (
    request_cancellation,
    request_extension,
    submit_resumption,
    review_resumption,
    sync_offline_leave,
)
from modules.leave.domain.exceptions import (
    LeaveApplicationError,
    LeaveTransitionError,
    LeaveActionError,
)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """
    API views for leave requests.
    Implements listing, detail, and basic CRUD operations.
    """

    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter leave requests based on actor role and permissions.
        Uses the scoping selector to enforce object-level access.
        """
        actor = self.request.user
        queryset = requests_for(actor)
        return queryset

    def get_permissions(self):
        """
        Override get_permissions to apply role-based access control.
        """
        if self.action == 'list':
            return [HasModuleGrant('leave'), HasPermission('leave.request.view')]
        elif self.action == 'retrieve':
            return [HasModuleGrant('leave'), HasPermission('leave.request.view')]
        elif self.action == 'create':
            return [HasModuleGrant('leave'), HasPermission('leave.request.create')]
        elif self.action == 'update':
            return [HasModuleGrant('leave'), HasPermission('leave.request.update')]
        elif self.action == 'destroy':
            return [HasModuleGrant('leave'), HasPermission('leave.request.delete')]
        elif self.action == 'apply':
            return [HasModuleGrant('leave'), HasPermission('leave.request.create')]
        elif self.action == 'withdraw':
            return [HasModuleGrant('leave'), HasPermission('leave.request.delete')]
        elif self.action == 'respond':
            return [HasModuleGrant('leave'), HasPermission('leave.substitute.respond')]
        elif self.action == 'nominate':
            return [HasModuleGrant('leave'), HasPermission('leave.substitute.respond')]
        elif self.action == 'approve':
            return [HasModuleGrant('leave'), HasPermission('leave.request.approve')]
        elif self.action == 'reject':
            return [HasModuleGrant('leave'), HasPermission('leave.request.approve')]
        elif self.action == 'resumption':
            return [HasModuleGrant('leave'), HasPermission('leave.resumption.submit')]
        elif self.action == 'review_resumption':
            return [HasModuleGrant('leave'), HasPermission('leave.resumption.review')]
        elif self.action == 'offline_sync':
            return [HasModuleGrant('leave'), HasPermission('leave.offline.record')]
        elif self.action == 'cancel':
            return [HasModuleGrant('leave'), HasPermission('leave.cancellation.request')]
        elif self.action == 'extend':
            return [HasModuleGrant('leave'), HasPermission('leave.extension.request')]
        return [HasModuleGrant('leave')]

    def perform_create(self, serializer):
        """
        Create leave request with authenticated user as owner.
        """
        serializer.save(user_id=self.request.user.user_id)

    @action(detail=True, methods=['get'])
    def transitions(self, request, pk=None):
        """
        Return transition history for a leave request.
        """
        leave_request = self.get_object()
        transitions = LeaveRequestTransition.objects.filter(
            leave_request_id=leave_request.id
        ).order_by('-created_at')

        serializer = LeaveRequestTransitionSerializer(
            transitions, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Return pending leave requests for the authenticated user.
        """
        queryset = self.get_queryset().filter(
            status__in=[
                'DRAFT',
                'AWAITING_SUBSTITUTE',
                'AWAITING_UNIT_HEAD',
                'AWAITING_ESTABLISHMENT',
                'AWAITING_FINAL_SANCTION',
                'AWAITING_DIRECTOR_SANCTION',
            ]
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def approved(self, request):
        """
        Return approved leave requests for the authenticated user.
        """
        queryset = self.get_queryset().filter(status='APPROVED')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def rejected(self, request):
        """
        Return rejected leave requests for the authenticated user.
        """
        queryset = self.get_queryset().filter(status='REJECTED')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """
        Apply for leave by creating a new leave request.
        """
        try:
            serializer = LeaveRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            leave_data = serializer.validated_data
            leave_data['user_id'] = self.request.user.user_id

            leave_request = apply_for_leave(**leave_data)

            return Response(
                LeaveRequestSerializer(leave_request).data,
                status=status.HTTP_201_CREATED
            )
        except LeaveApplicationError as e:
            error_code = getattr(e, 'code', 'leave.application.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            return Response(
                {
                    'error': {
                        'code': 'validation.error',
                        'message': 'Validation failed',
                        'details': e.detail,
                        'request_id': None
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Request cancellation of a leave request.
        """
        try:
            leave_request = self.get_object()

            response_data = request.data
            response_data['leave_request_id'] = leave_request.id
            response_data['actor_user_id'] = self.request.user.user_id
            response_data['actor_role'] = self.request.user.role
            response_data['reason'] = response_data.get('reason', '')

            request_cancellation(**response_data)

            return Response(
                {
                    'message': 'Leave cancellation requested successfully',
                    'leave_request_id': leave_request.id
                },
                status=status.HTTP_200_OK
            )
        except LeaveActionError as e:
            error_code = getattr(e, 'code', 'leave.cancellation.request.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'error': {
                        'code': 'internal.error',
                        'message': 'An unexpected error occurred',
                        'details': [str(e)],
                        'request_id': None
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def extend(self, request, pk=None):
        """
        Request extension of an ongoing leave.
        """
        try:
            leave_request = self.get_object()

            response_data = request.data
            response_data['leave_request_id'] = leave_request.id
            response_data['actor_user_id'] = self.request.user.user_id
            response_data['actor_role'] = self.request.user.role
            response_data['requested_end_date'] = response_data.get('requested_end_date')
            response_data['incremental_days'] = response_data.get('incremental_days')
            response_data['substitute_user_id'] = response_data.get('substitute_user_id')

            request_extension(**response_data)

            return Response(
                {
                    'message': 'Leave extension requested successfully',
                    'leave_request_id': leave_request.id
                },
                status=status.HTTP_200_OK
            )
        except LeaveActionError as e:
            error_code = getattr(e, 'code', 'leave.extension.request.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'error': {
                        'code': 'internal.error',
                        'message': 'An unexpected error occurred',
                        'details': [str(e)],
                        'request_id': None
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """
        Withdraw a pending leave request.
        """
        try:
            leave_request = self.get_object()

            withdraw_request(
                leave_request_id=leave_request.id,
                actor_user_id=self.request.user.user_id
            )

            return Response(
                {
                    'message': 'Leave request withdrawn successfully',
                    'leave_request_id': leave_request.id
                },
                status=status.HTTP_200_OK
            )
        except LeaveApplicationError as e:
            error_code = getattr(e, 'code', 'leave.withdraw.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except LeaveTransitionError as e:
            error_code = getattr(e, 'code', 'leave.transition.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'error': {
                        'code': 'internal.error',
                        'message': 'An unexpected error occurred',
                        'details': [str(e)],
                        'request_id': None
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """
        Respond to a substitute request (accept or decline).
        """
        try:
            leave_request = self.get_object()

            response_data = request.data
            response_data['leave_request_id'] = leave_request.id
            response_data['actor_user_id'] = self.request.user.user_id

            respond_substitute(**response_data)

            return Response(
                {
                    'message': 'Substitute response recorded successfully',
                    'leave_request_id': leave_request.id
                },
                status=status.HTTP_200_OK
            )
        except LeaveApplicationError as e:
            error_code = getattr(e, 'code', 'leave.substitute.respond.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except LeaveTransitionError as e:
            error_code = getattr(e, 'code', 'leave.transition.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'error': {
                        'code': 'internal.error',
                        'message': 'An unexpected error occurred',
                        'details': [str(e)],
                        'request_id': None
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def nominate(self, request, pk=None):
        """
        Nominate a replacement substitute.
        """
        try:
            leave_request = self.get_object()

            response_data = request.data
            response_data['leave_request_id'] = leave_request.id
            response_data['actor_user_id'] = self.request.user.user_id

            respond_substitute(**response_data)

            return Response(
                {
                    'message': 'Replacement substitute nominated successfully',
                    'leave_request_id': leave_request.id
                },
                status=status.HTTP_200_OK
            )
        except LeaveApplicationError as e:
            error_code = getattr(e, 'code', 'leave.substitute.nominate.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except LeaveTransitionError as e:
            error_code = getattr(e, 'code', 'leave.transition.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'error': {
                        'code': 'internal.error',
                        'message': 'An unexpected error occurred',
                        'details': [str(e)],
                        'request_id': None
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a leave request (Unit Head, Establishment, or Sanctioning Authority).
        """
        try:
            leave_request = self.get_object()

            response_data = request.data
            response_data['leave_request_id'] = leave_request.id
            response_data['actor_user_id'] = self.request.user.user_id

            transition(
                leave_request_id=leave_request.id,
                from_status=leave_request.status,
                to_status='APPROVED',
                actor_user_id=self.request.user.user_id,
                actor_role='UNIT_HEAD'
            )

            return Response(
                {
                    'message': 'Leave request approved successfully',
                    'leave_request_id': leave_request.id
                },
                status=status.HTTP_200_OK
            )
        except LeaveApplicationError as e:
            error_code = getattr(e, 'code', 'leave.approve.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except LeaveTransitionError as e:
            error_code = getattr(e, 'code', 'leave.transition.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'error': {
                        'code': 'internal.error',
                        'message': 'An unexpected error occurred',
                        'details': [str(e)],
                        'request_id': None
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a leave request (Unit Head, Establishment, or Sanctioning Authority).
        """
        try:
            leave_request = self.get_object()

            response_data = request.data
            response_data['leave_request_id'] = leave_request.id
            response_data['actor_user_id'] = self.request.user.user_id

            transition(
                leave_request_id=leave_request.id,
                from_status=leave_request.status,
                to_status='REJECTED',
                actor_user_id=self.request.user.user_id,
                actor_role='UNIT_HEAD'
            )

            return Response(
                {
                    'message': 'Leave request rejected successfully',
                    'leave_request_id': leave_request.id
                },
                status=status.HTTP_200_OK
            )
        except LeaveApplicationError as e:
            error_code = getattr(e, 'code', 'leave.reject.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except LeaveTransitionError as e:
            error_code = getattr(e, 'code', 'leave.transition.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'error': {
                        'code': 'internal.error',
                        'message': 'An unexpected error occurred',
                        'details': [str(e)],
                        'request_id': None
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def resumption(self, request, pk=None):
        """
        Submit leave resumption record.
        """
        try:
            leave_request = self.get_object()

            response_data = request.data
            response_data['leave_request_id'] = leave_request.id
            response_data['actor_user_id'] = self.request.user.user_id

            submit_resumption(**response_data)

            return Response(
                {
                    'message': 'Leave resumption submitted successfully',
                    'leave_request_id': leave_request.id
                },
                status=status.HTTP_200_OK
            )
        except LeaveActionError as e:
            error_code = getattr(e, 'code', 'leave.resumption.submit.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'error': {
                        'code': 'internal.error',
                        'message': 'An unexpected error occurred',
                        'details': [str(e)],
                        'request_id': None
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def review_resumption(self, request, pk=None):
        """
        Review and approve/reject leave resumption.
        """
        try:
            leave_request = self.get_object()

            response_data = request.data
            response_data['leave_request_id'] = leave_request.id
            response_data['actor_user_id'] = self.request.user.user_id

            review_resumption(**response_data)

            return Response(
                {
                    'message': 'Leave resumption reviewed successfully',
                    'leave_request_id': leave_request.id
                },
                status=status.HTTP_200_OK
            )
        except LeaveActionError as e:
            error_code = getattr(e, 'code', 'leave.resumption.review.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'error': {
                        'code': 'internal.error',
                        'message': 'An unexpected error occurred',
                        'details': [str(e)],
                        'request_id': None
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def offline_sync(self, request, pk=None):
        """
        Synchronise offline leave with sanction evidence.
        """
        try:
            leave_request = self.get_object()

            response_data = request.data
            response_data['leave_request_id'] = leave_request.id
            response_data['actor_user_id'] = self.request.user.user_id

            sync_offline_leave(**response_data)

            return Response(
                {
                    'message': 'Offline leave synchronised successfully',
                    'leave_request_id': leave_request.id
                },
                status=status.HTTP_200_OK
            )
        except LeaveActionError as e:
            error_code = getattr(e, 'code', 'leave.offline.sync.error')
            error_message = str(e)
            return Response(
                {
                    'error': {
                        'code': error_code,
                        'message': error_message,
                        'details': getattr(e, 'details', []),
                        'request_id': getattr(e, 'request_id', None)
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'error': {
                        'code': 'internal.error',
                        'message': 'An unexpected error occurred',
                        'details': [str(e)],
                        'request_id': None
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
