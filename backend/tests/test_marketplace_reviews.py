def complete_order(client, seller, buyer, item_id):
    requested = client.post(f"/api/items/{item_id}/orders", headers=buyer["headers"])
    assert requested.status_code == 201, requested.text
    order_id = requested.json()["order"]["order_id"]
    confirmed = client.patch(
        f"/api/orders/{order_id}",
        headers=seller["headers"],
        json={"status": "CONFIRMED"},
    )
    assert confirmed.status_code == 200, confirmed.text
    completed = client.patch(
        f"/api/orders/{order_id}",
        headers=seller["headers"],
        json={"status": "COMPLETED"},
    )
    assert completed.status_code == 200, completed.text


def test_only_completed_buyer_can_review_and_review_updates_in_place(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    pending_buyer = make_user(verified=True)
    item_id = make_item(seller=seller)["item"]["item_id"]

    anonymous = client.get(f"/api/items/{item_id}/reviews")
    pending = client.post(
        f"/api/items/{item_id}/orders",
        headers=pending_buyer["headers"],
    )
    early_review = client.put(
        f"/api/items/{item_id}/reviews",
        headers=pending_buyer["headers"],
        json={"rating": 5, "review_text": "Not completed yet."},
    )
    self_review = client.put(
        f"/api/items/{item_id}/reviews",
        headers=seller["headers"],
        json={"rating": 5, "review_text": "My own item."},
    )

    assert anonymous.status_code == 401
    assert pending.status_code == 201, pending.text
    assert early_review.status_code == 403
    assert self_review.status_code == 403

    complete_order(client, seller, buyer, item_id)
    first = client.put(
        f"/api/items/{item_id}/reviews",
        headers=buyer["headers"],
        json={"rating": 5, "review_text": "Exactly as described, thank you."},
    )
    updated = client.put(
        f"/api/items/{item_id}/reviews",
        headers=buyer["headers"],
        json={"rating": 4, "review_text": "Good condition and easy pickup."},
    )

    assert first.status_code == 200, first.text
    assert updated.status_code == 200, updated.text
    reviews = client.get(f"/api/items/{item_id}/reviews", headers=seller["headers"])
    assert reviews.status_code == 200, reviews.text
    payload = reviews.json()
    assert payload["review_count"] == 1
    assert payload["average_rating"] == 4.0
    assert payload["seller_rating"] == 4.0
    assert payload["reviews"][0]["rating"] == 4
    assert payload["reviews"][0]["review_text"] == "Good condition and easy pickup."
    assert payload["reviews"][0]["author"]["username"] == buyer["user"]["username"]


def test_products_include_item_and_seller_ratings(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    item = make_item(seller=seller)["item"]
    another_item = make_item(seller=seller, name="Campus desk lamp")["item"]
    complete_order(client, seller, buyer, item["item_id"])
    review = client.put(
        f"/api/items/{item['item_id']}/reviews",
        headers=buyer["headers"],
        json={"rating": 5, "review_text": "Works perfectly."},
    )
    assert review.status_code == 200, review.text

    response = client.get("/api/items", headers=buyer["headers"])
    assert response.status_code == 200, response.text
    product = next(result for result in response.json()["items"] if result["item_id"] == another_item["item_id"])
    assert product["average_rating"] is None
    assert product["review_count"] == 0
    assert product["seller_rating"] == 5.0
