from unittest.mock import MagicMock

from starlette.requests import Request

from main import RegistrationRequest, VerificationSendRequest, register_user, send_verification
from settings import settings
from verification_delivery import send_verification_code


def fake_request():
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
    )


class FakeCursor:
    def __init__(self, row=None):
        self.row = row
        self.executed = []
        self.result_rows = []

    def execute(self, query, params=None):
        self.executed.append((query, params))
        if "SELECT email, phone" in query or "INSERT INTO users" in query:
            self.result_rows = [self.row]
        else:
            self.result_rows = []

    def fetchone(self):
        return self.result_rows.pop(0) if self.result_rows else None

    def close(self):
        return None


class FakeConnection:
    def __init__(self, row=None):
        self.cursor_obj = FakeCursor(row)

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


def test_register_does_not_expose_verification_codes_by_default(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "dev")
    monkeypatch.setattr(settings, "EXPOSE_DEV_OTP", False)

    monkeypatch.setattr("main.get_connection", lambda: FakeConnection((1, "demo", "Demo User", "demo@example.com", "+8801712345678")))
    monkeypatch.setattr("main.create_verification_code_for_user", lambda *args, **kwargs: "123456")

    payload = RegistrationRequest(
        username="demo_user",
        full_name="Demo User",
        email="demo@example.com",
        phone="+8801712345678",
        password="StrongPass123!",
    )

    response = register_user(request=fake_request(), payload=payload)

    assert "verification_codes" not in response


def test_send_verification_does_not_expose_code_by_default(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "dev")
    monkeypatch.setattr(settings, "EXPOSE_DEV_OTP", False)

    monkeypatch.setattr("main.get_connection", lambda: FakeConnection(("demo@example.com", "+8801712345678")))
    monkeypatch.setattr("main.create_verification_code_for_user", lambda *args, **kwargs: "123456")
    monkeypatch.setattr("main.send_verification_code", lambda *args: None)

    response = send_verification(
        request=fake_request(),
        payload=VerificationSendRequest(channel="EMAIL"),
        current_user={"user_id": 99},
    )

    assert "code" not in response


def test_email_sender_uses_starttls_without_logging_code(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USERNAME", None)
    monkeypatch.setattr(settings, "SMTP_PASSWORD", None)
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "no-reply@example.com")

    smtp_context = MagicMock()
    smtp_client = smtp_context.__enter__.return_value
    monkeypatch.setattr("verification_delivery.smtplib.SMTP", lambda *args, **kwargs: smtp_context)

    send_verification_code("EMAIL", "student@example.com", "482731")

    smtp_client.starttls.assert_called_once_with()
    message = smtp_client.send_message.call_args.args[0]
    assert message["To"] == "student@example.com"
    assert "482731" in message.get_content()


def test_sms_sender_is_pluggable(monkeypatch):
    class FakeSmsSender:
        def __init__(self):
            self.sent = []

        def send(self, destination, code):
            self.sent.append((destination, code))

    sender = FakeSmsSender()
    monkeypatch.setattr("verification_delivery._sms_sender", sender)

    send_verification_code("PHONE", "+8801712345678", "482731")

    assert sender.sent == [("+8801712345678", "482731")]
