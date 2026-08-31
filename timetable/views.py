import json
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from timetable.scraper import crawl_and_match
from timetable.sorter import sort_entries, make_exam_datetime
from timetable.pdf_parser import parse_pdf_timetable
from timetable.models import (
    Student, Course, StudentCourse,
    TimetableEntry, VenueAllocation, PersonalTimetableEntry,
)
from timetable.pdf_gen import build_pdf


def _get_or_create_student(index_number):
    student, _ = Student.objects.get_or_create(index_number=index_number)
    return student


def _persist_results(student, results):
    for r in results:
        code = r["course_code"]
        course, _ = Course.objects.get_or_create(
            course_code=code,
            defaults={"course_title": r.get("course_title", "")}
        )
        StudentCourse.objects.get_or_create(student=student, course=course)
        exam_dt = make_exam_datetime(r.get("exam_date", ""), r.get("exam_time", ""))
        entry, _ = TimetableEntry.objects.update_or_create(
            course_code=code,
            defaults={
                "course_title": r.get("course_title", ""),
                "exam_date": r.get("exam_date", ""),
                "exam_time": r.get("exam_time", ""),
                "exam_datetime": exam_dt,
                "campus": r.get("campus", ""),
                "source_url": r.get("detail_url", ""),
            }
        )
        for alloc in r.get("allocations", []):
            VenueAllocation.objects.get_or_create(
                timetable_entry=entry,
                venue=alloc["venue"],
                range_start=alloc.get("range_start", ""),
                range_end=alloc.get("range_end", ""),
                defaults={"allocation_text": alloc.get("allocation_text", "")},
            )
        PersonalTimetableEntry.objects.update_or_create(
            student=student,
            timetable_entry=entry,
            defaults={
                "assigned_venue": r.get("venue", ""),
                "exam_datetime": exam_dt,
                "match_confidence": r.get("confidence", "UNKNOWN"),
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class GenerateTimetableView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        index_number = body.get("index_number", "").strip()
        course_codes = [c.strip() for c in body.get("course_codes", []) if c.strip()]

        if not index_number:
            return JsonResponse({"error": "Index number is required."}, status=400)
        if not course_codes:
            return JsonResponse({"error": "Please enter at least one course code."}, status=400)

        try:
            results = crawl_and_match(
                index_number=index_number,
                course_codes=course_codes,
                base_url=settings.UG_TIMETABLE_URL,
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        sorted_results = sort_entries(results)
        student = _get_or_create_student(index_number)
        _persist_results(student, sorted_results)

        return JsonResponse({
            "index_number": index_number,
            "total": len(sorted_results),
            "entries": sorted_results,
        })


@method_decorator(csrf_exempt, name="dispatch")
class UploadPdfTimetableView(View):
    def post(self, request):
        pdf_file = request.FILES.get("pdf_file")
        if not pdf_file:
            return JsonResponse({"error": "Please upload a timetable PDF file."}, status=400)

        raw_courses = request.POST.get("course_codes", "")
        try:
            course_codes = json.loads(raw_courses) if raw_courses.startswith("[") else [c.strip() for c in raw_courses.split(",") if c.strip()]
        except Exception:
            course_codes = [c.strip() for c in raw_courses.split(",") if c.strip()]

        if not course_codes:
            return JsonResponse({"error": "Please specify at least one course code."}, status=400)

        try:
            results = parse_pdf_timetable(pdf_file.file, course_codes)
        except Exception as e:
            return JsonResponse({"error": f"Failed to parse PDF: {str(e)}"}, status=500)

        return JsonResponse({
            "index_number": "PDF Timetable",
            "source": "Uploaded PDF Document",
            "total": len(results),
            "entries": results,
        })


@method_decorator(csrf_exempt, name="dispatch")
class DownloadPDFView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        index_number = body.get("index_number", "PDF Timetable").strip()
        entries = body.get("entries", [])

        if entries:
            pdf_bytes = build_pdf(index_number, entries)
            resp = HttpResponse(pdf_bytes, content_type="application/pdf")
            resp["Content-Disposition"] = f'attachment; filename="orchestra-{index_number.replace(" ", "_")}.pdf"'
            return resp

        course_codes = [c.strip() for c in body.get("course_codes", []) if c.strip()]
        if not course_codes:
            return JsonResponse({"error": "Course codes required"}, status=400)

        results = crawl_and_match(
            index_number=index_number,
            course_codes=course_codes,
            base_url=settings.UG_TIMETABLE_URL,
        )
        sorted_results = sort_entries(results)
        pdf_bytes = build_pdf(index_number, sorted_results)
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="orchestra-{index_number}.pdf"'
        return resp


class HealthView(View):
    def get(self, request):
        return JsonResponse({"status": "ok", "service": "Orchestra"})
