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


def test_send_verification_does_not_expose_code_after_sms_delivery(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "dev")
    monkeypatch.setattr(settings, "EXPOSE_DEV_OTP", True)
    monkeypatch.setattr("main.get_connection", lambda: FakeConnection(("demo@example.com", "+8801712345678")))
    monkeypatch.setattr("main.create_verification_code_for_user", lambda *args, **kwargs: "123456")
    monkeypatch.setattr("main.send_verification_code", lambda *args: True)

    response = send_verification(
        request=fake_request(),
        payload=VerificationSendRequest(channel="PHONE"),
        current_user={"user_id": 99},
    )

    assert response["message"] == "A verification code was sent to your phone."
    assert "dev_code" not in response


def test_email_sender_uses_starttls_without_logging_code(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "prod")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "smtp")
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


def test_email_sender_uses_resend_https_api(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "prod")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "Campus X Mart <verify@example.com>")
    post = MagicMock()
    monkeypatch.setattr("verification_delivery.requests.post", post)

    send_verification_code("EMAIL", "student@example.com", "482731")

    post.assert_called_once_with(
        "https://api.resend.com/emails",
        headers={
            "Authorization": "Bearer test-api-key",
            "Content-Type": "application/json",
        },
        json={
            "from": "Campus X Mart <verify@example.com>",
            "to": ["student@example.com"],
            "subject": "Campus X Mart verification code",
            "text": "Your Campus X Mart verification code is 482731. It expires in 10 minutes.",
        },
        timeout=(3, 15),
    )
    post.return_value.raise_for_status.assert_called_once_with()


def test_email_sender_uses_resend_in_development(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "Campus X Mart <verify@example.com>")
    post = MagicMock()
    monkeypatch.setattr("verification_delivery.requests.post", post)

    delivered = send_verification_code("EMAIL", "student@example.com", "482731")

    assert delivered is True
    post.assert_called_once()


def test_resend_http_failure_is_reported_without_exposing_provider_response(monkeypatch):
    import requests

    from verification_delivery import VerificationDeliveryError

    monkeypatch.setattr(settings, "APP_ENV", "prod")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "verify@example.com")
    monkeypatch.setattr(
        "verification_delivery.requests.post",
        MagicMock(side_effect=requests.Timeout("provider timeout")),
    )

    try:
        send_verification_code("EMAIL", "student@example.com", "482731")
    except VerificationDeliveryError as error:
        assert str(error) == "Email verification delivery failed."
    else:
        raise AssertionError("Expected delivery failure.")


def test_sms_sender_is_pluggable(monkeypatch):
    class FakeSmsSender:
        def __init__(self):
            self.sent = []

        def send(self, destination, code):
            self.sent.append((destination, code))

    sender = FakeSmsSender()
    monkeypatch.setattr("verification_delivery._sms_sender", sender)

    assert send_verification_code("PHONE", "+8801712345678", "482731") is True

    assert sender.sent == [("+8801712345678", "482731")]


def test_sms_sender_uses_twilio_in_development_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "dev")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "test-account")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TWILIO_FROM_PHONE", "+15555550100")
    send_sms = MagicMock()
    monkeypatch.setattr("verification_delivery._send_twilio_sms", send_sms)

    delivered = send_verification_code("PHONE", "+8801712345678", "482731")

    assert delivered is True
    send_sms.assert_called_once_with("+8801712345678", "482731")


def test_sms_sender_uses_demo_fallback_in_development_without_twilio(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "dev")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", None)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", None)
    monkeypatch.setattr(settings, "TWILIO_FROM_PHONE", None)
    send_sms = MagicMock()
    monkeypatch.setattr("verification_delivery._send_twilio_sms", send_sms)

    delivered = send_verification_code("PHONE", "+8801712345678", "482731")

    assert delivered is False
    send_sms.assert_not_called()
