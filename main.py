import os
import sys
from datetime import date

from dotenv import load_dotenv

from emailer import send_email as _send
from retriever import retrieve_questions as _retrieve
from selector import append_to_log, select_questions as _select
from verifier import verify_questions as _verify

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

MIN_QUESTIONS = 1  # send whatever we have if fewer than 5 pass verification


def main():
    print("=== daily-iq starting ===")

    # Phase 2 — retrieve
    print("\n[1/4] Retrieving candidates from Gemini...")
    candidates = _retrieve(GEMINI_API_KEY)

    if not candidates:
        print("ERROR: Retrieval returned 0 candidates. Aborting.")
        sys.exit(1)

    # Phase 3 — verify
    print("\n[2/4] Verifying candidates...")
    verified = _verify(candidates)

    if not verified:
        print("ERROR: No candidates passed verification. Aborting.")
        sys.exit(1)

    # Phase 4 — dedup + select
    print("\n[3/4] Selecting questions...")
    final = _select(verified)

    if len(final) < MIN_QUESTIONS:
        print(f"WARNING: Only {len(final)} fresh question(s) available — skipping email to avoid low-quality send.")
        sys.exit(0)

    if len(final) < 5:
        print(f"WARNING: Fewer than 5 questions available ({len(final)}). Sending what we have.")

    # Phase 5 — email
    print("\n[4/4] Sending email...")
    _send(final, GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL)

    # Persist selections to dedup log
    today = date.today().isoformat()
    append_to_log(final, today)
    print(f"[main] Appended {len(final)} entries to sent_log.csv")

    print("\n=== daily-iq done ===")


if __name__ == "__main__":
    main()
