Sure, here's a basic example of how you might structure these classes using Django ORM. In your `models.py` file in the `elm` app:

```python
from django.db import models
from django.contrib.auth.models import User  # assuming you have user model from django's auth module

class LeaveBalance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_leaves = models.IntegerField()
    leaves_taken = models.IntegerField()

    def remaining_leaves(self):
        return self.total_leaves - self.leaves_taken

class LeaveApplication(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=20)  # you can make this a foreign key if you have more types
    status = models.CharField(max_length=15)  # approved, pending, rejected etc.

class SubstituteRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    substitute_user = models.ForeignKey(User, related_name='subs', on_delete=models.CASCADE)  # the user to whom you are substituting
    date = models.DateField()
    status = models.CharField(max_length=15)  # approved, pending, rejected etc.

class HolidayCalendar(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField()

class LeavePolicy(models.Model):
    leave_type = models.CharField(max_length=20)  # annual, sick etc.
    duration = models.IntegerField()  # number of days the leave lasts for
```
Please replace `User` with your user model if it's different. Also, remember to run migrations after creating these models (you can use `python manage.py makemigrations elm` and then `python manage.py migrate`). 

These are just basic examples. Depending on the exact requirements of your application, you might need additional fields or methods.
