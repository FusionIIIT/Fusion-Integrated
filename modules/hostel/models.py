from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Hostel(models.Model):
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)

class RoleBinding(models.Model):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null: 255)

    class Meta:
        abstract = True

class WardenRoleBinding(RoleBinding):
    pass

class CaretakerRoleBinding(RoleBinding):
    pass
