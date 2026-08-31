from django.db import models


class Student(models.Model):
    index_number = models.CharField(max_length=20, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Student({self.index_number})"


class Course(models.Model):
    course_code = models.CharField(max_length=20, unique=True, db_index=True)
    course_title = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.course_code


class StudentCourse(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="courses")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="student_links")

    class Meta:
        unique_together = ("student", "course")


class TimetableEntry(models.Model):
    course_code = models.CharField(max_length=20, db_index=True)
    course_title = models.CharField(max_length=255, blank=True)
    exam_date = models.CharField(max_length=50, blank=True)
    exam_time = models.CharField(max_length=50, blank=True)
    exam_datetime = models.DateTimeField(null=True, blank=True)
    campus = models.CharField(max_length=100, blank=True)
    source_url = models.TextField(blank=True)
    last_scraped = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course_code} - {self.exam_date}"


class VenueAllocation(models.Model):
    timetable_entry = models.ForeignKey(
        TimetableEntry, on_delete=models.CASCADE, related_name="venue_allocations"
    )
    venue = models.CharField(max_length=255)
    range_start = models.CharField(max_length=30, blank=True)
    range_end = models.CharField(max_length=30, blank=True)
    allocation_text = models.TextField(blank=True)

    def __str__(self):
        return f"{self.venue} ({self.range_start}-{self.range_end})"


CONFIDENCE_CHOICES = [
    ("HIGH", "High"),
    ("MEDIUM", "Medium"),
    ("LOW", "Low"),
    ("UNKNOWN", "Unknown"),
]


class PersonalTimetableEntry(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="personal_entries")
    timetable_entry = models.ForeignKey(TimetableEntry, on_delete=models.CASCADE)
    assigned_venue = models.CharField(max_length=255, blank=True)
    exam_datetime = models.DateTimeField(null=True, blank=True)
    match_confidence = models.CharField(max_length=20, choices=CONFIDENCE_CHOICES, default="UNKNOWN")

    class Meta:
        unique_together = ("student", "timetable_entry")

    def __str__(self):
        return f"{self.student.index_number} - {self.timetable_entry.course_code}"
