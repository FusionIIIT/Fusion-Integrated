#  --- views.py ---

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from modules.mess.services.roles import assign_role
from modules.mess.selectors import roles as role_selector
from modules.mess.services import permissions as permission_service
from modules.mess.selectors import permissions as permission_selector

class ListAllRequestsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        requests = role_selector.list_all_requests()
        return Response(requests, status=status.HTTP_200_OK)

class ListFeedbackView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        feedback = role_selector.list_feedback()
        return Response(feedback, status=status.HTTP_200_OK)

class PublishAnnouncementView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        announcement = role_selector.publish_announcement(request.data['content'])
        return Response(announcement, status=status.HTTP_201_CREATED)

class ViewAnnouncementHistoryView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        history = role_selector.view_announcement_history()
        return Response(history, status=status.HTTP_200_OK)

class SearchRegisteredStudentsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        students = role_selector.search_registered_students(request.query_params['query'])
        return Response(students, status=status.HTTP_200_OK)

class RebateSummaryView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        rebate = role_selector.rebate_summary(request.query_params['query'])
        return Response(rebate, status=status.HTTP_200_OK)

class VacationSummaryView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        vacation = role_selector.vacation_summary(request.query_params['query'])
        return Response(vacation, status=status.HTTP_200_OK)

class AssignRoleView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        role_service.assign_role(request.data['role'], request.data['employee_user_id'], request.data['starts_at'], request.data['ends_at'])
        return Response({'message': 'Role assigned successfully'}, status=status.HTTP_200_OK)
