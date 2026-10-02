def test_location_directory_and_product_map_details(client, make_user):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)

    anonymous = client.get("/api/locations")
    assert anonymous.status_code == 401

    created_location = client.post(
        "/api/locations",
        headers=seller["headers"],
        json={
            "location_name": "North Gate",
            "campus_name": "Campus A",
            "address": "North entrance",
            "latitude": 23.7806,
            "longitude": 90.4070,
        },
    )
    assert created_location.status_code == 200, created_location.text
    location = created_location.json()["location"]

    directory = client.get("/api/locations", headers=buyer["headers"])
    assert directory.status_code == 200, directory.text
    assert directory.json()["locations"][0]["location_id"] == location["location_id"]

    listed = client.post(
        "/api/listings",
        headers=seller["headers"],
        json={
            "name": "Campus umbrella",
            "description": "A sturdy umbrella, used only a few times.",
            "price": 12,
            "category": "Accessories",
            "item_condition": "USED_GOOD",
            "status": "AVAILABLE",
            "location_id": location["location_id"],
        },
    )
    assert listed.status_code == 201, listed.text
    assert listed.json()["item"]["location_id"] == location["location_id"]

    products = client.get("/api/items", headers=buyer["headers"])
    assert products.status_code == 200, products.text
    product = products.json()["items"][0]
    assert product["location"] == {
        "location_id": location["location_id"],
        "location_name": "North Gate",
        "campus_name": "Campus A",
        "address": "North entrance",
        "latitude": 23.7806,
        "longitude": 90.407,
    }


def test_listing_rejects_unknown_location(client, make_user):
    seller = make_user(verified=True)
    response = client.post(
        "/api/listings",
        headers=seller["headers"],
        json={
            "name": "Campus umbrella",
            "description": "A sturdy umbrella, used only a few times.",
            "price": 12,
            "category": "Accessories",
            "item_condition": "USED_GOOD",
            "location_id": 999999,
        },
    )
    assert response.status_code == 404
