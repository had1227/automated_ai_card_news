import base64
from email import message_from_bytes
from email.header import decode_header, make_header

import send_email


def _decode_raw_message(raw):
    decoded = base64.urlsafe_b64decode(raw.encode("ascii"))
    return message_from_bytes(decoded)


def test_build_message_contains_html_digest_and_utf8_subject():
    raw = send_email.build_message(
        "sender@gmail.com",
        "reader@gmail.com",
        "[이번 주 AI 핵심 뉴스] 2026.05.18 - 2026.05.24",
        "<h1>이번 주 AI 핵심 뉴스</h1>",
    )
    message = _decode_raw_message(raw)
    subject = str(make_header(decode_header(message["Subject"])))

    assert message["From"] == "sender@gmail.com"
    assert message["To"] == "reader@gmail.com"
    assert "이번 주 AI 핵심 뉴스" in subject
    assert "text/html" in message.as_string()


def test_build_subject_uses_rendered_date_range():
    subject = send_email.build_subject(
        [{"published_at": "2026-05-18"}, {"published_at": "2026-05-24"}]
    )

    assert subject == "[이번 주 AI 핵심 뉴스] 2026.05.18 - 2026.05.24"


def test_send_digest_calls_gmail_messages_send():
    calls = {}

    class Request:
        def execute(self):
            return {"id": "message-123"}

    class Messages:
        def send(self, userId, body):
            calls["userId"] = userId
            calls["body"] = body
            return Request()

    class Users:
        def messages(self):
            return Messages()

    class Service:
        def users(self):
            return Users()

    result = send_email.send_digest(
        Service(),
        "sender@gmail.com",
        "reader@gmail.com",
        "subject",
        "<p>body</p>",
    )

    assert result == {"id": "message-123"}
    assert calls["userId"] == "me"
    assert "raw" in calls["body"]
