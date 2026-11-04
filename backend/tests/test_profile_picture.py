import pytest


def test_user_can_upload_profile_picture_and_see_it_on_current_user(client, make_user, monkeypatch):
    async def store_image(*args):
        return {
            "storage": "local",
            "secure_url": "http://localhost:8000/uploads/profile-photo.png",
        }

    monkeypatch.setattr("main.store_image_upload", store_image)
    user = make_user()

    response = client.post(
        "/api/auth/profile-image",
        headers=user["headers"],
        files={"file": ("profile.png", b"\x89PNG\r\n\x1a\nimage", "image/png")},
    )

    assert response.status_code == 200, response.text
    assert response.json()["profile_image_url"] == "http://localhost:8000/uploads/profile-photo.png"

    current_user = client.get("/api/auth/me", headers=user["headers"])
    assert current_user.status_code == 200, current_user.text
    assert current_user.json()["user"]["profile_image_url"] == response.json()["profile_image_url"]


def test_profile_picture_upload_requires_authentication(client):
    response = client.post(
        "/api/auth/profile-image",
        files={"file": ("profile.png", b"\x89PNG\r\n\x1a\nimage", "image/png")},
    )

    assert response.status_code == 401


def test_profile_picture_upload_rejects_non_image_content(client, make_user, monkeypatch):
    user = make_user()
    monkeypatch.setattr("main.store_image_upload", lambda *args: pytest.fail("must reject first"))

    response = client.post(
        "/api/auth/profile-image",
        headers=user["headers"],
        files={"file": ("profile.png", b"not an image", "image/png")},
    )

    assert response.status_code == 415
