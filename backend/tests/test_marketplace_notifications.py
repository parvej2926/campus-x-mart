import pytest
from starlette.websockets import WebSocketDisconnect


def test_message_notifications_are_private_and_can_be_marked_read(client, make_user):
    sender = make_user(verified=True)
    recipient = make_user(verified=True)
    outsider = make_user(verified=True)
    sent = client.post(
        f"/api/messages/{recipient['user']['user_id']}",
        headers=sender["headers"],
        json={"message_text": "Can we meet near the library?"},
    )
    assert sent.status_code == 201, sent.text

    inbox = client.get("/api/notifications", headers=recipient["headers"])
    assert inbox.status_code == 200, inbox.text
    assert inbox.json()["unread_count"] == 1
    notification = inbox.json()["notifications"][0]
    assert notification["notification_type"] == "MESSAGE"
    assert notification["title"] == "New message"
    assert sender["user"]["full_name"] in notification["message"]

    forbidden = client.patch(
        f"/api/notifications/{notification['notification_id']}/read",
        headers=outsider["headers"],
    )
    marked = client.patch(
        f"/api/notifications/{notification['notification_id']}/read",
        headers=recipient["headers"],
    )
    count = client.get("/api/notifications/unread-count", headers=recipient["headers"])

    assert forbidden.status_code == 404
    assert marked.status_code == 200, marked.text
    assert marked.json()["notification"]["is_read"] is True
    assert count.json()["unread_count"] == 0

    client.post(
        f"/api/messages/{recipient['user']['user_id']}",
        headers=sender["headers"],
        json={"message_text": "I am at the north entrance."},
    )
    marked_all = client.post("/api/notifications/read-all", headers=recipient["headers"])
    assert marked_all.status_code == 200, marked_all.text
    assert marked_all.json()["updated_count"] == 1


def test_order_requests_create_seller_notification(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    item = make_item(seller=seller)["item"]

    request = client.post(f"/api/items/{item['item_id']}/orders", headers=buyer["headers"])
    assert request.status_code == 201, request.text

    inbox = client.get("/api/notifications", headers=seller["headers"])
    assert inbox.status_code == 200, inbox.text
    notification = inbox.json()["notifications"][0]
    assert notification["notification_type"] == "ORDER"
    assert item["name"] in notification["message"]
    assert inbox.json()["unread_count"] == 1


def test_admins_receive_notifications_for_order_transactions(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    admin = make_user(role="ADMIN", verified=True)
    admin_login = client.post(
        "/api/admin/login",
        json={"email": admin["user"]["email"], "password": admin["password"]},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    item = make_item(seller=seller)["item"]

    requested = client.post(f"/api/items/{item['item_id']}/orders", headers=buyer["headers"])
    order_id = requested.json()["order"]["order_id"]
    client.patch(
        f"/api/orders/{order_id}",
        headers=seller["headers"],
        json={"status": "CONFIRMED"},
    )
    client.patch(
        f"/api/orders/{order_id}",
        headers=seller["headers"],
        json={"status": "COMPLETED"},
    )

    inbox = client.get("/api/notifications", headers=admin_headers)
    assert inbox.status_code == 200, inbox.text
    transaction_notifications = [
        notification
        for notification in inbox.json()["notifications"]
        if notification["notification_type"] == "ORDER"
    ]
    assert {notification["title"] for notification in transaction_notifications} == {
        "Marketplace transaction started",
        "Marketplace transaction confirmed",
        "Marketplace transaction completed",
    }


def test_new_registration_notifies_admin_in_app_and_over_websocket(client, make_user):
    admin = make_user(role="ADMIN", verified=True)
    admin_login = client.post(
        "/api/admin/login",
        json={"email": admin["user"]["email"], "password": admin["password"]},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    ticket_response = client.post("/api/ws/ticket", headers=admin_headers)
    assert ticket_response.status_code == 200, ticket_response.text

    with client.websocket_connect(
        f"/api/ws/notifications?ticket={ticket_response.json()['ticket']}"
    ) as websocket:
        registered = client.post(
            "/api/auth/register",
            json={
                "username": "new_student",
                "full_name": "New Student",
                "email": "new-student@example.com",
                "password": "Password123!",
            },
        )
        assert registered.status_code == 201, registered.text
        event = websocket.receive_json()

    assert event["type"] == "notification"
    assert event["notification"]["notification_type"] == "USER"
    assert event["notification"]["title"] == "New user registered"
    assert "New Student" in event["notification"]["message"]
    inbox = client.get("/api/notifications", headers=admin_headers)
    assert any(
        notification["notification_type"] == "USER"
        for notification in inbox.json()["notifications"]
    )


def test_notifications_are_delivered_over_single_use_ticket_websocket(client, make_user):
    sender = make_user(verified=True)
    recipient = make_user(verified=True)
    ticket_response = client.post("/api/ws/ticket", headers=recipient["headers"])
    assert ticket_response.status_code == 200, ticket_response.text
    ticket = ticket_response.json()["ticket"]

    with client.websocket_connect(f"/api/ws/notifications?ticket={ticket}") as websocket:
        sent = client.post(
            f"/api/messages/{recipient['user']['user_id']}",
            headers=sender["headers"],
            json={"message_text": "The book is ready for pickup."},
        )
        assert sent.status_code == 201, sent.text
        event = websocket.receive_json()
        assert event["type"] == "notification"
        assert event["notification"]["notification_type"] == "MESSAGE"

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/ws/notifications?ticket={ticket}"):
            pass
