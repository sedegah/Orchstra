import urllib.parse
import urllib.request
import re
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from timetable.sorter import sort_entries

# Fast Thread-safe In-Memory Cache (TTL: 15 minutes = 900s)
_MEM_CACHE = {}
_CACHE_TTL = 900

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def normalize_code(code: str) -> str:
    return re.sub(r"\s+", "", code).upper()


def get_cached(key: str):
    now = time.time()
    if key in _MEM_CACHE:
        val, ts = _MEM_CACHE[key]
        if now - ts < _CACHE_TTL:
            return val
    return None


def set_cached(key: str, val):
    _MEM_CACHE[key] = (val, time.time())


def fetch_url(url: str, timeout: int = 8) -> str:
    cache_key = f"raw_html_{url}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    try:
        encoded_url = urllib.parse.quote(url, safe=":/%?=#")
        req = urllib.request.Request(encoded_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            set_cached(cache_key, html)
            return html
    except Exception:
        return ""


def fetch_page_cards(url: str) -> list[dict]:
    cache_key = f"parsed_cards_{url}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    html = fetch_url(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_=lambda c: c and "card" in c)
    parsed = []

    for card in cards:
        a_tag = card.find("a", href=True)
        if not a_tag:
            continue

        card_text = card.get_text()
        norm_card_text = normalize_code(card_text)
        detail_url = a_tag["href"]
        full_header = a_tag.get_text(strip=True)
        c_title = re.sub(r"^[A-Z0-9\/\-]+\s*[\-\:]\s*", "", full_header, flags=re.IGNORECASE)

        e_date = ""
        e_time = ""
        date_p = card.find(string=re.compile(r"Date:", re.I))
        if date_p:
            p_text = date_p.parent.get_text(strip=True) if date_p.parent else str(date_p)
            m_dt = re.search(r"Date:\s*([^\|]+)", p_text, re.I)
            if m_dt:
                e_date = m_dt.group(1).strip()
            m_tm = re.search(r"Time:\s*(.*)", p_text, re.I)
            if m_tm:
                e_time = m_tm.group(1).strip()

        campus = ""
        camp_el = card.find(string=re.compile(r"Campus:", re.I))
        if camp_el and camp_el.parent:
            campus = camp_el.parent.get_text(strip=True).replace("Campus:", "").strip()

        parsed.append({
            "norm_text": norm_card_text,
            "full_header": full_header,
            "course_title": c_title,
            "exam_date": e_date,
            "exam_time": e_time,
            "campus": campus,
            "detail_url": detail_url,
        })

    set_cached(cache_key, parsed)
    return parsed


def parse_detail_page(detail_url: str) -> list[dict]:
    cache_key = f"detail_alloc_{detail_url}"
    cached_allocs = get_cached(cache_key)
    if cached_allocs is not None:
        return cached_allocs

    allocations = []
    html = fetch_url(detail_url)
    if not html:
        return allocations

    soup = BeautifulSoup(html, "html.parser")
    for li in soup.find_all("li"):
        text = li.get_text(strip=True)
        match = re.search(r"^(.*?)\s*\|\s*\[\s*(\d+)\s*-\s*(\d+)\s*\]$", text)
        if match:
            allocations.append({
                "venue": match.group(1).strip(" -|,\t"),
                "range_start": match.group(2),
                "range_end": match.group(3),
                "allocation_text": text,
            })

    if not allocations:
        full_text = soup.get_text()
        matches = re.finditer(r"([A-Za-z0-9\s\.\,\'\-\/\(\)]+?)\s*\|\s*\[\s*(\d+)\s*-\s*(\d+)\s*\]", full_text)
        for m in matches:
            allocations.append({
                "venue": m.group(1).strip(" -|,\t"),
                "range_start": m.group(2),
                "range_end": m.group(3),
                "allocation_text": m.group(0),
            })

    set_cached(cache_key, allocations)
    return allocations


def is_index_in_range(index_num: int, start_str: str, end_str: str) -> bool:
    try:
        return int(start_str) <= index_num <= int(end_str)
    except ValueError:
        return False


def crawl_and_match(index_number: str, course_codes: list[str], base_url: str) -> list[dict]:
    target_map = {normalize_code(c): c for c in course_codes}
    idx_num = None
    try:
        idx_num = int(index_number.strip())
    except ValueError:
        pass

    # 1. Fetch & parse all portal pages in parallel (16 concurrent threads)
    page_urls = [f"{base_url}?page={p}" if p > 1 else base_url for p in range(1, 16)]
    matched_cards = []

    with ThreadPoolExecutor(max_workers=16) as executor:
        future_to_url = {executor.submit(fetch_page_cards, url): url for url in page_urls}
        for future in as_completed(future_to_url):
            parsed_cards = future.result()
            for card in parsed_cards:
                norm_text = card["norm_text"]
                for norm_c, orig_c in target_map.items():
                    if norm_c in norm_text:
                        item = dict(card)
                        item["course_code"] = orig_c
                        matched_cards.append(item)

    # 2. Fetch detail pages in parallel for matching courses
    unique_detail_urls = list({e["detail_url"] for e in matched_cards if e.get("detail_url")})
    detail_alloc_map = {}

    if unique_detail_urls:
        with ThreadPoolExecutor(max_workers=16) as executor:
            future_to_detail = {executor.submit(parse_detail_page, d_url): d_url for d_url in unique_detail_urls}
            for future in as_completed(future_to_detail):
                d_url = future_to_detail[future]
                detail_alloc_map[d_url] = future.result()

    # 3. Match student index to venue allocation ranges
    results = []
    for e in matched_cards:
        d_url = e.get("detail_url", "")
        allocations = detail_alloc_map.get(d_url, [])
        assigned_venue = "See Detail Page"

        if idx_num is not None and allocations:
            matched_v = None
            for a in allocations:
                if a.get("range_start") and a.get("range_end"):
                    if is_index_in_range(idx_num, a["range_start"], a["range_end"]):
                        matched_v = a["venue"]
                        break
            if matched_v:
                assigned_venue = matched_v
            else:
                assigned_venue = allocations[0]["venue"]
        elif allocations:
            assigned_venue = allocations[0]["venue"]

        results.append({
            "course_code": e["course_code"],
            "course_title": e["course_title"],
            "exam_date": e["exam_date"],
            "exam_time": e["exam_time"],
            "campus": e["campus"],
            "venue": assigned_venue,
            "allocations": allocations,
            "detail_url": d_url,
        })

    # Deduplicate
    seen = set()
    unique = []
    for r in results:
        key = (r["course_code"], r["exam_date"], r["exam_time"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return sort_entries(unique)
