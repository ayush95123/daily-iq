import csv
import hashlib
import os
import re

LOG_FILE = os.path.join(os.path.dirname(__file__), "sent_log.csv")
LOG_HEADERS = ["date_sent", "question_hash", "topic", "company", "question_snippet"]
TARGET = 5


def _hash(question: str) -> str:
    normalized = re.sub(r"\s+", " ", question.lower().strip())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _load_sent_hashes() -> set[str]:
    if not os.path.exists(LOG_FILE):
        return set()
    with open(LOG_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["question_hash"] for row in reader if row.get("question_hash")}


def append_to_log(questions: list[dict], date_sent: str) -> None:
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_HEADERS)
        if not file_exists:
            writer.writeheader()
        for q in questions:
            writer.writerow({
                "date_sent": date_sent,
                "question_hash": _hash(q.get("question", "")),
                "topic": q.get("topic", ""),
                "company": q.get("company", ""),
                "question_snippet": q.get("question", "")[:80],
            })


def select_questions(verified: list[dict]) -> list[dict]:
    sent_hashes = _load_sent_hashes()
    print(f"[selector] sent_log has {len(sent_hashes)} past entries")

    fresh = [q for q in verified if _hash(q.get("question", "")) not in sent_hashes]
    print(f"[selector] {len(fresh)}/{len(verified)} are fresh (not previously sent)")

    # Prefer balanced mix: fill DSA slots first, then System Design
    dsa = [q for q in fresh if q.get("topic") == "DSA"]
    sd = [q for q in fresh if q.get("topic") == "System Design"]

    selected = []
    # Aim for 3 DSA + 2 System Design; adjust if one pool is short
    for pool, want in [(dsa, 3), (sd, 2)]:
        selected.extend(pool[:want])
    # Top up from whichever pool has leftovers
    if len(selected) < TARGET:
        used = set(id(q) for q in selected)
        extras = [q for q in fresh if id(q) not in used]
        selected.extend(extras[: TARGET - len(selected)])

    selected = selected[:TARGET]
    print(f"[selector] selected {len(selected)} questions")
    return selected
