from django.db import models

# Faculty model
class Faculty(models.Model):
    faculty_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    password = models.CharField(max_length=100)  # For demo only
    is_absent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.faculty_id})"


# Classroom model (Semester)
class Classroom(models.Model):
    semester = models.CharField(max_length=20)

    def __str__(self):
        return f"Semester {self.semester}"


# Subject model
class Subject(models.Model):
    course_id = models.CharField(max_length=20, unique=True)
    subject_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.subject_name} ({self.course_id})"


# Subject Assignment model
class Assignment(models.Model):
    CLASS_TYPE_CHOICES = [
        ("Lecture", "Lecture"),
        ("Lab", "Lab"),
    ]
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    class_type = models.CharField(max_length=10, choices=CLASS_TYPE_CHOICES)

    def __str__(self):
        return f"{self.faculty.name} - {self.subject.subject_name} ({self.class_type})"


# Timetable models
DAYS_OF_WEEK = [
    ("Mon", "Monday"),
    ("Tue", "Tuesday"),
    ("Wed", "Wednesday"),
    ("Thu", "Thursday"),
    ("Fri", "Friday"),
]

PERIOD_CHOICES = [(i, f"P{i}") for i in range(1, 7)]  # 6 periods/day

class TimeSlot(models.Model):
    day = models.CharField(max_length=3, choices=DAYS_OF_WEEK)
    period = models.IntegerField(choices=PERIOD_CHOICES)

    def __str__(self):
        return f"{self.day}-P{self.period}"


class TimetableEntry(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    class_type = models.CharField(max_length=10, choices=Assignment.CLASS_TYPE_CHOICES)

    def __str__(self):
        return f"{self.time_slot} | {self.faculty.name} | {self.subject.subject_name} | {self.class_type}"
