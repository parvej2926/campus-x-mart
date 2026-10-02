import pytest

from main import get_connection


LISTING_PAYLOAD = {
    "name": "Campus umbrella",
    "description": "A sturdy umbrella in good condition.",
    "price": 12,
    "category": "Accessories",
    "item_condition": "USED_GOOD",
}
ITEM_PAYLOAD = {
    "name": "Campus umbrella",
    "description": "A sturdy umbrella in good condition.",
    "price": 12,
    "category": "Accessories",
    "condition": "USED_GOOD",
}


def _set_verification(user_id, *, email=False, phone=False):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET email_verified = %s, phone_verified = %s WHERE user_id = %s",
                (email, phone, user_id),
            )
        connection.commit()
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("path", "payload"),
    [("/api/listings", LISTING_PAYLOAD), ("/api/items", ITEM_PAYLOAD)],
)
def test_unverified_user_cannot_create_listing_through_either_api(client, make_user, path, payload):
    user = make_user()

    response = client.post(path, headers=user["headers"], json=payload)

    assert response.status_code == 403
    assert "Verify your email or phone" in response.json()["detail"]


def test_phone_verification_alone_allows_listing(client, make_user):
    user = make_user()
    _set_verification(user["user"]["user_id"], phone=True)

    response = client.post("/api/listings", headers=user["headers"], json=LISTING_PAYLOAD)

    assert response.status_code == 201, response.text


def test_unverified_user_cannot_edit_or_upload_listing(client, make_user, make_item):
    seller = make_user(verified=True)
    item = make_item(seller=seller)["item"]
    _set_verification(seller["user"]["user_id"])

    edited = client.put(
        f"/api/listings/{item['item_id']}",
        headers=seller["headers"],
        json=LISTING_PAYLOAD,
    )
    uploaded = client.post(
        f"/api/listings/{item['item_id']}/media",
        headers=seller["headers"],
        files={"file": ("photo.jpg", b"image", "image/jpeg")},
    )

    assert edited.status_code == 403
    assert uploaded.status_code == 403


def test_unverified_user_cannot_request_order(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user()
    item = make_item(seller=seller)["item"]

    response = client.post(
        f"/api/items/{item['item_id']}/orders",
        headers=buyer["headers"],
    )

    assert response.status_code == 403
    assert "Verify your email or phone" in response.json()["detail"]


def test_email_verification_alone_allows_order(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user()
    _set_verification(buyer["user"]["user_id"], email=True)
    item = make_item(seller=seller)["item"]

    response = client.post(
        f"/api/items/{item['item_id']}/orders",
        headers=buyer["headers"],
    )

    assert response.status_code == 201, response.text