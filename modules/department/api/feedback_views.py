from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.department.api.feedback_serializers import (
    DeptFeedbackDisposeSerializer,
    DeptFeedbackReviewSerializer,
    DeptFeedbackSerializer,
    DeptFeedbackWriteSerializer,
)
from modules.department.models import Feedback
from modules.department.selectors.feedback import visible_feedback
from modules.department.services import feedback as feedback_service


@extend_schema(
    summary="List and create department feedback submissions",
    responses={
        200: DeptFeedbackSerializer,
        201: DeptFeedbackSerializer,
        400: None,
        403: None,
    },
    tags=["Feedback"],
)
class FeedbackListView(ListCreateAPIView):
    """Lists and creates department feedback submissions."""

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DeptFeedbackWriteSerializer
        return DeptFeedbackSerializer

    queryset = Feedback.objects.none()
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.feedback.view"),
    ]

    def get_queryset(self) -> QuerySet[Feedback]:
        """Returns the queryset of visible feedback submissions."""
        if getattr(self, "swagger_fake_view", False):
            return Feedback.objects.none()
        return visible_feedback(self.request.principal)

    def create(self, request, *args, **kwargs):
        """Creates a new department feedback submission."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        feedback = feedback_service.submit(
            actor=request.principal,
            department_id=data['department'],
            body=data['body'],
        )
        return Response(DeptFeedbackSerializer(feedback).data, status=201)


@extend_schema(
    summary="Review a department feedback submission",
    responses={
        200: DeptFeedbackSerializer,
        404: None,
        403: None,
    },
    tags=["Feedback"],
)
class FeedbackReviewView(APIView):
    """Reviews a specific department feedback submission."""
    serializer_class = DeptFeedbackSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.feedback.review"),
    ]

    def post(self, request, pk):
        """Reviews the feedback submission."""
        serializer = DeptFeedbackReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        feedback = feedback_service.review(
            actor=request.principal,
            feedback_id=pk,
            category=data['category'],
            disposition=data.get('disposition'),
        )
        return Response(DeptFeedbackSerializer(feedback).data)


@extend_schema(
    summary="Dispose of a department feedback submission",
    responses={
        200: DeptFeedbackSerializer,
        404: None,
        403: None,
    },
    tags=["Feedback"],
)
class FeedbackDisposeView(APIView):
    """Disposes of a specific department feedback submission."""
    serializer_class = DeptFeedbackSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.feedback.update"),
    ]

    def post(self, request, pk):
        """Disposes of the feedback submission."""
        serializer = DeptFeedbackDisposeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        feedback = feedback_service.dispose(
            actor=request.principal,
            feedback_id=pk,
            outcome=data['outcome'],
        )
        return Response(DeptFeedbackSerializer(feedback).data)
