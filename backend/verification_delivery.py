import smtplib
from email.message import EmailMessage
from typing import Optional, Protocol

from settings import settings


class VerificationDeliveryError(Exception):
    pass


class SmsVerificationSender(Protocol):
    def send(self, destination: str, code: str) -> None: ...


_sms_sender: Optional[SmsVerificationSender] = None


def configure_sms_sender(sender: SmsVerificationSender) -> None:
    global _sms_sender
    _sms_sender = sender


def send_verification_code(channel: str, destination: str, code: str) -> None:
    normalized_channel = channel.upper()
    if normalized_channel == "PHONE":
        if _sms_sender is not None:
            _sms_sender.send(destination, code)
            return
        if settings.APP_ENV == "dev":
            return
        _send_twilio_sms(destination, code)
        return

    if normalized_channel != "EMAIL":
        raise VerificationDeliveryError("Unsupported verification channel.")

    if settings.APP_ENV == "dev":
        return

    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise VerificationDeliveryError("Email verification delivery is not configured.")
    if bool(settings.SMTP_USERNAME) != bool(settings.SMTP_PASSWORD):
        raise VerificationDeliveryError("SMTP credentials are incomplete.")

    message = EmailMessage()
    message["Subject"] = "Campus X Mart verification code"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = destination
    message.set_content(
        f"Your Campus X Mart verification code is {code}. It expires in 10 minutes."
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as client:
            client.starttls()
            if settings.SMTP_USERNAME:
                client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise VerificationDeliveryError("Email verification delivery failed.") from exc


def _send_twilio_sms(destination: str, code: str) -> None:
    if not all((settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_FROM_PHONE)):
        raise VerificationDeliveryError("SMS verification delivery is not configured.")
    try:
        from twilio.rest import Client

        Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN).messages.create(
            body=f"Your Campus X Mart verification code is {code}. It expires in 10 minutes.",
            from_=settings.TWILIO_FROM_PHONE,
            to=destination,
        )
    except Exception as exc:
        raise VerificationDeliveryError("SMS verification delivery failed.") from exc
