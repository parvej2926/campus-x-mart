import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException, Request, Response

from database import get_connection
from settings import settings

ACCESS_COOKIE = "campus_x_mart_session"
REFRESH_COOKIE = "campus_x_mart_refresh"
CSRF_COOKIE = "campus_x_mart_csrf"
REFRESH_LIFETIME = timedelta(days=30)
MAX_SESSION_LIFETIME = timedelta(days=90)


def create_token(user_id: int, username: str, admin_session: bool = False, session_id: Optional[str] = None) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)
    claims = {"sub": str(user_id), "username": username, "admin_session": admin_session, "exp": expires}
    if session_id is not None:
        claims["sid"] = session_id
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm="HS256")


def create_session(user_id: int, username: str, admin_session: bool = False) -> tuple[str, str]:
    session_id = uuid.uuid4()
    refresh_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + REFRESH_LIFETIME
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO user_sessions
                   (session_id, user_id, refresh_token_hash, expires_at, admin_session)
                   VALUES (%s, %s, %s, %s, %s)""",
                (str(session_id), user_id, _token_hash(refresh_token), expires_at, admin_session),
            )
        connection.commit()
    finally:
        connection.close()
    return create_token(user_id, username, admin_session, str(session_id)), refresh_token


def rotate_session(refresh_token: Optional[str]) -> Optional[tuple[str, str]]:
    if not refresh_token:
        return None

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT s.session_id, s.user_id, s.admin_session, s.created_at,
                          u.username, u.role
                   FROM user_sessions s
                   JOIN users u ON u.user_id = s.user_id
                   WHERE s.refresh_token_hash = %s
                     AND s.revoked_at IS NULL
                     AND s.expires_at > CURRENT_TIMESTAMP
                   FOR UPDATE OF s""",
                (_token_hash(refresh_token),),
            )
            row = cursor.fetchone()
            if row is None:
                connection.rollback()
                return None

            session_id, user_id, admin_session, created_at, username, role = row
            if (
                created_at < datetime.now(timezone.utc) - MAX_SESSION_LIFETIME
                or (admin_session and role != "ADMIN")
            ):
                cursor.execute(
                    "UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE session_id = %s",
                    (session_id,),
                )
                connection.commit()
                return None

            new_refresh_token = secrets.token_urlsafe(48)
            cursor.execute(
                """UPDATE user_sessions
                   SET refresh_token_hash = %s, expires_at = %s
                   WHERE session_id = %s""",
                (
                    _token_hash(new_refresh_token),
                    datetime.now(timezone.utc) + REFRESH_LIFETIME,
                    str(session_id),
                ),
            )
        connection.commit()
        return (
            create_token(user_id, username, admin_session, str(session_id)),
            new_refresh_token,
        )
    finally:
        connection.close()


def revoke_session(refresh_token: Optional[str], access_token: Optional[str] = None) -> None:
    session_id = _session_id_from_access_token(access_token)
    if not refresh_token and session_id is None:
        return
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            if refresh_token:
                cursor.execute(
                    """UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP
                       WHERE refresh_token_hash = %s AND revoked_at IS NULL""",
                    (_token_hash(refresh_token),),
                )
            if session_id is not None and (not refresh_token or cursor.rowcount == 0):
                cursor.execute(
                    """UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP
                       WHERE session_id = %s AND revoked_at IS NULL""",
                    (session_id,),
                )
        connection.commit()
    finally:
        connection.close()


def set_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = settings.APP_ENV == "prod"
    same_site = "none" if secure else "lax"
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        httponly=True,
        secure=secure,
        samesite=same_site,
        max_age=settings.JWT_EXPIRES_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        httponly=True,
        secure=secure,
        samesite=same_site,
        max_age=int(REFRESH_LIFETIME.total_seconds()),
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(32),
        httponly=False,
        secure=secure,
        samesite=same_site,
        max_age=int(REFRESH_LIFETIME.total_seconds()),
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    secure = settings.APP_ENV == "prod"
    same_site = "none" if secure else "lax"
    for cookie_name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        response.delete_cookie(
            cookie_name,
            path="/",
            secure=secure,
            httponly=cookie_name != CSRF_COOKIE,
            samesite=same_site,
        )


def validate_csrf(request: Request) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get("X-CSRF-Token", "")
    if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed.")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _session_id_from_access_token(access_token: Optional[str]) -> Optional[str]:
    if not access_token:
        return None
    try:
        claims = jwt.decode(access_token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        return str(uuid.UUID(claims["sid"])) if claims.get("sid") is not None else None
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return None
