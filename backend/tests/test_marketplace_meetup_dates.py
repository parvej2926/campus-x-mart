from datetime import date, timedelta


def test_order_participants_can_set_and_change_meetup_date(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    item_id = make_item(seller=seller)["item"]["item_id"]
    order = client.post(f"/api/items/{item_id}/orders", headers=buyer["headers"]).json()["order"]
    url = f"/api/orders/{order['order_id']}/meetup-date"
    first_date = (date.today() + timedelta(days=3)).isoformat()
    second_date = (date.today() + timedelta(days=4)).isoformat()

    set_by_buyer = client.patch(url, headers=buyer["headers"], json={"meetup_date": first_date})
    set_by_seller = client.patch(url, headers=seller["headers"], json={"meetup_date": second_date})

    assert set_by_buyer.status_code == 200, set_by_buyer.text
    assert set_by_buyer.json()["order"]["meetup_date"] == first_date
    assert set_by_seller.status_code == 200, set_by_seller.text
    assert set_by_seller.json()["order"]["meetup_date"] == second_date
    assert client.get(f"/api/orders/{order['order_id']}", headers=buyer["headers"]).json()["order"]["meetup_date"] == second_date


def test_meetup_date_rejects_past_dates_and_nonparticipants(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    outsider = make_user(verified=True)
    item_id = make_item(seller=seller)["item"]["item_id"]
    order = client.post(f"/api/items/{item_id}/orders", headers=buyer["headers"]).json()["order"]
    url = f"/api/orders/{order['order_id']}/meetup-date"

    past = client.patch(url, headers=buyer["headers"], json={"meetup_date": (date.today() - timedelta(days=1)).isoformat()})
    private = client.patch(url, headers=outsider["headers"], json={"meetup_date": (date.today() + timedelta(days=1)).isoformat()})

    assert past.status_code == 422
    assert private.status_code == 404


def test_completed_order_meetup_date_is_immutable(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    item_id = make_item(seller=seller)["item"]["item_id"]
    order = client.post(f"/api/items/{item_id}/orders", headers=buyer["headers"]).json()["order"]

    for status in ("CONFIRMED", "COMPLETED"):
        response = client.patch(f"/api/orders/{order['order_id']}", headers=seller["headers"], json={"status": status})
        assert response.status_code == 200, response.text

    closed = client.patch(
        f"/api/orders/{order['order_id']}/meetup-date",
        headers=buyer["headers"],
        json={"meetup_date": (date.today() + timedelta(days=2)).isoformat()},
    )
    assert closed.status_code == 409
