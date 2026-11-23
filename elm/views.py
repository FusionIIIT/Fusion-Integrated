from django.shortcuts import render
from .models import ELearningCourse, Evaluation, Leave, Module

def course_list(request):
    courses = ELearningCourse.objects.all()
    return render(request, 'elm/courses.html', {'courses': courses})

def course_detail(request, pk):
    course = ELearningCourse.objects.get(pk=pk)
    return render(request, 'elm/course_detail.html', {'course': course})