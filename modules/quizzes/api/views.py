"""HTTP layer: parse, scope, delegate, serialise.

Querysets come from `selectors`, so a quiz outside the caller's scope is
absent and its detail view 404s rather than 403s.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.quizzes.api import serializers as s
from modules.quizzes.selectors import quizzes as selectors
from modules.quizzes.services import attempts as attempt_service
from modules.quizzes.services import authoring

MODULE = HasModuleGrant("quizzes")

P_VIEW = "quizzes.quiz.view"
P_MANAGE = "quizzes.quiz.manage"
P_ATTEMPT = "quizzes.attempt.create"
P_EVALUATE = "quizzes.attempt.evaluate"

MANAGE = [MODULE, HasPermission(P_MANAGE)]
EVALUATE = [MODULE, HasPermission(P_EVALUATE)]
ATTEMPT = [MODULE, HasPermission(P_ATTEMPT)]


def _uid(request) -> int:
    return request.principal.user_id


# -- Professor: quizzes and questions (CW-QZ-01) ------------------------------

class QuizListView(generics.ListCreateAPIView):
    serializer_class = s.QuizSerializer
    permission_classes = MANAGE

    def get_queryset(self):
        return selectors.quizzes_owned_by(_uid(self.request))

    def perform_create(self, serializer):
        serializer.instance = authoring.create_quiz(
            owner_user_id=_uid(self.request), data=serializer.validated_data)


class QuizDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = s.QuizDetailSerializer
    permission_classes = MANAGE

    def get_queryset(self):
        return selectors.quizzes_owned_by(_uid(self.request))

    def perform_update(self, serializer):
        serializer.instance = authoring.update_quiz(
            scope=self.get_queryset(), pk=self.kwargs["pk"],
            data=serializer.validated_data)


def _lifecycle_view(action, name):
    @extend_schema(request=None, responses=s.QuizSerializer)
    class View(APIView):
        permission_classes = MANAGE

        def post(self, request, pk):
            quiz = action(scope=selectors.quizzes_owned_by(_uid(request)), pk=pk)
            return Response(s.QuizSerializer(quiz).data)

    View.__name__ = View.__qualname__ = name
    return View


QuizPublishView = _lifecycle_view(authoring.publish, "QuizPublishView")
QuizCloseView = _lifecycle_view(authoring.close, "QuizCloseView")
QuizArchiveView = _lifecycle_view(authoring.archive, "QuizArchiveView")


@extend_schema(request=s.QuestionSerializer, responses=s.QuestionSerializer)
class QuizQuestionsView(APIView):
    permission_classes = MANAGE

    def post(self, request, pk):
        payload = s.QuestionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        question = authoring.add_question(
            scope=selectors.quizzes_owned_by(_uid(request)), quiz_id=pk,
            owner_user_id=_uid(request), data=dict(payload.validated_data))
        return Response(s.QuestionSerializer(question).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=None)
class QuizQuestionDeleteView(APIView):
    permission_classes = MANAGE

    def delete(self, request, pk, question_id):
        authoring.remove_question(scope=selectors.quizzes_owned_by(_uid(request)),
                                  quiz_id=pk, question_id=question_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(request=s.CopyFromBankSerializer, responses=s.QuestionSerializer(many=True))
class QuizCopyFromBankView(APIView):
    permission_classes = MANAGE

    def post(self, request, pk):
        payload = s.CopyFromBankSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        copies = authoring.copy_from_bank(
            scope=selectors.quizzes_owned_by(_uid(request)), quiz_id=pk,
            question_ids=payload.validated_data["question_ids"],
            owner_user_id=_uid(request))
        return Response(s.QuestionSerializer(copies, many=True).data,
                        status=status.HTTP_201_CREATED)


class QuestionBankView(generics.ListCreateAPIView):
    serializer_class = s.QuestionSerializer
    permission_classes = MANAGE

    def get_queryset(self):
        filters = s.BankFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        return selectors.bank_for(_uid(self.request), **filters.validated_data)

    def perform_create(self, serializer):
        serializer.instance = authoring.add_to_bank(
            owner_user_id=_uid(self.request), data=dict(serializer.validated_data))


# -- Professor: evaluation and release (CW-QZ-03) -----------------------------

class QuizAttemptsView(generics.ListAPIView):
    serializer_class = s.AttemptSerializer
    permission_classes = EVALUATE

    def get_queryset(self):
        return selectors.attempts_on_quizzes_of(_uid(self.request)) \
            .filter(quiz_id=self.kwargs["pk"])

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "as_professor": True}


@extend_schema(request=s.GradeSerializer, responses=s.AttemptSerializer)
class GradeResponseView(APIView):
    permission_classes = EVALUATE

    def post(self, request, pk):
        payload = s.GradeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        attempt = attempt_service.grade_response(
            scope=selectors.attempts_on_quizzes_of(_uid(request)), attempt_id=pk,
            **payload.validated_data)
        return Response(s.AttemptSerializer(attempt,
                                            context={"as_professor": True}).data)


@extend_schema(request=None, responses={200: dict})
class ReleaseResultsView(APIView):
    permission_classes = EVALUATE

    def post(self, request, pk):
        released = attempt_service.release(
            scope=selectors.attempts_on_quizzes_of(_uid(request)), quiz_id=pk)
        return Response({"released": released})


# -- Student: attempts (CW-QZ-02) ---------------------------------------------

class AvailableQuizzesView(generics.ListAPIView):
    serializer_class = s.QuizSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get_queryset(self):
        return selectors.quizzes_for_student()


@extend_schema(request=None, responses=s.AttemptPaperSerializer)
class StartAttemptView(APIView):
    permission_classes = ATTEMPT

    def post(self, request, pk):
        attempt = attempt_service.start(quiz_id=pk, student_user_id=_uid(request))
        return Response(s.AttemptPaperSerializer(attempt).data,
                        status=status.HTTP_201_CREATED)


class MyAttemptsView(generics.ListAPIView):
    serializer_class = s.AttemptSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get_queryset(self):
        return selectors.attempts_of(_uid(self.request))


class MyAttemptDetailView(generics.RetrieveAPIView):
    serializer_class = s.AttemptPaperSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get_queryset(self):
        return selectors.attempts_of(_uid(self.request))


@extend_schema(request=s.SaveResponseSerializer, responses=s.ResponseSerializer)
class SaveResponseView(APIView):
    permission_classes = ATTEMPT

    def put(self, request, pk):
        payload = s.SaveResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        saved = attempt_service.save_response(
            attempt_id=pk, student_user_id=_uid(request), **payload.validated_data)
        data = s.ResponseSerializer(saved).data
        data["awarded_marks"] = data["feedback"] = None
        return Response(data)


@extend_schema(request=None, responses=s.AttemptSerializer)
class SubmitAttemptView(APIView):
    permission_classes = ATTEMPT

    def post(self, request, pk):
        attempt = attempt_service.submit(attempt_id=pk, student_user_id=_uid(request))
        return Response(s.AttemptSerializer(attempt).data)
