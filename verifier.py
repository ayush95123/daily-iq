import re
from datetime import date, timedelta

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

# Pages on these domains are JS-rendered or login-walled; trust grounding instead
JS_OR_GATED_DOMAINS = {
    "leetcode.com",
    "teamblind.com",
    "glassdoor.com",
    "linkedin.com",
    "vertexaisearch.cloud.google.com",
}

STOP_WORDS = {
    "given", "array", "return", "where", "which", "there", "their",
    "about", "would", "could", "should", "number", "string", "value",
    "values", "elements", "element", "function", "design", "system",
}


def _strip_html(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).lower()


def _keywords(text: str) -> set[str]:
    words = re.findall(r"\b[a-zA-Z]{5,}\b", text.lower())
    return {w for w in words if w not in STOP_WORDS}


def _date_is_recent(post_date: str, cutoff: date) -> bool:
    try:
        if len(post_date) == 7:
            y, m = post_date.split("-")
            d = date(int(y), int(m), 1)
        else:
            d = date.fromisoformat(post_date[:10])
        return d >= cutoff
    except Exception:
        return False


def _is_gated(url: str) -> bool:
    return any(d in url for d in JS_OR_GATED_DOMAINS)


def _fetch(url: str) -> tuple[int, str]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        return resp.status_code, resp.text
    except Exception:
        return 0, ""


def _text_matches(question: str, page_html: str) -> bool:
    keywords = _keywords(question)
    if not keywords:
        return True
    page_text = _strip_html(page_html)
    matched = sum(1 for kw in keywords if kw in page_text)
    return matched / len(keywords) >= 0.35


def verify_questions(candidates: list[dict]) -> list[dict]:
    cutoff = date.today() - timedelta(days=180)
    verified = []

    for q in candidates:
        post_date = q.get("post_date", "")
        source_url = q.get("source_url", "")
        question_text = q.get("question", "")

        # --- date check (cheap, do first) ---
        if not _date_is_recent(post_date, cutoff):
            print(f"  DROP  [date too old] {post_date}")
            continue

        # --- skip fetch for gated/JS domains; trust grounding ---
        if _is_gated(source_url):
            print(f"  KEEP  [gated domain, trust grounding]")
            verified.append(q)
            continue

        # --- fetch source ---
        status, html = _fetch(source_url)

        if status == 0:
            print(f"  KEEP  [net err, trust grounding] {source_url[:60]}")
            verified.append(q)
            continue

        if status == 404:
            print(f"  DROP  [404] {source_url[:60]}")
            continue

        if status in (401, 403) or status >= 500:
            print(f"  KEEP  [{status} login/err, trust grounding] {source_url[:60]}")
            verified.append(q)
            continue

        # status 200 — keyword match
        if _text_matches(question_text, html):
            print(f"  KEEP  [200 + text match]")
            verified.append(q)
        else:
            print(f"  DROP  [200 but text mismatch] {question_text[:60]}")

    print(f"[verifier] {len(verified)}/{len(candidates)} passed verification")
    return verified
