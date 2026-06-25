import json
import os
import re
from datetime import date, timedelta

import requests

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
]

PROMPT_TEMPLATE = """Today is {today}. The cutoff date is {cutoff}. Ignore anything posted before {cutoff}.

Search the web for RECENT interview experience posts — blog posts, forum threads, or discussion pages published AFTER {cutoff} — where a real candidate describes a DSA or system design question they were asked at a top tech company (Google, Meta, Amazon, Microsoft, Apple, Uber, Netflix, etc.).

Target sources: LeetCode Discuss, Blind (teamblind.com), Glassdoor, Reddit (r/leetcode, r/cscareerquestions), GeeksForGeeks experience pages, or personal engineering blogs.

Return ONLY a JSON array — no markdown, no explanation, just raw JSON.
Each element must have exactly these keys:
  "question"   : the full interview question as described by the candidate
  "topic"      : one of "DSA" or "System Design"
  "company"    : company name (from the post)
  "source_url" : direct URL to the discussion post or blog page
  "post_date"  : date the post was published (YYYY-MM-DD or YYYY-MM)

Strict rules:
- ONLY include questions where the source post was published after {cutoff}. Reject anything older.
- 10 to 15 questions total.
- source_url must link to the actual discussion thread, not a search result or homepage.
- post_date must be after {cutoff} — double-check before including.
- No duplicate questions.

Return only the JSON array, starting with [ and ending with ].
"""


def _build_prompt() -> str:
    today = date.today()
    cutoff = today - timedelta(days=180)
    return PROMPT_TEMPLATE.format(today=today.isoformat(), cutoff=cutoff.isoformat())


def _extract_json(text: str) -> list:
    # Strip markdown code fences if Gemini wraps the JSON
    text = re.sub(r"```(?:json)?", "", text).strip()
    # Find the outermost JSON array
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("No JSON array found in Gemini response")
    return json.loads(text[start : end + 1])


def retrieve_questions(api_key: str) -> list[dict]:
    payload = {
        "contents": [{"parts": [{"text": _build_prompt()}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"thinkingConfig": {"thinkingBudget": 0}},
    }

    data = None
    for model in GEMINI_MODELS:
        url = f"{GEMINI_BASE}/{model}:generateContent"
        try:
            resp = requests.post(url, params={"key": api_key}, json=payload, timeout=120)
            if resp.status_code in (429, 503):
                print(f"[retriever] {model}: {resp.status_code}, trying next...")
                continue
            resp.raise_for_status()
            data = resp.json()
            print(f"[retriever] using model: {model}")
            break
        except requests.exceptions.Timeout:
            print(f"[retriever] {model}: timeout, trying next...")
            continue

    if data is None:
        raise RuntimeError("All Gemini models unavailable. Try again later.")

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Gemini response shape: {e}\n{data}") from e

    questions = _extract_json(text)

    required_keys = {"question", "topic", "source_url", "post_date"}
    valid = []
    for q in questions:
        if required_keys.issubset(q.keys()) and q.get("source_url", "").startswith("http"):
            valid.append(q)

    print(f"[retriever] Gemini returned {len(questions)} items, {len(valid)} passed basic validation")
    return valid
