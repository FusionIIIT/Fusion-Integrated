"""HTTP layer: parse, scope, delegate, serialise.

Querysets come from `selectors`, so a quiz outside the caller's scope is
absent and 404s rather than 403s.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.quizzes.api import serializers as s
from modules.quizzes.models import Quiz
from modules.quizzes.selectors import quizzes as selectors
from modules.quizzes.services import quizzes as service

MODULE = HasModuleGrant("quizzes")
MANAGE = [MODULE, HasPermission("quizzes.quiz.manage")]
ATTEMPT = [MODULE, HasPermission("quizzes.attempt.create")]


def _uid(request) -> int:
    return request.principal.user_id


class QuizListView(generics.ListCreateAPIView):
    """The professor's own quizzes; POST creates one with its questions."""
    serializer_class = s.QuizSerializer
    permission_classes = MANAGE

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):    # no principal at schema time
            return Quiz.objects.none()
        return selectors.quizzes_owned_by(_uid(self.request))

    def perform_create(self, serializer):
        serializer.instance = service.create_quiz(
            owner_user_id=_uid(self.request), data=serializer.validated_data)


@extend_schema(request=None, responses=s.QuizSerializer)
class PublishView(APIView):
    permission_classes = MANAGE

    def post(self, request, pk):
        quiz = service.publish(scope=selectors.quizzes_owned_by(_uid(request)),
                               quiz_id=pk)
        return Response(s.QuizSerializer(quiz).data)


class AvailableQuizzesView(generics.ListAPIView):
    serializer_class = s.QuizSerializer
    permission_classes = [MODULE, HasPermission("quizzes.quiz.view")]

    def get_queryset(self):
        return selectors.quizzes_for_student()


@extend_schema(request=None, responses=s.AttemptSerializer)
class StartAttemptView(APIView):
    permission_classes = ATTEMPT

    def post(self, request, pk):
        attempt = service.start_attempt(quiz_id=pk, student_user_id=_uid(request))
        return Response(s.AttemptSerializer(attempt).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.SaveResponseSerializer, responses=None)
class SaveResponseView(APIView):
    permission_classes = ATTEMPT

    def put(self, request, pk):
        payload = s.SaveResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        service.save_response(scope=selectors.attempts_of(_uid(request)),
                              attempt_id=pk, **payload.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(request=None, responses=s.AttemptSerializer)
class SubmitAttemptView(APIView):
    """Marks immediately and returns the score."""
    permission_classes = ATTEMPT

    def post(self, request, pk):
        attempt = service.submit_attempt(scope=selectors.attempts_of(_uid(request)),
                                         attempt_id=pk)
        return Response(s.AttemptSerializer(attempt).data)
