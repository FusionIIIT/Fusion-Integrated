from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .serializers import FileCreateSerializer, FileEditSerializer, FileDiscardSerializer, FileForwardSerializer, FileReturnSerializer
from modules.fts.services.file_creation import create_file_service, edit_draft_service, discard_draft_service
from modules.fts.services.file_movement import forward_file_service, return_file_service


class FileCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FileCreateSerializer(data=request.data)
        if serializer.is_valid():
            actor_id = str(request.user.id)
            initial_comment = serializer.validated_data['initial_comment']
            attachment_urls = serializer.validated_data.get('attachment_urls', [])
            file = create_file_service(actor_id, initial_comment, attachment_urls)
            return Response({'id': file.id, 'status': file.status}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FileEditView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, file_id):
        serializer = FileEditSerializer(data=request.data)
        if serializer.is_valid():
            actor_id = str(request.user.id)
            new_comment = serializer.validated_data['new_comment']
            new_attachment_urls = serializer.validated_data.get('new_attachment_urls', [])
            file = edit_draft_service(actor_id, file_id, new_comment, new_attachment_urls)
            return Response({'id': file.id, 'status': file.status}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FileDiscardView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, file_id):
        try:
            actor_id = str(request.user.id)
            discard_draft_service(actor_id, file_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FileForwardView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        serializer = FileForwardSerializer(data=request.data)
        if serializer.is_valid():
            actor_id = str(request.user.id)
            receiver_id = serializer.validated_data['receiver_id']
            movement_comment = serializer.validated_data['movement_comment']
            attachment_urls = serializer.validated_data.get('attachment_urls', [])
            file = forward_file_service(actor_id, file_id, receiver_id, movement_comment, attachment_urls)
            return Response({'id': file.id, 'status': file.status, 'current_holder_id': file.current_holder_id}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FileReturnView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        serializer = FileReturnSerializer(data=request.data)
        if serializer.is_valid():
            actor_id = str(request.user.id)
            movement_comment = serializer.validated_data['movement_comment']
            attachment_urls = serializer.validated_data.get('attachment_urls', [])
            file = return_file_service(actor_id, file_id, movement_comment, attachment_urls)
            return Response({'id': file.id, 'status': file.status, 'current_holder_id': file.current_holder_id}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
