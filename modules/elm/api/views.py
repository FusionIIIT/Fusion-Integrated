from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from modules.placement.models import Application, ApplicationTransition

class ApplicationListView(generics.ListAPIView):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]


class ApplicationCreateView(generics.CreateAPIView):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]


class ApplicationDetailView(generics.RetrieveUpdateAPIView):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]


class ApplicationTransitionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        application = Application.objects.get(pk=pk)
        serializer = ApplicationTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ApplicationTransition.objects.create(
            application=application,
            from_status=application.status,
            to_status=serializer.validated_data['to_status'],
            actor_user_id=request.user.id,
            reason=serializer.validated_data['reason']
        )
        application.status = serializer.validated_data['to_status']
        application.save()
        return Response(ApplicationSerializer(application).data, status=status.HTTP_200_OK)
