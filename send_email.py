from __future__ import annotations

import base64
import os
from email.message import EmailMessage
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from card_exporter import ISSUE_TITLE, date_range_label, load_records


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
HTML_PATH = Path("output/news.html")


def build_message(sender, recipient, subject, html_body):
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(
        "HTML 메일을 표시할 수 있는 메일 클라이언트에서 확인해 주세요."
    )
    message.add_alternative(html_body, subtype="html")
    return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")


def create_gmail_service():
    credentials = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def send_digest(service, sender, recipient, subject, html_body):
    raw = build_message(sender, recipient, subject, html_body)
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()


def build_subject(records):
    date_range = date_range_label(records)
    if date_range:
        return f"[{ISSUE_TITLE}] {date_range}"
    return f"[{ISSUE_TITLE}]"


def main():
    sender = os.environ["MAIL_FROM"]
    recipient = os.environ["MAIL_TO"]
    records = load_records()
    subject = build_subject(records)
    html_body = HTML_PATH.read_text(encoding="utf-8")
    result = send_digest(
        create_gmail_service(),
        sender,
        recipient,
        subject,
        html_body,
    )
    print(f"sent weekly digest: {result.get('id', 'unknown')}")


if __name__ == "__main__":
    main()
