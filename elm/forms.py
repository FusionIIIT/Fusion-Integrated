from django import forms
from .models import ELearningCourse, Evaluation, Leave, Module

class CourseForm(forms.ModelForm):
    class Meta:
        model = ELearningCourse
        fields = ['title', 'description']

class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = ['title', 'description']

class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['title', 'description']

class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description']