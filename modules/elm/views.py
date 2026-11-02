from .models import LeaveCategory, LeaveApplication

from .serializers import LeaveCategorySerializer,
LeaveApplicationSerializer



class LeaveCategoryListCreateView(generics.ListCreateAPIView):

    queryset = LeaveCategory.objects.all()

    serializer_class = LeaveCategorySerializer



class LeaveCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDe
stroyAPIView):

    queryset = LeaveCategory.objects.all()

    serializer_class = LeaveCategorySerializer



class
LeaveApplicationListCreateView(generics.ListCreateAPIView):

    queryset = LeaveApplication.objects.all()

    serializer_class = LeaveApplicationSerializer



class
LeaveApplicationRetrieveUpdateDestroyView(generics.RetrieveUpdat
eDestroyAPIView):

    queryset = LeaveApplication.objects.all()

    serializer_class = LeaveApplicationSerializer
