import io
import re
from datetime import datetime


def _esc(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(index_number: str, entries: list[dict]) -> bytes:
    now = datetime.now().strftime("%a, %b %d, %Y")
    PW, PH = 595, 842
    MARGIN = 36
    row_h = 24

    def txt_op(x, y, size, text, bold=False):
        font = "F2" if bold else "F1"
        return f"BT /{font} {size} Tf {x} {y} Td ({_esc(str(text))}) Tj ET\n"

    def rect_op(x, y, w_, h_, r=0, g=0, b=0, fill=True):
        op = "f" if fill else "S"
        cmd = "rg" if fill else "RG"
        return f"{r:.3f} {g:.3f} {b:.3f} {cmd} {x} {y} {w_} {h_} re {op}\n"

    content = ""
    content += rect_op(0, 0, PW, PH, 0.059, 0.106, 0.220)
    content += rect_op(0, PH-75, PW, 75, 0.094, 0.169, 0.341)
    content += rect_op(0, PH-77, PW, 2, 0.898, 0.753, 0.482)

    content += "1 1 1 rg\n"
    content += txt_op(MARGIN, PH-42, 22, "ORCHESTRA", bold=True)
    content += "0.898 0.753 0.482 rg\n"
    content += txt_op(MARGIN, PH-60, 9.5, "Personal Examination Timetable  |  University of Ghana")

    content += rect_op(MARGIN, PH-115, PW-2*MARGIN, 30, 0.082, 0.145, 0.302)
    content += "0.95 0.95 0.98 rg\n"
    content += txt_op(MARGIN+10, PH-100, 9, f"Student / Source: {index_number}", bold=True)
    content += txt_op(340, PH-100, 8.5, f"Generated: {now}")
    content += "0.898 0.753 0.482 rg\n"
    content += txt_op(MARGIN+10, PH-111, 7.5, f"Total Examinations: {len(entries)}")

    y = PH - 145
    content += rect_op(MARGIN, y-2, PW-2*MARGIN, 18, 0.125, 0.220, 0.439)
    content += rect_op(MARGIN, y-2, PW-2*MARGIN, 1, 0.898, 0.753, 0.482)

    content += "0.898 0.753 0.482 rg\n"
    header_cols = [
        (MARGIN+4,   "DATE"),
        (MARGIN+95,  "TIME"),
        (MARGIN+165, "COURSE"),
        (MARGIN+235, "COURSE TITLE"),
        (MARGIN+385, "VENUE / MODE"),
    ]
    for cx, ch in header_cols:
        content += txt_op(cx, y+3, 7.5, ch, bold=True)

    y -= 6

    for i, e in enumerate(entries):
        fill_r, fill_g, fill_b = (0.094, 0.169, 0.341) if i%2==0 else (0.070, 0.125, 0.259)
        content += rect_op(MARGIN, y-row_h+4, PW-2*MARGIN, row_h, fill_r, fill_g, fill_b)
        ry = y - 12
        content += "0.95 0.95 0.98 rg\n"
        content += txt_op(MARGIN+4,   ry, 7.5, str(e.get("exam_date",""))[:18])
        content += "0.95 0.85 0.55 rg\n"
        content += txt_op(MARGIN+95,  ry, 7.5, str(e.get("exam_time",""))[:10], bold=True)
        content += "1 1 1 rg\n"
        content += txt_op(MARGIN+165, ry, 7.5, str(e.get("course_code",""))[:10], bold=True)
        content += "0.90 0.90 0.95 rg\n"
        content += txt_op(MARGIN+235, ry, 7,   str(e.get("course_title",""))[:25])
        venue_str = str(e.get("venue",""))
        if len(venue_str) > 28:
            venue_str = venue_str[:26] + "..."
        content += "0.80 0.85 0.95 rg\n"
        content += txt_op(MARGIN+385, ry, 7, venue_str)
        
        y -= row_h
        if y < 50:
            break

    content += rect_op(0, 0, PW, 28, 0.094, 0.169, 0.341)
    content += rect_op(0, 27, PW, 1, 0.898, 0.753, 0.482)
    content += "1 1 1 rg\n"
    content += txt_op(MARGIN, 10, 7.5, "Orchestra | Personal Examination Timetable | sts.ug.edu.gh")

    cb = content.encode("latin-1", errors="replace")
    out = io.BytesIO()
    offsets = {}

    def write(s: str):
        out.write(s.encode("latin-1", errors="replace"))

    write("%PDF-1.4\n")
    write("%\xe2\xe3\xcf\xd3\n")

    offsets[1] = out.tell()
    write("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

    offsets[2] = out.tell()
    write(f"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")

    offsets[3] = out.tell()
    write(f"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PW} {PH}] /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>\nendobj\n")

    offsets[4] = out.tell()
    write(f"4 0 obj\n<< /Length {len(cb)} >>\nstream\n")
    out.write(cb)
    write("\nendstream\nendobj\n")

    offsets[5] = out.tell()
    write("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    offsets[6] = out.tell()
    write("6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n")

    xref_pos = out.tell()
    write("xref\n")
    write("0 7\n")
    write("0000000000 65535 f \n")
    for i in range(1, 7):
        write(f"{offsets[i]:010d} 00000 n \n")

    write("trailer\n")
    write("<< /Size 7 /Root 1 0 R >>\n")
    write("startxref\n")
    write(f"{xref_pos}\n")
    write("%%EOF\n")

    return out.getvalue()
