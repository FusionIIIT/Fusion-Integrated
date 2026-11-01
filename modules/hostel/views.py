from rest_framework import viewsets
from modules.hostel.models import Hostel, WardenRoleBinding, CaretakerRoleBinding
from modules.hostel.serializers import HostelSerializer, WardenRoleBindingSerializer, CaretakerRoleBindingSerializer

class HostelViewSet(viewsets.ModelViewSet):
    queryset = Hostel.objects.all()
    serializer_class = HostelSerializer

class WardenRoleBindingViewSet(viewsets.ModelViewSet):
    queryset = WardenRoleBinding.objects.all()
    serializer_class = WardenRoleBindingSerializer

class CaretakerRoleBindingViewSet(viewsets
