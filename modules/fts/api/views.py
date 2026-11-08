from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError, PermissionDenied
from modules.directory.models import UserRef
from modules.fts.models import FTSFile, FileMovement, FileAuditLog, FileAttachment
from modules.fts.api.serializers import (UserSummarySerializer, FileAttachmentSerializer, FileMovementSerializer, FileAuditLogSerializer, FTSFileListSerializer, FTSFileDetailSerializer, CreateFileRequestSerializer, DraftEditRequestSerializer, ForwardFileRequestSerializer, ReturnFileRequestSerializer, ArchiveFileRequestSerializer)
from modules.fts.services import file_service

class InboxView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user_ref = UserRef.objects.get(user_id=request.user.id)
        files = file_service.get_inbox(user_ref)
        return Response(FTSFileListSerializer(files, many=True).data)

class OutboxView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user_ref = UserRef.objects.get(user_id=request.user.id)
        files = file_service.get_outbox(user_ref)
        return Response(FTSFileListSerializer(files, many=True).data)

class DraftsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user_ref = UserRef.objects.get(user_id=request.user.id)
        files = file_service.get_drafts(user_ref)
        return Response(FTSFileListSerializer(files, many=True).data)

class ArchivedView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user_ref = UserRef.objects.get(user_id=request.user.id)
        files = file_service.get_archived(user_ref)
        return Response(FTSFileListSerializer(files, many=True).data)

class CreateFileView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = CreateFileRequestSerializer(data=request.data)
        if serializer.is_valid():
            user_ref = UserRef.objects.get(user_id=request.user.id)
            file = file_service.create_file(owner=user_ref, **serializer.validated_data)
            return Response(FTSFileDetailSerializer(file).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FileDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        file = get_object_or_404(FTSFile, pk=pk)
        user_ref = UserRef.objects.get(user_id=request.user.id)
        if not file.is_accessible_by(user_ref):
            raise PermissionDenied
        return Response(FTSFileDetailSerializer(file).data)

class EditDraftView(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, pk):
        file = get_object_or_404(FTSFile, pk=pk)
        serializer = DraftEditRequestSerializer(data=request.data)
        if serializer.is_valid():
            user_ref = UserRef.objects.get(user_id=request.user.id)
            file_service.edit_draft(file, user=user_ref, **serializer.validated_data)
            return Response(FTSFileDetailSerializer(file).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DiscardDraftView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        file = get_object_or_404(FTSFile, pk=pk)
        user_ref = UserRef.objects.get(user_id=request.user.id)
        file_service.discard_draft(file, user=user_ref)
        return Response({'status': 'discarded'})

class ForwardFileView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        file = get_object_or_404(FTSFile, pk=pk)
        serializer = ForwardFileRequestSerializer(data=request.data)
        if serializer.is_valid():
            user_ref = UserRef.objects.get(user_id=request.user.id)
            receiver = UserRef.objects.get(user_id=serializer.validated_data.pop('receiver_id'))
            movement = file_service.send_file(file, sender=user_ref, receiver=receiver, **serializer.validated_data)
            return Response(FileMovementSerializer(movement).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ReturnFileView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        file = get_object_or_404(FTSFile, pk=pk)
        serializer = ReturnFileRequestSerializer(data=request.data)
        if serializer.is_valid():
            user_ref = UserRef.objects.get(user_id=request.user.id)
            movement = file_service.return_file(file, sender=user_ref, **serializer.validated_data)
            return Response(FileMovementSerializer(movement).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ArchiveFileView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        file = get_object_or_404(FTSFile, pk=pk)
        serializer = ArchiveFileRequestSerializer(data=request.data)
        if serializer.is_valid():
            user_ref = UserRef.objects.get(user_id=request.user.id)
            file = file_service.archive_file(file, user=user_ref, **serializer.validated_data)
            return Response(FTSFileDetailSerializer(file).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FileHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        file = get_object_or_404(FTSFile, pk=pk)
        user_ref = UserRef.objects.get(user_id=request.user.id)
        history = file_service.get_file_history(file, user=user_ref)
        return Response({'movements': FileMovementSerializer(history['movements'], many=True).data, 'audit_logs': FileAuditLogSerializer(history['audit_logs'], many=True).data})

class ConsumingModuleApiView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        file_number = request.query_params.get('file_number')
        # Logic to return files based on file_number
        return Response({'files': []})
    
    def post(self, request):
        return Response({'status': 'integrated', 'detail': 'Integration stub processed.'})