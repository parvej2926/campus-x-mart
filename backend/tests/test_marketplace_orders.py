def test_order_price_comes_from_item_and_seller_can_complete(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    item = make_item(seller=seller, price=48)["item"]

    requested = client.post(
        f"/api/items/{item['item_id']}/orders",
        headers=buyer["headers"],
        json={"agreed_price": 1},
    )

    assert requested.status_code == 201, requested.text
    order = requested.json()["order"]
    assert order["agreed_price"] == 48
    assert order["status"] == "PENDING"
    products = client.get("/api/items", headers=buyer["headers"]).json()["items"]
    product = next(product for product in products if product["item_id"] == item["item_id"])
    assert product["my_order_status"] == "PENDING"

    confirmed = client.patch(
        f"/api/orders/{order['order_id']}",
        headers=seller["headers"],
        json={"status": "CONFIRMED"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["order"]["item_status"] == "RESERVED"

    completed = client.patch(
        f"/api/orders/{order['order_id']}",
        headers=seller["headers"],
        json={"status": "COMPLETED"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["order"]["status"] == "COMPLETED"
    assert completed.json()["order"]["item_status"] == "SOLD"


def test_confirmed_order_cancellation_releases_item_and_prevents_another_active_order(client, make_user, make_item):
    seller = make_user(verified=True)
    first_buyer = make_user(verified=True)
    second_buyer = make_user(verified=True)
    item_id = make_item(seller=seller)["item"]["item_id"]

    first = client.post(f"/api/items/{item_id}/orders", headers=first_buyer["headers"])
    second = client.post(f"/api/items/{item_id}/orders", headers=second_buyer["headers"])
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    confirmed = client.patch(
        f"/api/orders/{first.json()['order']['order_id']}",
        headers=seller["headers"],
        json={"status": "CONFIRMED"},
    )
    assert confirmed.status_code == 200, confirmed.text

    conflict = client.patch(
        f"/api/orders/{second.json()['order']['order_id']}",
        headers=seller["headers"],
        json={"status": "CONFIRMED"},
    )
    assert conflict.status_code == 409

    cancelled = client.patch(
        f"/api/orders/{first.json()['order']['order_id']}",
        headers=first_buyer["headers"],
        json={"status": "CANCELLED"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["order"]["item_status"] == "AVAILABLE"

    reconfirmed = client.patch(
        f"/api/orders/{second.json()['order']['order_id']}",
        headers=seller["headers"],
        json={"status": "CONFIRMED"},
    )
    assert reconfirmed.status_code == 200, reconfirmed.text


def test_seller_can_decline_pending_order_but_cannot_order_own_or_unavailable_item(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    other_buyer = make_user(verified=True)
    late_buyer = make_user(verified=True)
    item_id = make_item(seller=seller)["item"]["item_id"]

    self_order = client.post(f"/api/items/{item_id}/orders", headers=seller["headers"])
    request = client.post(f"/api/items/{item_id}/orders", headers=buyer["headers"])
    assert self_order.status_code == 400
    assert request.status_code == 201, request.text

    declined = client.patch(
        f"/api/orders/{request.json()['order']['order_id']}",
        headers=seller["headers"],
        json={"status": "CANCELLED"},
    )
    assert declined.status_code == 200, declined.text
    assert declined.json()["order"]["status"] == "CANCELLED"

    second_request = client.post(f"/api/items/{item_id}/orders", headers=other_buyer["headers"])
    assert second_request.status_code == 201, second_request.text
    confirmed = client.patch(
        f"/api/orders/{second_request.json()['order']['order_id']}",
        headers=seller["headers"],
        json={"status": "CONFIRMED"},
    )
    assert confirmed.status_code == 200, confirmed.text

    unavailable = client.post(f"/api/items/{item_id}/orders", headers=late_buyer["headers"])
    assert unavailable.status_code == 409


def test_orders_are_private_and_transition_roles_are_enforced(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    outsider = make_user(verified=True)
    item_id = make_item(seller=seller)["item"]["item_id"]
    order = client.post(f"/api/items/{item_id}/orders", headers=buyer["headers"]).json()["order"]

    anonymous = client.get("/api/orders")
    outsider_view = client.get(f"/api/orders/{order['order_id']}", headers=outsider["headers"])
    buyer_confirm = client.patch(
        f"/api/orders/{order['order_id']}",
        headers=buyer["headers"],
        json={"status": "CONFIRMED"},
    )

    assert anonymous.status_code == 401
    assert outsider_view.status_code == 404
    assert buyer_confirm.status_code == 403
