import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _build_body(questions: list[dict]) -> tuple[str, str]:
    today = date.today().strftime("%d %b %Y")
    header = f"Daily Interview Questions — {today}\n{'=' * 45}\n\n"

    plain_parts = [header]
    html_rows = []

    for i, q in enumerate(questions, 1):
        topic = q.get("topic", "")
        company = q.get("company", "Unknown")
        question = q.get("question", "")
        source = q.get("source_url", "")
        post_date = q.get("post_date", "")

        # Plain text block
        plain_parts.append(
            f"Q{i}. [{topic}] {company}\n"
            f"{question}\n"
            f"Source: {source}\n"
            f"Posted: {post_date}\n\n"
        )

        # HTML block
        html_rows.append(f"""
        <tr>
          <td style="padding:14px 0; border-bottom:1px solid #eee; vertical-align:top;">
            <span style="background:{'#0066cc' if topic=='DSA' else '#2e8b57'};color:#fff;
                         font-size:11px;padding:2px 7px;border-radius:3px;font-weight:bold;">
              {topic}
            </span>
            <span style="color:#888;font-size:12px;margin-left:8px;">{company} &bull; {post_date}</span>
            <p style="margin:8px 0 6px;font-size:15px;color:#222;line-height:1.5;">{question}</p>
            <a href="{source}" style="font-size:12px;color:#0066cc;">View source &rarr;</a>
          </td>
        </tr>""")

    plain_body = "".join(plain_parts) + "---\nYou are receiving this because you subscribed to daily-iq."

    html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;padding:20px;color:#333;">
  <h2 style="color:#111;border-bottom:2px solid #0066cc;padding-bottom:8px;">
    Daily Interview Questions
    <span style="font-size:14px;font-weight:normal;color:#888;">{today}</span>
  </h2>
  <table width="100%" cellpadding="0" cellspacing="0">
    {"".join(html_rows)}
  </table>
  <p style="font-size:11px;color:#aaa;margin-top:24px;">daily-iq &mdash; automated interview question digest</p>
</body>
</html>"""

    return plain_body, html_body


def send_email(
    questions: list[dict],
    gmail_user: str,
    app_password: str,
    recipient: str,
) -> None:
    if not questions:
        print("[emailer] No questions to send — skipping.")
        return

    today = date.today().strftime("%d %b %Y")
    subject = f"Daily Interview Questions — {today}"

    plain_body, html_body = _build_body(questions)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(gmail_user, app_password)
        server.sendmail(gmail_user, recipient, msg.as_string())

    print(f"[emailer] Email sent to {recipient} — {len(questions)} questions.")
