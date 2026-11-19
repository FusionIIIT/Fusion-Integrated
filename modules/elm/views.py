from rest_framework import generics
from .models import Course, Module, Lesson
from .serializers import CourseSerializer, ModuleSerializer, LessonSerializer

class CourseListView(generics.ListAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

class CourseDetailView(generics.RetrieveAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

class ModuleListView(generics.ListAPIView):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer

class ModuleDetailView(generics.RetrieveAPIView):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer

class LessonListView(generics.ListAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

class LessonDetailView(generics.RetrieveAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
