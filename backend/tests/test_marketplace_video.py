from unittest.mock import Mock


def test_listing_video_url_is_validated_saved_and_returned_in_products(client, make_user):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    payload = {
        "name": "Intro to calculus",
        "description": "A useful lecture recording for the calculus course.",
        "price": 10,
        "category": "Books",
        "item_condition": "USED_GOOD",
        "status": "AVAILABLE",
        "video_url": "https://youtu.be/dQw4w9WgXcQ",
    }

    created = client.post("/api/listings", headers=seller["headers"], json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["item"]["video_url"] == payload["video_url"]

    payload["video_url"] = "https://www.youtube.com/watch?v=abcdefghijk"
    updated = client.put(
        f"/api/listings/{created.json()['item']['item_id']}",
        headers=seller["headers"],
        json=payload,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["item"]["video_url"] == payload["video_url"]

    products = client.get("/api/items", headers=buyer["headers"])
    assert products.status_code == 200, products.text
    assert products.json()["items"][0]["video_url"] == payload["video_url"]


def test_listing_rejects_non_youtube_and_spoofed_hosts(client, make_user):
    seller = make_user(verified=True)
    payload = {
        "name": "Video listing",
        "description": "A useful item with a video demonstration.",
        "price": 10,
        "category": "Electronics",
        "item_condition": "USED_GOOD",
    }

    for video_url in ("https://example.com/video", "https://youtube.com.evil.example/watch?v=abcdefghijk"):
        response = client.post(
            "/api/listings",
            headers=seller["headers"],
            json={**payload, "video_url": video_url},
        )
        assert response.status_code == 422


def test_listing_video_upload_is_saved_and_returned_to_listings_and_products(
    client, make_user, make_item, monkeypatch
):
    import cloudinary.uploader

    seller = make_user(verified=True)
    item = make_item(seller=seller)["item"]
    monkeypatch.setattr("main.settings.CLOUDINARY_CLOUD_NAME", "test-cloud")
    monkeypatch.setattr("main.settings.CLOUDINARY_UPLOAD_PRESET", "test-preset")
    upload = Mock(return_value={
        "secure_url": "https://res.cloudinary.com/test-cloud/video/upload/campus-item.mp4",
        "public_id": "campus-x-mart/listings/1/campus-item",
    })
    monkeypatch.setattr(cloudinary.uploader, "upload", upload)

    response = client.post(
        f"/api/listings/{item['item_id']}/media",
        headers=seller["headers"],
        files={"file": ("item.mp4", b"\x00\x00\x00\x18ftypmp42video-data", "video/mp4")},
    )

    assert response.status_code == 201, response.text
    assert response.json()["media"]["media_type"] == "VIDEO"
    upload.assert_called_once()
    assert upload.call_args.kwargs["resource_type"] == "video"

    listings = client.get("/api/listings/mine", headers=seller["headers"])
    assert listings.status_code == 200, listings.text
    assert listings.json()["items"][0]["uploaded_video_url"] == response.json()["media"]["media_url"]

    products = client.get("/api/items", headers=seller["headers"])
    assert products.status_code == 200, products.text
    assert products.json()["items"][0]["uploaded_video_url"] == response.json()["media"]["media_url"]


def test_listing_video_upload_rejects_invalid_and_oversized_videos(
    client, make_user, make_item, monkeypatch
):
    seller = make_user(verified=True)
    item = make_item(seller=seller)["item"]
    endpoint = f"/api/listings/{item['item_id']}/media"

    invalid = client.post(
        endpoint,
        headers=seller["headers"],
        files={"file": ("not-a-video.mp4", b"not a video", "video/mp4")},
    )
    assert invalid.status_code == 415

    monkeypatch.setattr("main.MAX_VIDEO_UPLOAD_BYTES", 8)
    oversized = client.post(
        endpoint,
        headers=seller["headers"],
        files={"file": ("large.mp4", b"\x00\x00\x00\x18ftypmp42", "video/mp4")},
    )
    assert oversized.status_code == 413
