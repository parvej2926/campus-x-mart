import os
import secrets
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
import pytest
from fastapi.testclient import TestClient
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[2]
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL must point to a dedicated *_test database.")

database_name = urlparse(TEST_DATABASE_URL).path.rsplit("/", 1)[-1]
if not database_name.endswith("_test"):
    raise RuntimeError("Refusing to run tests unless TEST_DATABASE_URL names a *_test database.")

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET_KEY", "testing-secret-key-1234567890-abcdef")
os.environ.setdefault("JWT_EXPIRES_MINUTES", "60")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

from main import app, create_token, limiter, get_connection


@pytest.fixture(scope="session", autouse=True)
def rebuild_test_database():
    connection = psycopg2.connect(TEST_DATABASE_URL)
    try:
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE;")
            cursor.execute("CREATE SCHEMA public;")
            cursor.execute((ROOT / "database" / "schema.sql").read_text())
        connection.commit()
        yield
    finally:
        connection.close()


@pytest.fixture(autouse=True)
def truncate_test_database(rebuild_test_database, client):
    limiter.reset()
    client.cookies.clear()
    connection = psycopg2.connect(TEST_DATABASE_URL)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
            tables = [row[0] for row in cursor.fetchall()]
            if tables:
                names = sql.SQL(", ").join(sql.Identifier(table) for table in tables)
                cursor.execute(sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE;").format(names))
        connection.commit()
        yield
    finally:
        connection.close()
        limiter.reset()
        client.cookies.clear()


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def make_user(client):
    def _make(
        role: str = "STUDENT",
        verified: bool = False,
        email: str = None,
        password: str = "Password123!",
    ):
        suffix = secrets.token_hex(4)
        email = email or f"student-{suffix}@example.com"
        response = client.post(
            "/api/auth/register",
            json={
                "username": f"student_{suffix}",
                "full_name": "Student User",
                "email": email,
                "phone": f"017{secrets.randbelow(10**8):08d}",
                "password": password,
            },
        )
        assert response.status_code == 201, response.text
        user = response.json()["user"]
        if role != "STUDENT" or verified:
            connection = get_connection()
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE users SET role = %s, email_verified = %s, phone_verified = %s WHERE user_id = %s;",
                        (role, verified, verified, user["user_id"]),
                    )
                connection.commit()
            finally:
                connection.close()
        headers = {
            "Authorization": (
                f"Bearer {create_token(user['user_id'], user['username'], admin_session=role == 'ADMIN')}"
            )
        }
        return {
            "user": user,
            "headers": headers,
            "password": password,
        }

    return _make


@pytest.fixture
def token_headers():
    def _make(user, admin_session: bool = False):
        token = create_token(user["user_id"], user["username"], admin_session=admin_session)
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture
def auth_headers(make_user):
    def _make(
        email: str = None,
        password: str = "Password123!",
        role: str = "STUDENT",
        verified: bool = False,
    ):
        return make_user(role=role, verified=verified, email=email, password=password)["headers"]

    return _make


@pytest.fixture
def make_item(client, make_user):
    def _make(seller=None, **overrides):
        seller = seller or make_user(verified=True)
        payload = {
            "name": "Campus bicycle",
            "price": 35,
            "category": "Sports",
            "condition": "Used - Good",
            "description": "A bicycle in good working condition.",
            **overrides,
        }
        response = client.post("/api/items", headers=seller["headers"], json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make
