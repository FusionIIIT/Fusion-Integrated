from django.db import models



class Employee(models.Model):

       name = models.CharField(max_length=100)

       email = models.EmailField(unique=True)

       department = models.ForeignKey('Department', on_delete=models.CASCADE)



class Department(models.Model):

       name = models.CharField(max_length=100)

       location = models.CharField(max_length=100)



class Position(models.Model):

       title = models.CharField(max_length=100)

       department = models.ForeignKey('Department', on_delete=models.CASCADE)

       ctc_lpa = models.DecimalField(max_digits=8, decimal_places=2)
class Leave(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()


class Appraisal(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    performance_score = models.DecimalField(max_digits=5, decimal_places=2)
    feedback = models.TextField()


class LTC(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.TextField()


class CPDA(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.TextField()


class Approval(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.TextField()
