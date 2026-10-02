def test_products_filter_sort_and_paginate_server_side(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    alpha = make_item(seller=seller, name="Book Alpha", price=10, category="Books", condition="New")["item"]
    beta = make_item(seller=seller, name="Book Beta", price=20, category="Books", condition="Used - Good")["item"]
    calculator = make_item(seller=seller, name="Calculator", price=30, category="Electronics", condition="Used - Excellent")["item"]

    filtered = client.get(
        "/api/items",
        headers=buyer["headers"],
        params={
            "q": "Book",
            "category": "Books",
            "condition": "NEW",
            "min_price": 5,
            "max_price": 15,
            "sort": "price_asc",
            "limit": 1,
            "offset": 0,
        },
    )
    assert filtered.status_code == 200, filtered.text
    assert filtered.json()["total_count"] == 1
    assert [item["item_id"] for item in filtered.json()["items"]] == [alpha["item_id"]]

    first_page = client.get("/api/items", headers=buyer["headers"], params={"sort": "price_asc", "limit": 1, "offset": 0})
    second_page = client.get("/api/items", headers=buyer["headers"], params={"sort": "price_asc", "limit": 1, "offset": 1})
    assert first_page.status_code == 200, first_page.text
    assert second_page.status_code == 200, second_page.text
    assert first_page.json()["total_count"] == 3
    assert first_page.json()["items"][0]["item_id"] == alpha["item_id"]
    assert second_page.json()["items"][0]["item_id"] == beta["item_id"]

    hyphenated_sort = client.get("/api/items", headers=buyer["headers"], params={"sort": "price-asc", "limit": 2, "offset": 0})
    assert hyphenated_sort.status_code == 200, hyphenated_sort.text
    assert [item["item_id"] for item in hyphenated_sort.json()["items"]] == [alpha["item_id"], beta["item_id"]]

    literal_percent = client.get("/api/items", headers=buyer["headers"], params={"q": "%"})
    assert literal_percent.status_code == 200, literal_percent.text
    assert literal_percent.json()["total_count"] == 0
    assert calculator["item_id"] != alpha["item_id"]
