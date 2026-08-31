from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("timetable.urls")),
    path("", include("timetable.frontend_urls")),
]
