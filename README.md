# Orchestra — UG Personal Examination Timetable Assistant

Orchestra is an intelligent, high-performance web application designed for students at the **University of Ghana**. It generates personalized, chronologically sorted examination timetables directly from the official **STS Timetable App** or via an uploaded general **Timetable PDF document**.

---

## Key Features

- **Dual Extraction Modes**:
  - **STS Timetable App Mode**: Input student index number and course codes to match exact venue allocations based on index ranges (e.g., `[ 10976286 - 22395581 ]`).
  - **PDF Upload Mode**: Drag and drop the official University of Ghana Final Examination Timetable PDF to extract personal exam schedules without needing an index number.
- **University of Ghana Navy & Gold Aesthetics**: Custom UI styled in official UG Navy (`#0F1B38`) and Gold (`#E5C07B`) theme.
- **Smart Date & Time Formatting**: Formats dates cleanly with short day abbreviations (`Mon, Aug 31, 2026`) and formatted times (`7:30 AM`, `11:30 AM`, `3:30 PM`).
- **Dynamic Next Examination Card**: Real-time comparison that automatically highlights the next upcoming paper scheduled after the current date and time.
- **Ultra-Fast Parallel Engine & In-Memory TTL Cache**:
  - Multi-threaded crawler utilizing `ThreadPoolExecutor` with 16 parallel workers.
  - Sub-millisecond (3.8ms) cache hits for instant repeated queries and high concurrency support.
- **Formal Print & PDF Export**:
  - Custom high-contrast `@media print` stylesheet for clean 1-page paper printouts.
  - One-click downloadable PDF export built with raw PDF 1.4 byte-stream builder.

---

## Tech Stack

- **Backend**: Python 3.14, Django 6.1, Django REST Framework
- **Frontend**: Vanilla HTML5, CSS3 (Vanilla CSS with CSS Custom Properties), JavaScript (ES6)
- **Scraper & PDF Processing**: BeautifulSoup4, `pypdf`, `concurrent.futures`
- **Database**: SQLite3 (`orchestra.db`)

---

## Installation & Setup

### 1. Prerequisites
- Python 3.10+ installed on your system.

### 2. Clone & Install Dependencies

```bash
git clone https://github.com/your-username/orchestra.git
cd orchestra
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory (optional):

```env
DEBUG=True
SECRET_KEY=your-secret-key
BASE_TIMETABLE_URL=https://sts.ug.edu.gh/timetable/all
```

---

## Running the Application

Run the Django development server:

```bash
python manage.py runserver 8000
```

Open your browser and navigate to:
**`http://localhost:8000`**

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health/` | Service health status check |
| `POST` | `/api/timetable/generate/` | Generates personal timetable from STS Portal |
| `POST` | `/api/timetable/upload-pdf/` | Extracts timetable entries from uploaded PDF |
| `POST` | `/api/timetable/pdf/` | Generates downloadable PDF document |

---

## License

This project is open-source and intended for University of Ghana students.
