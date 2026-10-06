def test_admin_features_require_dedicated_admin_login(client, make_user):
    admin = make_user(role="ADMIN", verified=True)

    normal_login = client.post(
        "/api/auth/login",
        json={"email": admin["user"]["email"], "password": admin["password"]},
    )
    normal_headers = {"Authorization": f"Bearer {normal_login.json()['access_token']}"}
    normal_admin_queue = client.get("/api/admin/reports", headers=normal_headers)

    admin_login = client.post(
        "/api/admin/login",
        json={"email": admin["user"]["email"], "password": admin["password"]},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    admin_queue = client.get("/api/admin/reports", headers=admin_headers)

    student = make_user(verified=True)
    student_admin_login = client.post(
        "/api/admin/login",
        json={"email": student["user"]["email"], "password": student["password"]},
    )

    assert normal_login.status_code == 200, normal_login.text
    assert normal_login.json()["user"]["role"] == "ADMIN"
    assert normal_login.json()["user"]["admin_session"] is False
    assert normal_admin_queue.status_code == 403
    assert admin_login.status_code == 200, admin_login.text
    assert admin_login.json()["user"]["admin_session"] is True
    assert admin_queue.status_code == 200, admin_queue.text
    assert student_admin_login.status_code == 403


def test_admin_can_list_all_users_with_search_and_pagination(client, make_user):
    admin = make_user(role="ADMIN", verified=True)
    student = make_user(verified=True)
    make_user(verified=False)
    admin_login = client.post(
        "/api/admin/login",
        json={"email": admin["user"]["email"], "password": admin["password"]},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    anonymous = client.get("/api/admin/users")
    forbidden = client.get("/api/admin/users", headers=student["headers"])
    first_page = client.get("/api/admin/users?limit=2&offset=0", headers=admin_headers)
    second_page = client.get("/api/admin/users?limit=2&offset=2", headers=admin_headers)
    searched = client.get(
        f"/api/admin/users?q={student['user']['email']}",
        headers=admin_headers,
    )

    assert anonymous.status_code == 401
    assert forbidden.status_code == 403
    assert first_page.status_code == 200, first_page.text
    assert first_page.json()["total_count"] == 3
    assert len(first_page.json()["users"]) == 2
    assert second_page.status_code == 200, second_page.text
    assert len(second_page.json()["users"]) == 1
    assert first_page.json()["users"][0]["user_id"] != second_page.json()["users"][0]["user_id"]
    assert searched.status_code == 200, searched.text
    assert [person["user_id"] for person in searched.json()["users"]] == [student["user"]["user_id"]]
    assert searched.json()["users"][0]["email"] == student["user"]["email"]


def test_student_can_report_product_and_admin_can_review_it(client, make_user, make_item):
    seller = make_user(verified=True)
    reporter = make_user(verified=True)
    admin = make_user(role="ADMIN", verified=True)
    admin_login = client.post(
        "/api/admin/login",
        json={"email": admin["user"]["email"], "password": admin["password"]},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    item = make_item(seller=seller)["item"]

    submitted = client.post(
        f"/api/items/{item['item_id']}/reports",
        headers=reporter["headers"],
        json={"reason": "The product description appears misleading."},
    )
    assert submitted.status_code == 201, submitted.text
    report = submitted.json()["report"]
    assert report["status"] == "OPEN"
    assert report["item"]["item_id"] == item["item_id"]
    assert report["reporter"]["username"] == reporter["user"]["username"]

    forbidden = client.get("/api/admin/reports", headers=reporter["headers"])
    queue = client.get("/api/admin/reports?status=OPEN", headers=admin_headers)
    assert forbidden.status_code == 403
    assert queue.status_code == 200, queue.text
    assert queue.json()["total_count"] == 1
    assert queue.json()["reports"][0]["report_id"] == report["report_id"]

    updated = client.patch(
        f"/api/admin/reports/{report['report_id']}",
        headers=admin_headers,
        json={"status": "RESOLVED"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["report"]["status"] == "RESOLVED"
    assert updated.json()["report"]["reviewed_by"] == admin["user"]["user_id"]
    assert updated.json()["report"]["resolved_at"] is not None

    admin_notifications = client.get("/api/notifications", headers=admin_headers).json()["notifications"]
    assert any(notification["notification_type"] == "REPORT" for notification in admin_notifications)


def test_admin_can_ban_and_unban_student_posting(client, make_user, make_item):
    admin = make_user(role="ADMIN", verified=True)
    target = make_user(verified=True)
    seller = make_user(verified=True)
    target_item = make_item(seller=target)["item"]
    admin_login = client.post(
        "/api/admin/login",
        json={"email": admin["user"]["email"], "password": admin["password"]},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    search = client.get(
        f"/api/admin/users/search?q={target['user']['username']}",
        headers=admin_headers,
    )
    assert search.status_code == 200, search.text
    assert search.json()["users"][0]["user_id"] == target["user"]["user_id"]

    banned = client.patch(
        f"/api/admin/users/{target['user']['user_id']}/posting-ban",
        headers=admin_headers,
        json={"banned": True, "reason": "Repeated spam listings."},
    )
    assert banned.status_code == 200, banned.text
    assert banned.json()["user"]["posting_banned"] is True

    listing_payload = {
        "name": "Campus notebook",
        "price": 10,
        "category": "Books",
        "condition": "Used - Good",
        "description": "A notebook in good condition for class.",
    }
    blocked_listing = client.post("/api/items", headers=target["headers"], json=listing_payload)
    other_item = make_item(seller=seller)["item"]
    blocked_comment = client.post(
        f"/api/items/{other_item['item_id']}/comments",
        headers=target["headers"],
        json={"comment_text": "A comment from a posting-banned account."},
    )
    blocked_edit = client.put(
        f"/api/listings/{target_item['item_id']}",
        headers=target["headers"],
        json={
            "name": "Campus notebook updated",
            "price": 10,
            "category": "Books",
            "item_condition": "USED_GOOD",
            "description": "A notebook in good condition for class.",
        },
    )
    blocked_upload = client.post(
        f"/api/listings/{target_item['item_id']}/media",
        headers=target["headers"],
        files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0image", "image/jpeg")},
    )
    allowed_purchase = client.post(
        f"/api/items/{other_item['item_id']}/orders",
        headers=target["headers"],
    )
    order_id = allowed_purchase.json()["order"]["order_id"]
    confirmed = client.patch(
        f"/api/orders/{order_id}",
        headers=seller["headers"],
        json={"status": "CONFIRMED"},
    )
    completed = client.patch(
        f"/api/orders/{order_id}",
        headers=seller["headers"],
        json={"status": "COMPLETED"},
    )
    blocked_review = client.put(
        f"/api/items/{other_item['item_id']}/reviews",
        headers=target["headers"],
        json={"rating": 5, "review_text": "A review from a posting-banned account."},
    )
    assert blocked_listing.status_code == 403
    assert blocked_comment.status_code == 403
    assert blocked_edit.status_code == 403
    assert blocked_upload.status_code == 403
    assert allowed_purchase.status_code == 201, allowed_purchase.text
    assert confirmed.status_code == 200, confirmed.text
    assert completed.status_code == 200, completed.text
    assert blocked_review.status_code == 403

    unbanned = client.patch(
        f"/api/admin/users/{target['user']['user_id']}/posting-ban",
        headers=admin_headers,
        json={"banned": False},
    )
    allowed_listing = client.post("/api/items", headers=target["headers"], json=listing_payload)
    assert unbanned.status_code == 200, unbanned.text
    assert unbanned.json()["user"]["posting_banned"] is False
    assert allowed_listing.status_code == 201, allowed_listing.text


def test_reports_reject_empty_reasons_and_are_private(client, make_user, make_item):
    seller = make_user(verified=True)
    reporter = make_user(verified=True)
    other = make_user(verified=True)
    item_id = make_item(seller=seller)["item"]["item_id"]

    empty = client.post(
        f"/api/items/{item_id}/reports",
        headers=reporter["headers"],
        json={"reason": "  "},
    )
    submitted = client.post(
        f"/api/items/{item_id}/reports",
        headers=reporter["headers"],
        json={"reason": "Potentially counterfeit item."},
    )
    anonymous_queue = client.get("/api/admin/reports")
    student_update = client.patch(
        f"/api/admin/reports/{submitted.json()['report']['report_id']}",
        headers=other["headers"],
        json={"status": "RESOLVED"},
    )

    assert empty.status_code == 422
    assert submitted.status_code == 201
    assert anonymous_queue.status_code == 401
    assert student_update.status_code == 403
