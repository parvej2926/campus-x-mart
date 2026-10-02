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
