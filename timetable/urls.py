from django.urls import path
from timetable.views import GenerateTimetableView, UploadPdfTimetableView, DownloadPDFView, HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("timetable/generate/", GenerateTimetableView.as_view(), name="generate"),
    path("timetable/upload-pdf/", UploadPdfTimetableView.as_view(), name="upload_pdf"),
    path("timetable/pdf/", DownloadPDFView.as_view(), name="pdf"),
]
