import hashlib
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.websockets import WebSocketDisconnect

from main import (
    ItemCreateRequest,
    MAX_UPLOAD_BYTES,
    app,
    get_current_user,
    limiter,
)
from ml_model import SimpleCategoryModel, load_model
from settings import Settings


def test_settings_require_jwt_secret(monkeypatch, tmp_path):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_ENV=test\n"
        "DATABASE_URL=postgresql://user@localhost:5432/campusxmart_test\n"
        "JWT_EXPIRES_MINUTES=60\n"
        "CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173\n"
    )
    with pytest.raises(ValidationError):
        Settings(_env_file=env_file)


def test_settings_reject_public_jwt_placeholder(monkeypatch, tmp_path):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_ENV=test\n"
        "DATABASE_URL=postgresql:///campusxmart_test\n"
        "JWT_SECRET_KEY=replace-with-32-plus-character-secret\n"
    )

    with pytest.raises(ValidationError):
        Settings(_env_file=env_file)


def test_category_model_ignores_filesystem_model_files(tmp_path):
    model_file = tmp_path / "untrusted.pkl"
    model_file.write_bytes(b"not a model")

    model = load_model(str(model_file))

    assert isinstance(model, SimpleCategoryModel)
    assert model.predict("textbook") == "Books"
    assert model_file.read_bytes() == b"not a model"


def test_assistant_requires_login():
    client = TestClient(app)
    response = client.post("/api/assistant/chat", json={"query": "How do I sell my bike?"})
    assert response.status_code == 401


def test_graphql_returns_data_wrapper():
    client = TestClient(app)
    response = client.post(
        "/graphql",
        json={"query": "{ hello }"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "data" in payload
    assert payload["data"]["hello"] == "Hello from Campus X Mart GraphQL"


def test_locations_create_requires_auth():
    client = TestClient(app)
    response = client.post(
        "/api/locations",
        json={"location_name": "Main Gate", "campus_name": "Campus A"},
    )
    assert response.status_code == 401


def test_make_item_fixture_creates_verified_listing(make_item):
    assert make_item()


def test_item_video_url_must_be_youtube_video():
    item = {
        "name": "Campus bike",
        "price": 20,
        "category": "Sports",
        "condition": "Good",
        "description": "A used bike in good condition.",
        "video_url": "https://youtu.be/dQw4w9WgXcQ",
    }
    assert ItemCreateRequest(**item).video_url == item["video_url"]

    item["video_url"] = "https://example.com/video"
    with pytest.raises(ValidationError):
        ItemCreateRequest(**item)


def test_item_endpoint_rejects_non_youtube_video(client, auth_headers):
    headers = auth_headers(email="video-validation@example.com")
    response = client.post(
        "/api/items",
        headers=headers,
        json={
            "name": "Campus bike",
            "price": 20,
            "category": "Sports",
            "condition": "Used - Good",
            "description": "A used bike in good condition.",
            "video_url": "https://example.com/video",
        },
    )
    assert response.status_code == 422


def test_login_is_rate_limited(client):
    limiter.reset()
    try:
        responses = [
            client.post(
                "/api/auth/login",
                json={"email": "nobody@example.com", "password": "Password123!"},
            )
            for _ in range(6)
        ]
    finally:
        limiter.reset()
    assert [response.status_code for response in responses[:5]] == [401] * 5
    assert responses[5].status_code == 429


def test_image_upload_validates_and_stores_local_images(monkeypatch, tmp_path):
    monkeypatch.setattr("main.UPLOADS_DIR", tmp_path)
    monkeypatch.setattr("main.settings.APP_ENV", "test")
    app.dependency_overrides[get_current_user] = lambda: {"user_id": 1}
    client = TestClient(app)

    try:
        valid = client.post(
            "/api/upload/image",
            files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0image", "image/jpeg")},
        )
        assert valid.status_code == 200, valid.text
        assert valid.json()["storage"] == "local"
        uploaded_path = valid.json()["secure_url"].rsplit("/", 1)[-1]
        assert (tmp_path / uploaded_path).read_bytes() == b"\xff\xd8\xff\xe0image"

        spoofed = client.post(
            "/api/upload/image",
            files={"file": ("photo.png", b"not an image", "image/png")},
        )
        assert spoofed.status_code == 415

        oversized = client.post(
            "/api/upload/image",
            files={"file": ("large.jpg", b"x" * (MAX_UPLOAD_BYTES + 1), "image/jpeg")},
        )
        assert oversized.status_code == 413

        monkeypatch.setattr("main.settings.APP_ENV", "prod")
        monkeypatch.setattr("main.settings.CLOUDINARY_CLOUD_NAME", None)
        monkeypatch.setattr("main.settings.CLOUDINARY_API_KEY", None)
        monkeypatch.setattr("main.settings.CLOUDINARY_API_SECRET", None)
        unconfigured_prod = client.post(
            "/api/upload/image",
            files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0image", "image/jpeg")},
        )
        assert unconfigured_prod.status_code == 503

        monkeypatch.setattr("main.settings.CLOUDINARY_CLOUD_NAME", "test-cloud")
        monkeypatch.setattr("main.settings.CLOUDINARY_API_KEY", "test-api-key")
        monkeypatch.setattr("main.settings.CLOUDINARY_API_SECRET", "test-api-secret")
        cloudinary_response = MagicMock()
        cloudinary_response.json.return_value = {
            "secure_url": "https://res.cloudinary.com/test/image/upload/photo.jpg",
            "public_id": "photo",
        }
        cloudinary_post = MagicMock(return_value=cloudinary_response)
        monkeypatch.setattr("main.requests.post", cloudinary_post)
        signed_upload = client.post(
            "/api/upload/image",
            files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0image", "image/jpeg")},
        )
        assert signed_upload.status_code == 200
        cloudinary_data = cloudinary_post.call_args.kwargs["data"]
        assert cloudinary_data["api_key"] == "test-api-key"
        assert cloudinary_data["signature"] == hashlib.sha1(
            f"timestamp={cloudinary_data['timestamp']}test-api-secret".encode()
        ).hexdigest()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_local_image_upload_does_not_use_client_filename_as_a_path(monkeypatch, tmp_path):
    monkeypatch.setattr("main.UPLOADS_DIR", tmp_path)
    monkeypatch.setattr("main.settings.APP_ENV", "test")
    app.dependency_overrides[get_current_user] = lambda: {"user_id": 1}
    client = TestClient(app)

    try:
        response = client.post(
            "/api/upload/image",
            files={"file": ("../../outside.jpg", b"\xff\xd8\xff\xe0image", "image/jpeg")},
        )
        assert response.status_code == 200, response.text
        filename = response.json()["secure_url"].rsplit("/", 1)[-1]
        assert filename.endswith(".jpg")
        assert (tmp_path / filename).is_file()
        assert not (tmp_path.parent / "outside.jpg").exists()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_uploads_are_served_from_static_files(monkeypatch, tmp_path):
    monkeypatch.setattr("main.UPLOADS_DIR", tmp_path)
    uploaded = tmp_path / "stored-image.jpg"
    uploaded.write_bytes(b"\xff\xd8\xff\xe0image")

    client = TestClient(app)
    response = client.get("/uploads/stored-image.jpg")
    assert response.status_code == 200, response.text
    assert response.content == b"\xff\xd8\xff\xe0image"


def test_image_upload_rejects_mismatched_non_image_content_type(monkeypatch):
    monkeypatch.setattr("main.settings.APP_ENV", "test")
    app.dependency_overrides[get_current_user] = lambda: {"user_id": 1}
    client = TestClient(app)

    try:
        response = client.post(
            "/api/upload/image",
            files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0image", "text/plain")},
        )
        assert response.status_code == 415, response.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_chat_websocket_ticket_is_single_use(client, auth_headers):
    headers = auth_headers(email="chat-ticket@example.com")
    response = client.post(
        "/api/ws/ticket",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    ticket = response.json()["ticket"]
    with client.websocket_connect(f"/api/ws/chat?ticket={ticket}"):
        pass

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/ws/chat?ticket={ticket}"):
            pass

    access_token = headers["Authorization"].removeprefix("Bearer ")
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/ws/chat?token={access_token}"):
            pass
