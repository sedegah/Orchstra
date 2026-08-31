import io
import re
from typing import BinaryIO
from pypdf import PdfReader
from timetable.sorter import sort_entries, format_short_date, format_clean_time

_DATE_BANNER_RE = re.compile(
    r"\b((?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)[,\s]+"
    r"(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d{1,2}[,\s]+\d{4})\b",
    re.IGNORECASE
)

_TIME_TOKEN_RE = re.compile(
    r"\b(\d{1,2}:\d{2}\s*(?:AM|PM))\b",
    re.IGNORECASE
)

_COURSE_CODE_RE = re.compile(
    r"\b([A-Z]{2,6}\d{2,4}(?:/[A-Z]{2,6}\d{2,4})*)\b"
)


def _normalize_code(code: str) -> str:
    return re.sub(r"\s+", "", code).upper()


def smart_title(s: str) -> str:
    def cap_word(w):
        if w.isupper() and len(w) >= 2:
            return w
        return w.capitalize()
    return " ".join(cap_word(w) for w in s.split())


def parse_pdf_timetable(pdf_file: BinaryIO, target_courses: list[str]) -> list[dict]:
    normalized_targets = {_normalize_code(c): c for c in target_courses}
    reader = PdfReader(pdf_file)
    extracted_entries = []

    current_date = "Date TBA"
    current_time = "Time TBA"

    for page in reader.pages:
        text = page.extract_text()
        if not text:
            continue

        lines = [l.strip() for l in text.split("\n") if l.strip()]

        for line in lines:
            date_match = _DATE_BANNER_RE.search(line)
            if date_match:
                current_date = format_short_date(date_match.group(1).strip())

            time_match = _TIME_TOKEN_RE.search(line)
            if time_match and any(k in line.upper() for k in ["AM", "PM"]):
                if len(line) < 18:
                    current_time = format_clean_time(time_match.group(1))

            codes_in_line = _COURSE_CODE_RE.findall(line)
            matched_code = None

            for raw_c in codes_in_line:
                for sub_c in raw_c.split("/"):
                    c_norm = _normalize_code(sub_c)
                    if c_norm in normalized_targets:
                        matched_code = c_norm
                        break
                if matched_code:
                    break

            if matched_code:
                line_time = None
                t_match = _TIME_TOKEN_RE.search(line)
                if t_match:
                    line_time = format_clean_time(t_match.group(1))

                exam_time = line_time or current_time
                exam_date = current_date

                mode_of_exam = "Onsite / Physical"
                if "ONLINE/ONSITE USING SAKAI" in line.upper() or "ONLINE" in line.upper():
                    mode_of_exam = "Online / Onsite using Sakai"
                elif "WITH ANSWER BOOKLET" in line.upper():
                    mode_of_exam = "Onsite (Physical Answer Booklet)"

                clean_title = line
                clean_title = re.sub(_COURSE_CODE_RE, "", clean_title)
                clean_title = re.sub(_TIME_TOKEN_RE, "", clean_title)
                clean_title = re.sub(r"(?:ONSITE|ONLINE|PHYSICAL|WITH ANSWER BOOKLET|USING SAKAI|MANUAL).*", "", clean_title, flags=re.IGNORECASE)
                clean_title = re.sub(r"\s+\d+(\s+\d+)*\s*$", "", clean_title)
                clean_title = clean_title.strip(" -|,\t")

                campus_info = "University of Ghana"
                counts = re.findall(r"\b\d+\b", line)
                if len(counts) >= 3:
                    accra_count = int(counts[-4] if len(counts)>=4 else counts[0])
                    health_count = int(counts[-3] if len(counts)>=4 else counts[1])
                    main_count = int(counts[-2] if len(counts)>=4 else counts[2])
                    active_campuses = []
                    if accra_count > 0:
                        active_campuses.append("Accra City Campus")
                    if health_count > 0:
                        active_campuses.append("College of Health Sciences")
                    if main_count > 0:
                        active_campuses.append("Main Campus")
                    if active_campuses:
                        campus_info = ", ".join(active_campuses)

                extracted_entries.append({
                    "course_code": matched_code,
                    "course_title": smart_title(clean_title) if clean_title else "Course Schedule",
                    "exam_date": exam_date,
                    "exam_time": exam_time,
                    "campus": campus_info,
                    "venue": mode_of_exam,
                    "allocations": [],
                    "detail_url": "",
                })

    seen = set()
    unique = []
    for e in extracted_entries:
        key = (e["course_code"], e["exam_date"], e["exam_time"], e["campus"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return sort_entries(unique)
