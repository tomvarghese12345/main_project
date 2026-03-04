from django.db import models
from accounts.models import Faculty   # ✅ IMPORTANT


class CourseDiary(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    date = models.DateField()

    HOUR_CHOICES = [
        ('1', 'Hour 1'),
        ('2', 'Hour 2'),
        ('3', 'Hour 3'),
        ('4', 'Hour 4'),
        ('5', 'Hour 5'),
        ('6', 'Hour 6'),
    ]
    hour = models.CharField(max_length=10, choices=HOUR_CHOICES)

    module = models.CharField(max_length=100)
    topic = models.CharField(max_length=300)
    summary = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.faculty.name} - {self.date}"


class LeaveApplication(models.Model):
    STATUS_PENDING = 'Pending'
    STATUS_APPROVED = 'Approved'
    STATUS_REJECTED = 'Rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name='leave_applications'
    )
    from_date = models.DateField()
    to_date = models.DateField()
    topic = models.CharField(max_length=255)
    generated_letter = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    applied_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.faculty.name} | {self.from_date} to {self.to_date} | {self.status}"