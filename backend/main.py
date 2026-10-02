"""Campus X Mart API: registration, login, and current-user authentication."""

import asyncio
import base64
import hashlib
import hmac
import secrets
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import parse_qs, urlparse

import jwt
import psycopg2
import requests
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from database import get_connection
from generate_report import generate_market_report
from graph_schema import schema
from llm_assistant import LLMAssistant
from settings import settings
from verification_delivery import VerificationDeliveryError, send_verification_code

app = FastAPI(title="Campus X Mart API", version="1.0.0")
UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/uploads/{filename:path}")
def serve_uploaded_file(filename: str):
    upload_root = Path(UPLOADS_DIR).resolve()
    candidate = (upload_root / filename).resolve()
    try:
        candidate.relative_to(upload_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="File not found.") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(candidate)


app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
PASSWORD_ITERATIONS = 600_000
VERIFICATION_EXPIRY_MINUTES = 10
RESEND_COOLDOWN_SECONDS = 60
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_FILE_TYPES = {"application/pdf", "text/plain", "application/zip"}
MAX_VERIFICATION_ATTEMPTS = 5
ACTIVE_CHAT_CONNECTIONS = defaultdict(set)


def youtube_video_id(value: str) -> Optional[str]:
    try:
        parsed = urlparse(value.strip())
        hostname = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
            return None
        if hostname in {"youtu.be", "www.youtu.be"}:
            candidate = parsed.path.strip("/").split("/", 1)[0]
        elif hostname in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"}:
            segments = [segment for segment in parsed.path.split("/") if segment]
            if parsed.path == "/watch":
                candidate = parse_qs(parsed.query).get("v", [""])[0]
            elif len(segments) >= 2 and segments[0] in {"embed", "shorts", "live"}:
                candidate = segments[1]
            else:
                return None
        else:
            return None
        if len(candidate) != 11 or not all(character.isascii() and (character.isalnum() or character in "-_") for character in candidate):
            return None
        return candidate
    except ValueError:
        return None


class RegistrationRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=20)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = value.strip().lower()
        if not username.replace("_", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, and underscores.")
        return username

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return email

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: Optional[str]) -> Optional[str]:
        if not value or not value.strip():
            return None
        compact = "".join(character for character in value.strip() if character.isdigit() or character == "+")
        if compact.startswith("01") and len(compact) == 11:
            compact = "+880" + compact[1:]
        if not compact.startswith("+") or not compact[1:].isdigit() or not 8 <= len(compact[1:]) <= 15:
            raise ValueError("Enter a phone number in international format, for example +8801712345678.")
        return compact


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=150)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class VerificationSendRequest(BaseModel):
    channel: str

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value: str) -> str:
        channel = value.strip().upper()
        if channel not in {"EMAIL", "PHONE"}:
            raise ValueError("Channel must be EMAIL or PHONE.")
        return channel


class VerificationConfirmRequest(VerificationSendRequest):
    code: str = Field(pattern=r"^\d{6}$")


class ItemCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str = Field(min_length=10, max_length=5000)
    price: float = Field(ge=0, le=99_999_999)
    category: str = Field(min_length=2, max_length=50)
    condition: str
    available_from: Optional[str] = None
    location_id: Optional[int] = Field(default=None, gt=0)
    status: str = "AVAILABLE"
    video_url: Optional[str] = None

    @field_validator("condition")
    @classmethod
    def valid_condition(cls, value: str) -> str:
        normalized = value.strip().upper().replace(" - ", "_").replace(" ", "_")
        if normalized in {"NEW", "USED_EXCELLENT", "USED_GOOD", "USED", "GOOD", "EXCELLENT", "LIKE_NEW"}:
            return normalized
        if normalized == "GOOD":
            return "USED_GOOD"
        if normalized == "EXCELLENT":
            return "USED_EXCELLENT"
        if normalized == "LIKE_NEW":
            return "USED_EXCELLENT"
        raise ValueError("Invalid item condition.")

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"DRAFT", "AVAILABLE", "RESERVED", "SOLD", "ARCHIVED"}:
            raise ValueError("Invalid listing status.")
        return value

    @field_validator("video_url")
    @classmethod
    def valid_video_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not str(value).strip():
            return None
        url = value.strip()
        if youtube_video_id(url):
            return url
        raise ValueError("Video URL must be a YouTube link.")


class ListingRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str = Field(min_length=10, max_length=5000)
    price: float = Field(ge=0, le=99_999_999)
    category: str = Field(min_length=2, max_length=50)
    item_condition: str
    available_from: Optional[str] = None
    location_id: Optional[int] = Field(default=None, gt=0)
    video_url: Optional[str] = None
    status: str = "AVAILABLE"

    @field_validator("item_condition")
    @classmethod
    def valid_condition(cls, value: str) -> str:
        value = value.strip().upper().replace(" - ", "_").replace(" ", "_")
        if value in {"NEW", "USED_EXCELLENT", "USED_GOOD", "USED", "GOOD", "EXCELLENT", "LIKE_NEW"}:
            if value == "GOOD":
                return "USED_GOOD"
            if value == "EXCELLENT":
                return "USED_EXCELLENT"
            if value == "LIKE_NEW":
                return "USED_EXCELLENT"
            return value
        if value in {"USED_GOOD", "USED_EXCELLENT", "NEW", "USED"}:
            return value
            raise ValueError("Invalid item condition.")
        return value

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"DRAFT", "AVAILABLE", "RESERVED", "SOLD", "ARCHIVED"}:
            raise ValueError("Invalid listing status.")
        return value

    @field_validator("video_url")
    @classmethod
    def valid_video_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        url = value.strip()
        if youtube_video_id(url):
            return url
        raise ValueError("Video URL must be a valid YouTube video link.")


class LocationCreateRequest(BaseModel):
    location_name: str = Field(min_length=1, max_length=100)
    campus_name: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class AssistantChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)

    @field_validator("query")
    @classmethod
    def nonblank_query(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Enter a question for the marketplace assistant.")
        return text


class ItemReactionRequest(BaseModel):
    reaction_type: Literal["LIKE", "DISLIKE"]


class ItemCommentRequest(BaseModel):
    comment_text: str = Field(min_length=1, max_length=1000)

    @field_validator("comment_text")
    @classmethod
    def nonblank_comment(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Comment text cannot be blank.")
        return text


class MessageCreateRequest(BaseModel):
    message_text: str = Field(min_length=1, max_length=2000)

    @field_validator("message_text")
    @classmethod
    def nonblank_message(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Message text cannot be blank.")
        return text


class OrderStatusRequest(BaseModel):
    status: Literal["CONFIRMED", "CANCELLED", "COMPLETED"]


class OrderMeetupDateRequest(BaseModel):
    meetup_date: Optional[date]


class ProductReportRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value: str) -> str:
        reason = value.strip()
        if len(reason) < 5:
            raise ValueError("Give a little more detail about this report.")
        return reason


class ReportStatusRequest(BaseModel):
    status: Literal["REVIEWING", "RESOLVED", "REJECTED"]


class PostingBanRequest(BaseModel):
    banned: bool
    reason: Optional[str] = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() or None if value else None


class ItemReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_text: Optional[str] = Field(default=None, max_length=1200)

    @field_validator("review_text")
    @classmethod
    def normalize_review_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        _, iterations, salt, expected = stored_hash.split("$", 3)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt), int(iterations))
        return hmac.compare_digest(actual, base64.b64decode(expected))
    except (TypeError, ValueError):
        return False


def create_token(user_id: int, username: str, admin_session: bool = False) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "username": username, "admin_session": admin_session, "exp": expires},
        settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )


def discard_verification_code(user_id: int, channel: str, code_hash: str) -> None:
    """Remove an undelivered OTP so it neither blocks resend nor can be guessed."""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM verification_codes WHERE user_id = %s AND channel = %s AND code_hash = %s AND verified_at IS NULL",
                (user_id, channel, code_hash),
            )
        connection.commit()
    finally:
        connection.close()


def serialize_user(row) -> dict:
    if isinstance(row, dict):
        result = dict(row)
        if "user_id" not in result and "id" in result:
            result["user_id"] = result["id"]
        if "id" not in result and "user_id" in result:
            result["id"] = result["user_id"]
        return result
    return {
        "user_id": row[0],
        "id": row[0],
        "username": row[1],
        "full_name": row[2],
        "email": row[3],
        "phone": row[4],
        "email_verified": row[5] if len(row) > 5 else False,
        "phone_verified": row[6] if len(row) > 6 else False,
        "role": row[7] if len(row) > 7 else "STUDENT",
    }


def serialize_listing(row) -> dict:
    return {
        "item_id": row[0], "name": row[1], "description": row[2], "price": float(row[3]),
        "category": row[4], "item_condition": row[5], "available_from": row[6], "status": row[7],
        "created_at": row[8], "updated_at": row[9], "media_url": row[10] if len(row) > 10 else None,
        "location_id": row[11] if len(row) > 11 else None,
        "video_url": row[12] if len(row) > 12 else None,
    }


def serialize_notification(row) -> dict:
    return {
        "notification_id": row[0],
        "notification_type": row[1],
        "title": row[2],
        "message": row[3],
        "target_url": row[4],
        "is_read": row[5],
        "created_at": row[6].isoformat() if row[6] is not None else None,
    }


def serialize_message(row) -> dict:
    return {
        "message_id": row[0],
        "sender_id": row[1],
        "receiver_id": row[2],
        "message_text": row[3],
        "is_read": row[4],
        "sent_at": row[5].isoformat() if row[5] is not None else None,
    }


async def broadcast_chat_message(message_payload: dict):
    for user_id in {message_payload["sender_id"], message_payload["receiver_id"]}:
        for websocket in list(ACTIVE_CHAT_CONNECTIONS.get(user_id, set())):
            try:
                await websocket.send_json({"type": "message", "message": message_payload})
            except Exception:
                ACTIVE_CHAT_CONNECTIONS.get(user_id, set()).discard(websocket)


def insert_notification(cursor, user_id: int, notification_type: str, title: str, message: str, target_url: str):
    cursor.execute(
        """INSERT INTO notifications (user_id, notification_type, title, message, target_url)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING notification_id, notification_type, title, message, target_url, is_read, created_at""",
        (user_id, notification_type, title, message[:2000], target_url),
    )
    return serialize_notification(cursor.fetchone())


def notify_admins(cursor, notification_type: str, title: str, message: str, target_url: str):
    cursor.execute("SELECT user_id FROM users WHERE role = 'ADMIN'")
    for (admin_id,) in cursor.fetchall():
        insert_notification(cursor, admin_id, notification_type, title, message, target_url)


def consume_ws_ticket(ticket: str) -> Optional[int]:
    ticket_hash = hashlib.sha256(ticket.encode()).hexdigest()
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """DELETE FROM websocket_tickets
                   WHERE ticket_hash = %s AND expires_at > CURRENT_TIMESTAMP
                   RETURNING user_id""",
                (ticket_hash,),
            )
            row = cursor.fetchone()
        connection.commit()
    finally:
        connection.close()
    return row[0] if row else None


def get_unread_notifications(user_id: int):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT notification_id, notification_type, title, message, target_url, is_read, created_at
                   FROM notifications WHERE user_id = %s AND is_read = FALSE
                   ORDER BY notification_id""",
                (user_id,),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()
    return [serialize_notification(row) for row in rows]


def get_notification_max_id(user_id: int) -> int:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(notification_id), 0) FROM notifications WHERE user_id = %s", (user_id,))
            return cursor.fetchone()[0]
    finally:
        connection.close()


def get_notifications_after(user_id: int, notification_id: int):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT notification_id, notification_type, title, message, target_url, is_read, created_at
                   FROM notifications WHERE user_id = %s AND notification_id > %s
                   ORDER BY notification_id""",
                (user_id, notification_id),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()
    return [serialize_notification(row) for row in rows]


def _normalize_condition(value: str) -> str:
    return value.strip().upper().replace(" - ", "_").replace(" ", "_")


def _valid_image_signature(content: bytes) -> bool:
    return (
        content.startswith(b"\xFF\xD8\xFF")
        or content.startswith(b"\x89PNG\r\n\x1A\n")
        or (content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP")
    )


def current_user_from_token(token: str) -> dict:
    try:
        claims = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="The authentication token is invalid or has expired.") from exc
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT user_id, username, full_name, email, phone, email_verified, phone_verified, role FROM users WHERE user_id = %s",
                (int(claims["sub"]),),
            )
            row = cursor.fetchone()
    finally:
        connection.close()
    if not row:
        raise HTTPException(status_code=401, detail="User not found.")
    user = serialize_user(row)
    user["admin_session"] = claims.get("admin_session") is True
    return user


def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    return current_user_from_token(auth_header.split(" ", 1)[1])


def current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        claims = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="The authentication token is invalid or has expired.")
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT user_id, username, full_name, email, phone, email_verified, phone_verified FROM users WHERE user_id = %s", (claims["sub"],))
            row = cursor.fetchone()
    finally:
        connection.close()
    if not row:
        raise HTTPException(status_code=401, detail="User not found.")
    return serialize_user(row)


def require_admin(current_user: dict = Depends(get_current_user)):
    if str(current_user.get("role", "STUDENT")).upper() != "ADMIN" or not current_user.get("admin_session"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


def require_posting_allowed(cursor, user_id: int) -> None:
    cursor.execute("SELECT posting_banned FROM users WHERE user_id = %s FOR UPDATE", (user_id,))
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="User not found.")
    if row[0]:
        raise HTTPException(status_code=403, detail="Your account is restricted from posting marketplace content.")


def require_verified_contact(user: dict) -> None:
    if not (user.get("email_verified") or user.get("phone_verified")):
        raise HTTPException(
            status_code=403,
            detail="Verify your email or phone number in Account & verification before posting or purchasing.",
        )


def register_user(request: Request, payload: RegistrationRequest):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """INSERT INTO users (username, full_name, email, phone, password_hash)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING user_id, username, full_name, email, phone, email_verified, phone_verified""",
                (payload.username, payload.full_name.strip(), payload.email, payload.phone, hash_password(payload.password)),
            )
            user = cursor.fetchone()
        finally:
            cursor.close()
        connection.commit()
    except psycopg2.IntegrityError:
        connection.rollback()
        raise HTTPException(status_code=409, detail="The email, phone number, or username is already in use.")
    finally:
        connection.close()
    return {"user": serialize_user(user), "access_token": create_token(user[0], user[1]), "token_type": "bearer"}


def create_verification_code_for_user(user_id: int, channel: str, destination: str) -> str:
    code = f"{secrets.randbelow(1_000_000):06d}"
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO verification_codes (user_id, channel, destination, code_hash, expires_at) VALUES (%s, %s, %s, %s, %s)",
                (user_id, channel.upper(), destination, hash_password(code), datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_EXPIRY_MINUTES)),
            )
        connection.commit()
    finally:
        connection.close()
    return code


def send_verification(request: Request, payload: VerificationSendRequest, user: Optional[dict] = None, current_user: Optional[dict] = None):
    if user is None:
        user = current_user
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")

    user_id = user.get("user_id") if isinstance(user, dict) else None
    if user_id is None:
        user_id = user.get("id") if isinstance(user, dict) else None
    if user_id is not None and "id" not in user:
        user = {**user, "id": user_id}

    if isinstance(user, dict) and ("email" not in user or "phone" not in user):
        connection = get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT email, phone FROM users WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
            finally:
                cursor.close()
        finally:
            connection.close()
        if row:
            user = {**user, "email": row[0], "phone": row[1]}

    destination = user.get("email") if payload.channel == "EMAIL" else user.get("phone")
    if not destination:
        raise HTTPException(status_code=400, detail="Add a phone number before requesting phone verification.")
    if (payload.channel == "EMAIL" and user.get("email_verified")) or (payload.channel == "PHONE" and user.get("phone_verified")):
        return {"message": f"Your {payload.channel.lower()} is already verified."}

    connection = get_connection()
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """SELECT created_at FROM verification_codes
                   WHERE user_id = %s AND channel = %s AND verified_at IS NULL
                   ORDER BY created_at DESC LIMIT 1""",
                (user["id"], payload.channel),
            )
            previous = cursor.fetchone()
            if previous and (datetime.now(timezone.utc) - previous[0]).total_seconds() < RESEND_COOLDOWN_SECONDS:
                raise HTTPException(status_code=429, detail="Please wait 60 seconds before requesting another code.")
            code = f"{secrets.randbelow(1_000_000):06d}"
            code_hash = hash_password(code)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_EXPIRY_MINUTES)
            cursor.execute(
                "UPDATE verification_codes SET verified_at = CURRENT_TIMESTAMP WHERE user_id = %s AND channel = %s AND verified_at IS NULL",
                (user["id"], payload.channel),
            )
            cursor.execute(
                """INSERT INTO verification_codes (user_id, channel, destination, code_hash, expires_at)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user["id"], payload.channel, destination, code_hash, expires_at),
            )
        finally:
            cursor.close()
        connection.commit()
    finally:
        connection.close()

    try:
        send_verification_code(payload.channel, destination, code)
    except VerificationDeliveryError as error:
        if settings.APP_ENV != "dev":
            discard_verification_code(user["id"], payload.channel, code_hash)
            raise HTTPException(status_code=503, detail="The verification code could not be delivered. Check your delivery settings and try again.") from error
    if settings.APP_ENV == "dev":
        if settings.EXPOSE_DEV_OTP:
            return {"message": "Development code generated. It expires in 10 minutes.", "dev_code": code, "expires_in_seconds": VERIFICATION_EXPIRY_MINUTES * 60, "resend_after_seconds": RESEND_COOLDOWN_SECONDS}
        return {"message": "Development mode does not send real codes. Set EXPOSE_DEV_OTP=true in backend/.env to show the development code.", "expires_in_seconds": VERIFICATION_EXPIRY_MINUTES * 60, "resend_after_seconds": RESEND_COOLDOWN_SECONDS}
    return {"message": f"A verification code was sent to your {payload.channel.lower()}.", "expires_in_seconds": VERIFICATION_EXPIRY_MINUTES * 60, "resend_after_seconds": RESEND_COOLDOWN_SECONDS}


def verify_destination(payload: VerificationConfirmRequest, user: dict):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """SELECT verification_id, code_hash, expires_at, attempt_count
                   FROM verification_codes
                   WHERE user_id = %s AND channel = %s AND verified_at IS NULL
                   ORDER BY created_at DESC LIMIT 1 FOR UPDATE""",
                (user["id"], payload.channel),
            )
            record = cursor.fetchone()
            if not record or record[2] < datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="The verification code is missing or has expired.")
            if record[3] >= MAX_VERIFICATION_ATTEMPTS:
                raise HTTPException(status_code=429, detail="Too many failed attempts. Request a new code.")
            if not verify_password(payload.code, record[1]):
                new_attempt_count = record[3] + 1
                cursor.execute("UPDATE verification_codes SET attempt_count = %s WHERE verification_id = %s", (new_attempt_count, record[0]))
                connection.commit()
                if new_attempt_count >= MAX_VERIFICATION_ATTEMPTS:
                    raise HTTPException(status_code=429, detail="Too many failed attempts. Request a new code.")
                raise HTTPException(status_code=400, detail="Incorrect verification code.")
            verified_field = "email_verified" if payload.channel == "EMAIL" else "phone_verified"
            cursor.execute("UPDATE verification_codes SET verified_at = CURRENT_TIMESTAMP WHERE verification_id = %s", (record[0],))
            cursor.execute(f"UPDATE users SET {verified_field} = TRUE, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s", (user["id"],))
        finally:
            cursor.close()
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {"message": f"Your {payload.channel.lower()} has been verified."}


@app.get("/")
def health_check():
    return {"message": "Campus X Mart API is running"}


@app.post("/api/locations")
def create_location(payload: LocationCreateRequest, user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO locations (location_name, campus_name, address, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING location_id, location_name, campus_name, address, latitude, longitude, created_at
                """,
                (
                    payload.location_name.strip(),
                    payload.campus_name.strip() if payload.campus_name else None,
                    payload.address.strip() if payload.address else None,
                    payload.latitude,
                    payload.longitude,
                ),
            )
            row = cursor.fetchone()
        connection.commit()
    finally:
        connection.close()
    return {"location": {"location_id": row[0], "location_name": row[1], "campus_name": row[2], "address": row[3], "latitude": row[4], "longitude": row[5], "created_at": row[6]}}


@app.get("/api/locations")
def list_locations(user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT location_id, location_name, campus_name, address, latitude, longitude
                   FROM locations ORDER BY campus_name NULLS LAST, location_name, location_id"""
            )
            rows = cursor.fetchall()
    finally:
        connection.close()
    return {
        "locations": [
            {
                "location_id": row[0],
                "location_name": row[1],
                "campus_name": row[2],
                "address": row[3],
                "latitude": float(row[4]) if row[4] is not None else None,
                "longitude": float(row[5]) if row[5] is not None else None,
            }
            for row in rows
        ]
    }


@app.post("/api/assistant/chat")
@limiter.limit("5/minute")
def assistant_chat(request: Request, payload: AssistantChatRequest, user: dict = Depends(get_current_user)):
    try:
        return LLMAssistant().ask(payload.query)
    except (requests.RequestException, RuntimeError) as error:
        raise HTTPException(status_code=502, detail="The marketplace assistant is temporarily unavailable. Please try again.") from error


@app.post("/api/upload/image")
@limiter.limit("5/minute")
async def upload_image(request: Request, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The selected file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Files must be 5 MB or smaller.")
    if not _valid_image_signature(content):
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid image.")

    content_type = (file.content_type or "application/octet-stream").lower()
    if content_type not in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, and WEBP images are supported.")

    if settings.APP_ENV != "prod":
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{secrets.token_hex(8)}_{file.filename or 'upload'}"
        safe_path = UPLOADS_DIR / filename
        safe_path.write_bytes(content)
        return {"storage": "local", "secure_url": f"http://localhost:8000/uploads/{filename}"}

    if not settings.CLOUDINARY_CLOUD_NAME or not settings.CLOUDINARY_API_KEY or not settings.CLOUDINARY_API_SECRET:
        raise HTTPException(status_code=503, detail="Cloud storage is not configured. Add Cloudinary credentials to backend/.env.")

    timestamp = int(datetime.now(timezone.utc).timestamp())
    data = {
        "api_key": settings.CLOUDINARY_API_KEY,
        "timestamp": timestamp,
        "signature": hashlib.sha1(f"timestamp={timestamp}{settings.CLOUDINARY_API_SECRET}".encode()).hexdigest(),
    }
    response = requests.post(
        f"https://api.cloudinary.com/v1_1/{settings.CLOUDINARY_CLOUD_NAME}/image/upload",
        data=data,
        files={"file": (file.filename or "upload", content, content_type)},
        timeout=30,
    )
    if not response.ok:
        raise HTTPException(status_code=502, detail="Cloud upload failed. Please try again.")
    payload = response.json()
    return {"storage": "cloudinary", "secure_url": payload.get("secure_url", "")}


@app.post("/api/ws/ticket")
def create_ws_ticket(user: dict = Depends(get_current_user)):
    ticket = secrets.token_urlsafe(32)
    ticket_hash = hashlib.sha256(ticket.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO websocket_tickets (ticket_hash, user_id, expires_at) VALUES (%s, %s, %s)",
                (ticket_hash, user["id"], expires_at),
            )
        connection.commit()
    finally:
        connection.close()
    return {"ticket": ticket}


@app.websocket("/api/ws/chat")
async def websocket_chat(websocket: WebSocket):
    ticket = websocket.query_params.get("ticket")
    if ticket is None:
        await websocket.close(code=1008)
        return

    user_id = await run_in_threadpool(consume_ws_ticket, ticket)
    if user_id is None:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    ACTIVE_CHAT_CONNECTIONS[user_id].add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return
    finally:
        ACTIVE_CHAT_CONNECTIONS.get(user_id, set()).discard(websocket)
        if not ACTIVE_CHAT_CONNECTIONS.get(user_id):
            ACTIVE_CHAT_CONNECTIONS.pop(user_id, None)


@app.websocket("/api/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    ticket = websocket.query_params.get("ticket")
    if ticket is None:
        await websocket.close(code=1008)
        return
    user_id = await run_in_threadpool(consume_ws_ticket, ticket)
    if user_id is None:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        last_notification_id = await run_in_threadpool(get_notification_max_id, user_id)
        unread = await run_in_threadpool(get_unread_notifications, user_id)
        for notification in unread:
            if notification["notification_id"] <= last_notification_id:
                await websocket.send_json({"type": "notification", "notification": notification})

        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1)
            except asyncio.TimeoutError:
                pass
            notifications = await run_in_threadpool(get_notifications_after, user_id, last_notification_id)
            for notification in notifications:
                await websocket.send_json({"type": "notification", "notification": notification})
                last_notification_id = notification["notification_id"]
    except WebSocketDisconnect:
        return


@app.get("/api/auth/check-username")
def check_username(username: str = ""):
    normalized = username.strip().lower()
    if len(normalized) < 3 or not normalized.replace("_", "").isalnum():
        return {"available": False, "message": "Username must contain at least 3 characters."}
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM users WHERE username = %s", (normalized,))
            available = cursor.fetchone() is None
    finally:
        connection.close()
    return {"available": available, "message": "Username is available." if available else "This username is already taken."}


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register_route(request: Request, payload: RegistrationRequest):
    return register_user(request, payload)


@app.post("/api/auth/login")
@limiter.limit("5/minute")
def login_route(request: Request, payload: LoginRequest):
    return authenticate_login(payload)


@app.post("/api/admin/login")
@limiter.limit("5/minute")
def admin_login_route(request: Request, payload: LoginRequest):
    return authenticate_login(payload, admin_session=True)


def authenticate_login(payload: LoginRequest, admin_session: bool = False):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT user_id, username, full_name, email, phone, email_verified, phone_verified, role, password_hash FROM users WHERE email = %s", (payload.email,))
            row = cursor.fetchone()
    finally:
        connection.close()
    if not row or not verify_password(payload.password, row[8]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if admin_session and row[7] != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required.")
    user = serialize_user(row)
    user["admin_session"] = admin_session
    return {
        "user": user,
        "access_token": create_token(row[0], row[1], admin_session=admin_session),
        "token_type": "bearer",
    }


@app.post("/api/auth/send-verification", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/minute")
def send_verification_route(request: Request, payload: VerificationSendRequest):
    user = get_current_user(request)
    return send_verification(request, payload, user)


@app.post("/api/auth/verify")
@limiter.limit("5/minute")
def verify_route(request: Request, payload: VerificationConfirmRequest):
    user = get_current_user(request)
    return verify_destination(payload, user)


@app.get("/api/listings/mine")
def my_listings(user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                     """SELECT i.item_id, i.name, i.description, i.price, i.category, i.item_condition, i.available_from, i.status, i.created_at, i.updated_at,
                         (SELECT media_url FROM item_media WHERE item_id = i.item_id AND media_type = 'IMAGE' ORDER BY sort_order, media_id LIMIT 1) AS media_url,
                         i.location_id, i.video_url
                   FROM items i WHERE i.seller_id = %s ORDER BY i.created_at DESC""",
                (user["id"],),
            )
            listings = [serialize_listing(row) for row in cursor.fetchall()]
    finally:
        connection.close()
    return {"items": listings}


@app.post("/api/listings", status_code=status.HTTP_201_CREATED)
def create_listing(payload: ListingRequest, user: dict = Depends(get_current_user)):
    require_verified_contact(user)
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            if payload.location_id is not None:
                cursor.execute("SELECT 1 FROM locations WHERE location_id = %s", (payload.location_id,))
                if cursor.fetchone() is None:
                    raise HTTPException(status_code=404, detail="Selected location not found.")
            cursor.execute(
                """INSERT INTO items (seller_id, name, description, price, category, item_condition, available_from, status, location_id, video_url)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING item_id, name, description, price, category, item_condition, available_from, status, created_at, updated_at""",
                (user["id"], payload.name.strip(), payload.description.strip(), payload.price, payload.category.strip(), payload.item_condition, payload.available_from or None, payload.status, payload.location_id, payload.video_url),
            )
            listing = serialize_listing(cursor.fetchone())
            listing["location_id"] = payload.location_id
            listing["video_url"] = payload.video_url
        connection.commit()
    finally:
        connection.close()
    return {"item": listing}


@app.post("/api/listings/{item_id}/media", status_code=status.HTTP_201_CREATED)
async def upload_listing_media(item_id: int, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    require_verified_contact(user)
    content_type = file.content_type or "application/octet-stream"
    is_image = content_type.startswith("image/")
    if not is_image and content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=415, detail="Only images, PDF, text, and ZIP files are supported.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The selected file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Files must be 5 MB or smaller.")

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            require_posting_allowed(cursor, user["id"])
            cursor.execute("SELECT 1 FROM items WHERE item_id = %s AND seller_id = %s", (item_id, user["id"]))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Listing not found or you do not have permission to upload media.")
    finally:
        connection.close()

    if not settings.CLOUDINARY_CLOUD_NAME or (not settings.CLOUDINARY_API_SECRET and not settings.CLOUDINARY_UPLOAD_PRESET):
        raise HTTPException(status_code=503, detail="Cloud storage is not configured. Add Cloudinary credentials to backend/.env.")
    try:
        import cloudinary
        import cloudinary.uploader

        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        options = {"resource_type": "image" if is_image else "raw", "folder": f"campus-x-mart/listings/{item_id}"}
        if settings.CLOUDINARY_UPLOAD_PRESET:
            options["upload_preset"] = settings.CLOUDINARY_UPLOAD_PRESET
        uploaded = cloudinary.uploader.upload(content, **options)
    except Exception as error:
        raise HTTPException(status_code=502, detail="Cloud upload failed. Please try again.") from error

    media_type = "IMAGE" if is_image else "FILE"
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM item_media WHERE item_id = %s", (item_id,))
            sort_order = cursor.fetchone()[0]
            cursor.execute(
                """INSERT INTO item_media (item_id, media_type, storage_provider, media_url, public_id, original_filename, sort_order)
                   VALUES (%s, %s, 'CLOUDINARY', %s, %s, %s, %s)
                   RETURNING media_id, media_url, media_type, original_filename""",
                (item_id, media_type, uploaded["secure_url"], uploaded.get("public_id"), file.filename, sort_order),
            )
            media = cursor.fetchone()
        connection.commit()
    finally:
        connection.close()
    return {"media": {"media_id": media[0], "media_url": media[1], "media_type": media[2], "filename": media[3]}}


@app.put("/api/listings/{item_id}")
def update_listing(item_id: int, payload: ListingRequest, user: dict = Depends(get_current_user)):
    require_verified_contact(user)
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            require_posting_allowed(cursor, user["id"])
            if payload.location_id is not None:
                cursor.execute("SELECT 1 FROM locations WHERE location_id = %s", (payload.location_id,))
                if cursor.fetchone() is None:
                    raise HTTPException(status_code=404, detail="Selected location not found.")
            cursor.execute(
                """UPDATE items SET name = %s, description = %s, price = %s, category = %s, item_condition = %s,
                   available_from = %s, status = %s, location_id = %s, video_url = %s, updated_at = CURRENT_TIMESTAMP
                   WHERE item_id = %s AND seller_id = %s
                   RETURNING item_id, name, description, price, category, item_condition, available_from, status, created_at, updated_at""",
                (payload.name.strip(), payload.description.strip(), payload.price, payload.category.strip(), payload.item_condition, payload.available_from or None, payload.status, payload.location_id, payload.video_url, item_id, user["id"]),
            )
            row = cursor.fetchone()
            updated_listing = serialize_listing(row) if row else None
            if updated_listing is not None:
                updated_listing["location_id"] = payload.location_id
                updated_listing["video_url"] = payload.video_url
        connection.commit()
    finally:
        connection.close()
    if not row:
        raise HTTPException(status_code=404, detail="Listing not found or you do not have permission to edit it.")
    return {"item": updated_listing}


@app.delete("/api/listings/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(item_id: int, user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM items WHERE item_id = %s AND seller_id = %s RETURNING item_id", (item_id, user["id"]))
            deleted = cursor.fetchone()
        connection.commit()
    finally:
        connection.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Listing not found or you do not have permission to delete it.")


@app.get("/api/auth/me")
def me_route(request: Request):
    user = get_current_user(request)
    return {"user_id": user.get("user_id", user.get("id")), **user}


@app.post("/api/items", status_code=status.HTTP_201_CREATED)
def create_item_route(payload: ItemCreateRequest, user: dict = Depends(get_current_user)):
    require_verified_contact(user)
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            require_posting_allowed(cursor, user["id"])
            if payload.location_id is not None:
                cursor.execute("SELECT 1 FROM locations WHERE location_id = %s", (payload.location_id,))
                if cursor.fetchone() is None:
                    raise HTTPException(status_code=404, detail="Selected location not found.")
            cursor.execute(
                """
                INSERT INTO items (seller_id, name, description, price, category, item_condition, available_from, status, video_url, location_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING item_id, name, description, price, category, item_condition, available_from, status, created_at, updated_at, video_url, location_id
                """,
                (
                    user["id"],
                    payload.name.strip(),
                    payload.description.strip(),
                    payload.price,
                    payload.category.strip(),
                    _normalize_condition(payload.condition),
                    payload.available_from,
                    payload.status.upper(),
                    payload.video_url,
                    payload.location_id,
                ),
            )
            row = cursor.fetchone()
        connection.commit()
    finally:
        connection.close()
    return {"item": {"item_id": row[0], "name": row[1], "description": row[2], "price": float(row[3]), "category": row[4], "item_condition": row[5], "available_from": row[6], "status": row[7], "created_at": row[8], "updated_at": row[9], "video_url": row[10], "location_id": row[11]}}


@app.get("/api/items")
def list_products(
    q: str = Query(default="", max_length=100),
    category: Optional[str] = Query(default=None, max_length=50),
    condition: Optional[Literal["NEW", "USED_EXCELLENT", "USED_GOOD", "USED"]] = None,
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    sort: str = Query(default="newest"),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=422, detail="Minimum price must not exceed maximum price.")

    normalized_sort = sort.strip().lower().replace("-", "_")
    allowed_sorts = {"newest", "price_asc", "price_desc", "name_asc"}
    if normalized_sort not in allowed_sorts:
        raise HTTPException(status_code=422, detail="Invalid sort option.")

    filters = ["i.status = 'AVAILABLE'"]
    filter_params = []
    if q.strip():
        filters.append("POSITION(LOWER(%s) IN LOWER(i.name || ' ' || i.description || ' ' || i.category)) > 0")
        filter_params.append(q.strip())
    if category:
        filters.append("i.category = %s")
        filter_params.append(category)
    if condition:
        filters.append("i.item_condition = %s")
        filter_params.append(condition)
    if min_price is not None:
        filters.append("i.price >= %s")
        filter_params.append(min_price)
    if max_price is not None:
        filters.append("i.price <= %s")
        filter_params.append(max_price)

    ordering = {
        "newest": "i.created_at DESC, i.item_id DESC",
        "price_asc": "i.price ASC, i.item_id ASC",
        "price_desc": "i.price DESC, i.item_id DESC",
        "name_asc": "LOWER(i.name) ASC, i.item_id ASC",
    }[normalized_sort]
    where_clause = " AND ".join(filters)
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM items i WHERE {where_clause}", filter_params)
            total_count = cursor.fetchone()[0]
            cursor.execute(
                f"""SELECT i.item_id, i.name, i.description, i.price, i.category, i.item_condition,
                          i.available_from, i.status, i.created_at, i.updated_at,
                          u.user_id, u.username, u.full_name, media.media_url,
                          (SELECT COUNT(*) FROM item_reactions r WHERE r.item_id = i.item_id AND r.reaction_type = 'LIKE'),
                          (SELECT COUNT(*) FROM item_comments c WHERE c.item_id = i.item_id),
                          (SELECT r.reaction_type FROM item_reactions r WHERE r.item_id = i.item_id AND r.user_id = %s),
                          (SELECT o.status FROM orders o WHERE o.item_id = i.item_id AND o.buyer_id = %s ORDER BY o.ordered_at DESC, o.order_id DESC LIMIT 1),
                          (SELECT ROUND(AVG(r.rating)::numeric, 1) FROM reviews r WHERE r.item_id = i.item_id),
                          (SELECT COUNT(*) FROM reviews r WHERE r.item_id = i.item_id),
                          (SELECT ROUND(AVG(r.rating)::numeric, 1)
                           FROM reviews r JOIN items reviewed_item ON reviewed_item.item_id = r.item_id
                              WHERE reviewed_item.seller_id = i.seller_id),
                              i.location_id, l.location_name, l.campus_name, l.address, l.latitude, l.longitude,
                              i.video_url,
                              (SELECT COUNT(*) FROM item_reactions r WHERE r.item_id = i.item_id AND r.reaction_type = 'DISLIKE')
                   FROM items i
                   JOIN users u ON u.user_id = i.seller_id
                         LEFT JOIN locations l ON l.location_id = i.location_id
                   LEFT JOIN LATERAL (
                       SELECT media_url FROM item_media
                       WHERE item_id = i.item_id AND media_type = 'IMAGE'
                       ORDER BY sort_order, media_id LIMIT 1
                   ) media ON TRUE
                         WHERE {where_clause}
                         ORDER BY {ordering}
                   LIMIT %s OFFSET %s""",
                     (user["id"], user["id"], *filter_params, limit, offset),
            )
            rows = cursor.fetchall()
            cursor.execute("SELECT DISTINCT category FROM items WHERE status = 'AVAILABLE' ORDER BY category")
            categories = [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()

    return {
        "items": [
            {
                "item_id": row[0],
                "name": row[1],
                "description": row[2],
                "price": float(row[3]),
                "category": row[4],
                "item_condition": row[5],
                "available_from": row[6],
                "status": row[7],
                "created_at": row[8],
                "updated_at": row[9],
                "seller": {"user_id": row[10], "username": row[11], "full_name": row[12]},
                "media_url": row[13],
                "like_count": row[14],
                "comment_count": row[15],
                "current_reaction": row[16],
                "my_order_status": row[17],
                "average_rating": float(row[18]) if row[18] is not None else None,
                "review_count": row[19],
                "seller_rating": float(row[20]) if row[20] is not None else None,
                "location": {
                    "location_id": row[21],
                    "location_name": row[22],
                    "campus_name": row[23],
                    "address": row[24],
                    "latitude": float(row[25]) if row[25] is not None else None,
                    "longitude": float(row[26]) if row[26] is not None else None,
                } if row[21] is not None else None,
                "video_url": row[27],
                "dislike_count": row[28],
            }
            for row in rows
        ],
        "categories": categories,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
    }


def require_item_exists(cursor, item_id: int) -> int:
    cursor.execute("SELECT seller_id FROM items WHERE item_id = %s", (item_id,))
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return row[0]


def item_reaction_summary(cursor, item_id: int, user_id: int) -> dict:
    cursor.execute(
        """SELECT COUNT(*) FILTER (WHERE reaction_type = 'LIKE'),
                  COUNT(*) FILTER (WHERE reaction_type = 'DISLIKE'),
                  MAX(reaction_type) FILTER (WHERE user_id = %s)
           FROM item_reactions WHERE item_id = %s""",
        (user_id, item_id),
    )
    likes, dislikes, current_reaction = cursor.fetchone()
    return {"like_count": likes, "dislike_count": dislikes, "current_reaction": current_reaction}


def review_summary(cursor, item_id: int, seller_id: int) -> dict:
    cursor.execute(
        "SELECT ROUND(AVG(rating)::numeric, 1), COUNT(*) FROM reviews WHERE item_id = %s",
        (item_id,),
    )
    average_rating, review_count = cursor.fetchone()
    cursor.execute(
        """SELECT ROUND(AVG(r.rating)::numeric, 1)
           FROM reviews r JOIN items reviewed_item ON reviewed_item.item_id = r.item_id
           WHERE reviewed_item.seller_id = %s""",
        (seller_id,),
    )
    seller_rating = cursor.fetchone()[0]
    return {
        "average_rating": float(average_rating) if average_rating is not None else None,
        "review_count": review_count,
        "seller_rating": float(seller_rating) if seller_rating is not None else None,
    }


@app.get("/api/items/{item_id}/reviews")
def list_item_reviews(item_id: int, user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            seller_id = require_item_exists(cursor, item_id)
            cursor.execute(
                """SELECT r.review_id, r.user_id, r.rating, r.review_text, r.created_at, r.updated_at,
                          u.username, u.full_name
                   FROM reviews r JOIN users u ON u.user_id = r.user_id
                   WHERE r.item_id = %s ORDER BY r.created_at DESC, r.review_id DESC LIMIT 100""",
                (item_id,),
            )
            rows = cursor.fetchall()
            summary = review_summary(cursor, item_id, seller_id)
    finally:
        connection.close()
    reviews = [
        {
            "review_id": row[0],
            "rating": row[2],
            "review_text": row[3],
            "created_at": row[4],
            "updated_at": row[5],
            "author": {"user_id": row[1], "username": row[6], "full_name": row[7]},
        }
        for row in rows
    ]
    current_review = next(
        ({"rating": row[2], "review_text": row[3]} for row in rows if row[1] == user["id"]),
        None,
    )
    return {**summary, "reviews": reviews, "my_review": current_review}


@app.put("/api/items/{item_id}/reviews")
def upsert_item_review(item_id: int, payload: ItemReviewRequest, user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            require_posting_allowed(cursor, user["id"])
            seller_id = require_item_exists(cursor, item_id)
            if seller_id == user["id"]:
                raise HTTPException(status_code=403, detail="You cannot review your own product.")
            cursor.execute(
                "SELECT 1 FROM orders WHERE item_id = %s AND buyer_id = %s AND status = 'COMPLETED' LIMIT 1",
                (item_id, user["id"]),
            )
            if cursor.fetchone() is None:
                raise HTTPException(status_code=403, detail="Only buyers with a completed order can review this product.")
            cursor.execute("SELECT 1 FROM reviews WHERE item_id = %s AND user_id = %s", (item_id, user["id"]))
            is_update = cursor.fetchone() is not None
            cursor.execute(
                """INSERT INTO reviews (item_id, user_id, rating, review_text)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (item_id, user_id)
                   DO UPDATE SET rating = EXCLUDED.rating, review_text = EXCLUDED.review_text,
                                 updated_at = CURRENT_TIMESTAMP
                   RETURNING review_id, rating, review_text, created_at, updated_at""",
                (item_id, user["id"], payload.rating, payload.review_text),
            )
            row = cursor.fetchone()
            summary = review_summary(cursor, item_id, seller_id)
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {
        "review": {
            "review_id": row[0],
            "rating": row[1],
            "review_text": row[2],
            "created_at": row[3],
            "updated_at": row[4],
            "author": {"user_id": user["id"], "username": user["username"], "full_name": user["full_name"]},
        },
        **summary,
        "created": not is_update,
    }


@app.put("/api/items/{item_id}/reaction")
def set_item_reaction(item_id: int, payload: ItemReactionRequest, user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            seller_id = require_item_exists(cursor, item_id)
            if seller_id == user["id"]:
                raise HTTPException(status_code=403, detail="You cannot react to your own product.")
            cursor.execute(
                """INSERT INTO item_reactions (item_id, user_id, reaction_type)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (item_id, user_id)
                   DO UPDATE SET reaction_type = EXCLUDED.reaction_type, created_at = CURRENT_TIMESTAMP""",
                (item_id, user["id"], payload.reaction_type),
            )
            summary = item_reaction_summary(cursor, item_id, user["id"])
        connection.commit()
    finally:
        connection.close()
    return summary


@app.delete("/api/items/{item_id}/reaction")
def remove_item_reaction(item_id: int, user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            require_item_exists(cursor, item_id)
            cursor.execute("DELETE FROM item_reactions WHERE item_id = %s AND user_id = %s", (item_id, user["id"]))
            summary = item_reaction_summary(cursor, item_id, user["id"])
        connection.commit()
    finally:
        connection.close()
    return summary


@app.get("/api/items/{item_id}/comments")
def list_item_comments(item_id: int, user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            require_item_exists(cursor, item_id)
            cursor.execute(
                """SELECT c.comment_id, c.comment_text, c.created_at, u.user_id, u.username, u.full_name
                   FROM item_comments c JOIN users u ON u.user_id = c.author_id
                   WHERE c.item_id = %s ORDER BY c.created_at, c.comment_id LIMIT 100""",
                (item_id,),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()
    return {
        "comments": [
            {
                "comment_id": row[0],
                "comment_text": row[1],
                "created_at": row[2],
                "author": {"user_id": row[3], "username": row[4], "full_name": row[5]},
            }
            for row in rows
        ]
    }


@app.post("/api/items/{item_id}/comments", status_code=status.HTTP_201_CREATED)
def create_item_comment(item_id: int, payload: ItemCommentRequest, user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            require_posting_allowed(cursor, user["id"])
            cursor.execute("SELECT seller_id, name FROM items WHERE item_id = %s", (item_id,))
            item = cursor.fetchone()
            if item is None:
                raise HTTPException(status_code=404, detail="Product not found.")
            cursor.execute(
                """INSERT INTO item_comments (item_id, author_id, comment_text)
                   VALUES (%s, %s, %s) RETURNING comment_id, comment_text, created_at""",
                (item_id, user["id"], payload.comment_text),
            )
            row = cursor.fetchone()
            if item[0] != user["id"]:
                insert_notification(cursor, item[0], "COMMENT", "New product comment", f"{user['full_name']} commented on {item[1]}.", "/products")
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {
        "comment": {
            "comment_id": row[0],
            "comment_text": row[1],
            "created_at": row[2],
            "author": {"user_id": user["id"], "username": user["username"], "full_name": user["full_name"]},
        }
    }


def require_message_recipient(cursor, current_user_id: int, recipient_id: int) -> None:
    if current_user_id == recipient_id:
        raise HTTPException(status_code=400, detail="You cannot message yourself.")
    cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (recipient_id,))
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Conversation user not found.")


@app.get("/api/users/search")
def search_users(q: str = Query(min_length=2, max_length=50), user: dict = Depends(get_current_user)):
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Search must contain at least 2 characters.")
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT user_id, username, full_name FROM users
                   WHERE user_id <> %s
                     AND (POSITION(LOWER(%s) IN LOWER(username)) > 0
                          OR POSITION(LOWER(%s) IN LOWER(full_name)) > 0)
                   ORDER BY username, user_id LIMIT 20""",
                (user["id"], query, query),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()
    return {
        "users": [
            {"user_id": row[0], "username": row[1], "full_name": row[2]}
            for row in rows
        ]
    }


@app.get("/api/messages/conversations")
def list_conversations(user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """WITH participant_messages AS (
                       SELECT CASE WHEN sender_id = %s THEN receiver_id ELSE sender_id END AS peer_id,
                              sender_id, message_id, message_text, sent_at
                       FROM messages WHERE sender_id = %s OR receiver_id = %s
                   ), latest AS (
                       SELECT DISTINCT ON (peer_id) peer_id, sender_id, message_text, sent_at
                       FROM participant_messages ORDER BY peer_id, sent_at DESC, message_id DESC
                   )
                   SELECT latest.peer_id, u.username, u.full_name, latest.message_text, latest.sent_at,
                          (SELECT COUNT(*) FROM messages unread
                           WHERE unread.sender_id = latest.peer_id AND unread.receiver_id = %s AND unread.is_read = FALSE)
                   FROM latest JOIN users u ON u.user_id = latest.peer_id
                   ORDER BY latest.sent_at DESC""",
                (user["id"], user["id"], user["id"], user["id"]),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()
    return {
        "conversations": [
            {
                "user_id": row[0],
                "username": row[1],
                "full_name": row[2],
                "last_message": row[3],
                "last_message_at": row[4],
                "unread_count": row[5],
            }
            for row in rows
        ]
    }


@app.get("/api/messages/{user_id}")
def list_messages(
    user_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            require_message_recipient(cursor, user["id"], user_id)
            cursor.execute(
                """SELECT message_id, sender_id, receiver_id, message_text, is_read, sent_at
                   FROM (
                       SELECT message_id, sender_id, receiver_id, message_text, is_read, sent_at
                       FROM messages
                       WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)
                       ORDER BY sent_at DESC, message_id DESC LIMIT %s OFFSET %s
                   ) conversation ORDER BY sent_at, message_id""",
                (user["id"], user_id, user_id, user["id"], limit, offset),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()
    return {
        "messages": [
            {
                "message_id": row[0],
                "sender_id": row[1],
                "receiver_id": row[2],
                "message_text": row[3],
                "is_read": row[4],
                "sent_at": row[5],
            }
            for row in rows
        ],
        "limit": limit,
        "offset": offset,
    }


@app.post("/api/messages/{user_id}", status_code=status.HTTP_201_CREATED)
async def send_message(user_id: int, payload: MessageCreateRequest, user: dict = Depends(get_current_user)):
    connection = get_connection()
    row = None
    try:
        with connection.cursor() as cursor:
            require_message_recipient(cursor, user["id"], user_id)
            cursor.execute(
                """INSERT INTO messages (sender_id, receiver_id, message_text)
                   VALUES (%s, %s, %s)
                   RETURNING message_id, sender_id, receiver_id, message_text, is_read, sent_at""",
                (user["id"], user_id, payload.message_text),
            )
            row = cursor.fetchone()
            insert_notification(cursor, user_id, "MESSAGE", "New message", f"{user['full_name']} sent you a message.", "/messages")
        connection.commit()
    finally:
        connection.close()

    message_payload = serialize_message(row)
    await broadcast_chat_message(message_payload)
    return {"message": message_payload}


@app.post("/api/messages/{user_id}/read")
def mark_conversation_read(user_id: int, user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            require_message_recipient(cursor, user["id"], user_id)
            cursor.execute(
                "UPDATE messages SET is_read = TRUE WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE",
                (user_id, user["id"]),
            )
            updated_count = cursor.rowcount
        connection.commit()
    finally:
        connection.close()
    return {"updated_count": updated_count}


def order_record(cursor, order_id: int, current_user_id: int, lock: bool = False) -> dict:
    cursor.execute(
        """SELECT o.order_id, o.item_id, o.buyer_id, o.seller_id, o.agreed_price, o.status,
              o.ordered_at, o.updated_at, o.meetup_date, i.name, i.status,
                  buyer.username, buyer.full_name, seller.username, seller.full_name
           FROM orders o
           JOIN items i ON i.item_id = o.item_id
           JOIN users buyer ON buyer.user_id = o.buyer_id
           JOIN users seller ON seller.user_id = o.seller_id
           WHERE o.order_id = %s""" + (" FOR UPDATE OF o" if lock else ""),
        (order_id,),
    )
    row = cursor.fetchone()
    if row is None or current_user_id not in (row[2], row[3]):
        raise HTTPException(status_code=404, detail="Order not found.")
    return {
        "order_id": row[0],
        "item_id": row[1],
        "buyer_id": row[2],
        "seller_id": row[3],
        "agreed_price": float(row[4]),
        "status": row[5],
        "ordered_at": row[6],
        "updated_at": row[7],
        "meetup_date": row[8],
        "item_name": row[9],
        "item_status": row[10],
        "buyer": {"user_id": row[2], "username": row[11], "full_name": row[12]},
        "seller": {"user_id": row[3], "username": row[13], "full_name": row[14]},
        "current_user_role": "BUYER" if current_user_id == row[2] else "SELLER",
    }


@app.post("/api/items/{item_id}/orders", status_code=status.HTTP_201_CREATED)
def create_order(item_id: int, user: dict = Depends(get_current_user)):
    require_verified_contact(user)
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT seller_id, price, status FROM items WHERE item_id = %s FOR UPDATE",
                (item_id,),
            )
            item = cursor.fetchone()
            if item is None:
                raise HTTPException(status_code=404, detail="Product not found.")
            seller_id, price, item_status = item
            if seller_id == user["id"]:
                raise HTTPException(status_code=400, detail="You cannot order your own product.")
            if item_status != "AVAILABLE":
                raise HTTPException(status_code=409, detail="This product is no longer available.")
            cursor.execute(
                "SELECT 1 FROM orders WHERE item_id = %s AND buyer_id = %s AND status = 'PENDING' LIMIT 1",
                (item_id, user["id"]),
            )
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="You already have a pending request for this product.")
            cursor.execute(
                """INSERT INTO orders (item_id, buyer_id, seller_id, agreed_price)
                   VALUES (%s, %s, %s, %s) RETURNING order_id""",
                (item_id, user["id"], seller_id, price),
            )
            order_id = cursor.fetchone()[0]
            order = order_record(cursor, order_id, user["id"])
            insert_notification(cursor, seller_id, "ORDER", "New purchase request", f"{user['full_name']} requested {order['item_name']}.", "/orders")
            notify_admins(
                cursor,
                "ORDER",
                "Marketplace transaction started",
                f"{user['full_name']} requested {order['item_name']}.",
                "/notifications",
            )
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {"order": order}


@app.get("/api/orders")
def list_orders(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT o.order_id FROM orders o
                   WHERE o.buyer_id = %s OR o.seller_id = %s
                   ORDER BY o.ordered_at DESC, o.order_id DESC LIMIT %s OFFSET %s""",
                (user["id"], user["id"], limit, offset),
            )
            order_ids = [row[0] for row in cursor.fetchall()]
            orders = [order_record(cursor, order_id, user["id"]) for order_id in order_ids]
    finally:
        connection.close()
    return {"orders": orders, "limit": limit, "offset": offset}


@app.get("/api/orders/{order_id}")
def get_order(order_id: int, user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            order = order_record(cursor, order_id, user["id"])
    finally:
        connection.close()
    return {"order": order}


@app.patch("/api/orders/{order_id}/meetup-date")
def update_order_meetup_date(order_id: int, payload: OrderMeetupDateRequest, user: dict = Depends(get_current_user)):
    if payload.meetup_date is not None and payload.meetup_date < date.today():
        raise HTTPException(status_code=422, detail="Meetup date cannot be in the past.")
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            order = order_record(cursor, order_id, user["id"], lock=True)
            if order["status"] not in {"PENDING", "CONFIRMED"}:
                raise HTTPException(status_code=409, detail="Closed orders cannot be rescheduled.")
            cursor.execute(
                "UPDATE orders SET meetup_date = %s, updated_at = CURRENT_TIMESTAMP WHERE order_id = %s",
                (payload.meetup_date, order_id),
            )
            updated_order = order_record(cursor, order_id, user["id"])
            if payload.meetup_date != order["meetup_date"]:
                recipient_id = order["seller_id"] if user["id"] == order["buyer_id"] else order["buyer_id"]
                date_message = payload.meetup_date.isoformat() if payload.meetup_date else "No date selected"
                insert_notification(cursor, recipient_id, "ORDER", "Meetup date updated", f"{order['item_name']} meetup date: {date_message}.", "/orders")
                notify_admins(
                    cursor,
                    "ORDER",
                    "Marketplace meetup updated",
                    f"Order #{order_id} for {order['item_name']} has a new meetup date: {date_message}.",
                    "/notifications",
                )
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {"order": updated_order}


@app.patch("/api/orders/{order_id}")
def update_order(order_id: int, payload: OrderStatusRequest, user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            order = order_record(cursor, order_id, user["id"], lock=True)
            is_buyer = user["id"] == order["buyer_id"]
            is_seller = user["id"] == order["seller_id"]
            current_status = order["status"]
            next_status = payload.status

            if next_status == "CONFIRMED":
                if not is_seller:
                    raise HTTPException(status_code=403, detail="Only the seller can confirm an order.")
                if current_status != "PENDING":
                    raise HTTPException(status_code=409, detail="Only pending orders can be confirmed.")
                cursor.execute("SELECT status FROM items WHERE item_id = %s FOR UPDATE", (order["item_id"],))
                item = cursor.fetchone()
                if item is None or item[0] != "AVAILABLE":
                    raise HTTPException(status_code=409, detail="This product is no longer available.")
                cursor.execute(
                    "UPDATE items SET status = 'RESERVED', updated_at = CURRENT_TIMESTAMP WHERE item_id = %s AND status = 'AVAILABLE'",
                    (order["item_id"],),
                )
                if cursor.rowcount != 1:
                    raise HTTPException(status_code=409, detail="This product is no longer available.")
            elif next_status == "CANCELLED":
                if not (is_buyer or is_seller):
                    raise HTTPException(status_code=403, detail="Only the buyer or seller can cancel an order.")
                if current_status not in {"PENDING", "CONFIRMED"}:
                    raise HTTPException(status_code=409, detail="This order can no longer be cancelled.")
                if current_status == "CONFIRMED":
                    cursor.execute("SELECT status FROM items WHERE item_id = %s FOR UPDATE", (order["item_id"],))
                    item = cursor.fetchone()
                    if item is None or item[0] != "RESERVED":
                        raise HTTPException(status_code=409, detail="The reserved product cannot be released.")
                    cursor.execute(
                        "UPDATE items SET status = 'AVAILABLE', updated_at = CURRENT_TIMESTAMP WHERE item_id = %s AND status = 'RESERVED'",
                        (order["item_id"],),
                    )
                    if cursor.rowcount != 1:
                        raise HTTPException(status_code=409, detail="The reserved product cannot be released.")
            elif next_status == "COMPLETED":
                if not is_seller:
                    raise HTTPException(status_code=403, detail="Only the seller can complete an order.")
                if current_status != "CONFIRMED":
                    raise HTTPException(status_code=409, detail="Only confirmed orders can be completed.")
                cursor.execute("SELECT status FROM items WHERE item_id = %s FOR UPDATE", (order["item_id"],))
                item = cursor.fetchone()
                if item is None or item[0] != "RESERVED":
                    raise HTTPException(status_code=409, detail="The reserved product cannot be completed.")
                cursor.execute(
                    "UPDATE items SET status = 'SOLD', updated_at = CURRENT_TIMESTAMP WHERE item_id = %s AND status = 'RESERVED'",
                    (order["item_id"],),
                )
                if cursor.rowcount != 1:
                    raise HTTPException(status_code=409, detail="The reserved product cannot be completed.")

            cursor.execute(
                "UPDATE orders SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE order_id = %s",
                (next_status, order_id),
            )
            if next_status == "CONFIRMED":
                insert_notification(cursor, order["buyer_id"], "ORDER", "Order confirmed", f"Your request for {order['item_name']} was confirmed.", "/orders")
            elif next_status == "COMPLETED":
                insert_notification(cursor, order["buyer_id"], "ORDER", "Order completed", f"Your purchase of {order['item_name']} is complete.", "/orders")
            elif next_status == "CANCELLED":
                recipient_id = order["seller_id"] if is_buyer else order["buyer_id"]
                insert_notification(cursor, recipient_id, "ORDER", "Order cancelled", f"The request for {order['item_name']} was cancelled.", "/orders")
            transaction_titles = {
                "CONFIRMED": "Marketplace transaction confirmed",
                "COMPLETED": "Marketplace transaction completed",
                "CANCELLED": "Marketplace transaction cancelled",
            }
            notify_admins(
                cursor,
                "ORDER",
                transaction_titles[next_status],
                f"Order #{order_id} for {order['item_name']} was {next_status.lower()}.",
                "/notifications",
            )
            updated_order = order_record(cursor, order_id, user["id"])
        connection.commit()
    except psycopg2.IntegrityError as error:
        connection.rollback()
        raise HTTPException(status_code=409, detail="Another order already reserves this product.") from error
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {"order": updated_order}


@app.get("/api/notifications")
def list_notifications(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT notification_id, notification_type, title, message, target_url, is_read, created_at
                   FROM notifications WHERE user_id = %s
                   ORDER BY notification_id DESC LIMIT %s OFFSET %s""",
                (user["id"], limit, offset),
            )
            notifications = [serialize_notification(row) for row in cursor.fetchall()]
            cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_id = %s AND is_read = FALSE", (user["id"],))
            unread_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_id = %s", (user["id"],))
            total_count = cursor.fetchone()[0]
    finally:
        connection.close()
    return {"notifications": notifications, "unread_count": unread_count, "total_count": total_count, "limit": limit, "offset": offset}


@app.get("/api/notifications/unread-count")
def unread_notification_count(user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_id = %s AND is_read = FALSE", (user["id"],))
            unread_count = cursor.fetchone()[0]
    finally:
        connection.close()
    return {"unread_count": unread_count}


@app.patch("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE notifications SET is_read = TRUE
                   WHERE notification_id = %s AND user_id = %s
                   RETURNING notification_id, notification_type, title, message, target_url, is_read, created_at""",
                (notification_id, user["id"]),
            )
            row = cursor.fetchone()
        connection.commit()
    finally:
        connection.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return {"notification": serialize_notification(row)}


@app.post("/api/notifications/read-all")
def mark_all_notifications_read(user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE notifications SET is_read = TRUE WHERE user_id = %s AND is_read = FALSE", (user["id"],))
            updated_count = cursor.rowcount
        connection.commit()
    finally:
        connection.close()
    return {"updated_count": updated_count}


def report_record(cursor, report_id: int) -> dict:
    cursor.execute(
        """SELECT r.report_id, r.reporter_id, reporter.username, reporter.full_name,
                  r.item_id, i.name, r.reported_user_id, seller.username, seller.full_name,
                  r.reason, r.status, r.created_at, r.reviewed_by, reviewer.username, r.resolved_at
           FROM reports r
           JOIN users reporter ON reporter.user_id = r.reporter_id
           LEFT JOIN items i ON i.item_id = r.item_id
           LEFT JOIN users seller ON seller.user_id = r.reported_user_id
           LEFT JOIN users reviewer ON reviewer.user_id = r.reviewed_by
           WHERE r.report_id = %s""",
        (report_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {
        "report_id": row[0],
        "reporter": {"user_id": row[1], "username": row[2], "full_name": row[3]},
        "item": {"item_id": row[4], "name": row[5]} if row[4] is not None else None,
        "reported_user": {"user_id": row[6], "username": row[7], "full_name": row[8]} if row[6] is not None else None,
        "reason": row[9],
        "status": row[10],
        "created_at": row[11],
        "reviewed_by": row[12],
        "reviewer_username": row[13],
        "resolved_at": row[14],
    }


@app.post("/api/items/{item_id}/reports", status_code=status.HTTP_201_CREATED)
def submit_product_report(item_id: int, payload: ProductReportRequest, user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT seller_id, name FROM items WHERE item_id = %s", (item_id,))
            item = cursor.fetchone()
            if item is None:
                raise HTTPException(status_code=404, detail="Product not found.")
            if item[0] == user["id"]:
                raise HTTPException(status_code=400, detail="You cannot report your own product.")
            cursor.execute(
                """INSERT INTO reports (reporter_id, reported_user_id, item_id, reason)
                   VALUES (%s, %s, %s, %s) RETURNING report_id""",
                (user["id"], item[0], item_id, payload.reason),
            )
            report_id = cursor.fetchone()[0]
            notify_admins(cursor, "REPORT", "Product reported", f"{user['full_name']} reported {item[1]}.", "/admin/moderation")
            report = report_record(cursor, report_id)
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {"report": report}


@app.get("/api/admin/reports")
def list_admin_reports(
    status_filter: Optional[Literal["OPEN", "REVIEWING", "RESOLVED", "REJECTED"]] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(require_admin),
):
    where_clause = " WHERE status = %s" if status_filter else ""
    parameters = [status_filter] if status_filter else []
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM reports{where_clause}", parameters)
            total_count = cursor.fetchone()[0]
            cursor.execute(
                f"SELECT report_id FROM reports{where_clause} ORDER BY created_at DESC, report_id DESC LIMIT %s OFFSET %s",
                (*parameters, limit, offset),
            )
            report_ids = [row[0] for row in cursor.fetchall()]
            reports = [report_record(cursor, report_id) for report_id in report_ids]
    finally:
        connection.close()
    return {"reports": reports, "total_count": total_count, "limit": limit, "offset": offset}


@app.patch("/api/admin/reports/{report_id}")
def update_admin_report(report_id: int, payload: ReportStatusRequest, user: dict = Depends(require_admin)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE reports SET status = %s, reviewed_by = %s,
                          resolved_at = CASE WHEN %s IN ('RESOLVED', 'REJECTED') THEN CURRENT_TIMESTAMP ELSE NULL END
                   WHERE report_id = %s RETURNING report_id""",
                (payload.status, user["id"], payload.status, report_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Report not found.")
            report = report_record(cursor, report_id)
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {"report": report}


@app.get("/api/admin/users/search")
def search_admin_users(q: str = Query(min_length=2, max_length=50), user: dict = Depends(require_admin)):
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Search must contain at least 2 characters.")
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT user_id, username, full_name, posting_banned, posting_ban_reason, posting_banned_at
                   FROM users WHERE role = 'STUDENT'
                     AND (POSITION(LOWER(%s) IN LOWER(username)) > 0
                          OR POSITION(LOWER(%s) IN LOWER(full_name)) > 0)
                   ORDER BY username, user_id LIMIT 20""",
                (query, query),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()
    return {
        "users": [
            {
                "user_id": row[0],
                "username": row[1],
                "full_name": row[2],
                "posting_banned": row[3],
                "posting_ban_reason": row[4],
                "posting_banned_at": row[5],
            }
            for row in rows
        ]
    }


@app.patch("/api/admin/users/{user_id}/posting-ban")
def update_user_posting_ban(
    user_id: int,
    payload: PostingBanRequest,
    user: dict = Depends(require_admin),
):
    if payload.banned and not payload.reason:
        raise HTTPException(status_code=422, detail="A reason is required to ban posting.")
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            if payload.banned:
                cursor.execute(
                    """UPDATE users SET posting_banned = TRUE, posting_ban_reason = %s,
                              posting_banned_by = %s, posting_banned_at = CURRENT_TIMESTAMP
                       WHERE user_id = %s AND role = 'STUDENT'
                       RETURNING user_id, username, full_name, posting_banned, posting_ban_reason, posting_banned_at""",
                    (payload.reason, user["id"], user_id),
                )
            else:
                cursor.execute(
                    """UPDATE users SET posting_banned = FALSE, posting_ban_reason = NULL,
                              posting_banned_by = NULL, posting_banned_at = NULL
                       WHERE user_id = %s AND role = 'STUDENT'
                       RETURNING user_id, username, full_name, posting_banned, posting_ban_reason, posting_banned_at""",
                    (user_id,),
                )
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Student account not found.")
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {
        "user": {
            "user_id": row[0],
            "username": row[1],
            "full_name": row[2],
            "posting_banned": row[3],
            "posting_ban_reason": row[4],
            "posting_banned_at": row[5],
        }
    }


@app.get("/api/reports/market-summary")
def market_summary(user: dict = Depends(require_admin)):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM items;")
            total_listings = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM users;")
            total_users = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'COMPLETED';")
            completed_orders = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COALESCE(SUM(agreed_price), 0) FROM orders WHERE status = 'COMPLETED';")
            revenue = float(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT category, COUNT(*) FROM items GROUP BY category ORDER BY COUNT(*) DESC LIMIT 3;")
            top_categories = cursor.fetchall()
    finally:
        connection.close()
    return {
        "total_listings": total_listings,
        "total_users": total_users,
        "completed_orders": completed_orders,
        "revenue": revenue,
        "top_categories": [{"category": category, "count": count} for category, count in top_categories],
    }


@app.get("/api/reports/download")
def market_report_download(user: dict = Depends(require_admin)):
    pdf_bytes = generate_market_report()
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=market_report.pdf"})


@app.post("/graphql")
async def graphql_route(request: Request):
    payload = await request.json()
    if not payload or "query" not in payload:
        raise HTTPException(status_code=400, detail="A GraphQL query is required.")
    result = await run_in_threadpool(schema.execute, payload["query"], context_value={"request": request})
    if result.errors:
        return {"data": result.data, "errors": [{"message": error.message} for error in result.errors]}
    return {"data": result.data}
