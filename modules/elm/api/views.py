from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status

class ELMDataViewSet(viewsets.ViewSet):
    def list(self, request):
        metadata = {
            "label": "elm",
            "description": "ELM module metadata",
            "version": "1.0.0"
        }
        return Response(metadata, status=status.HTTP_200_OK)
