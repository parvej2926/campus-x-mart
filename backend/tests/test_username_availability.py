def test_username_availability_reports_available_taken_and_invalid_names(client, make_user):
    existing = make_user(verified=True)
    username = existing["user"]["username"]

    available = client.get("/api/auth/check-username", params={"username": "available_student_87"})
    taken = client.get("/api/auth/check-username", params={"username": username.upper()})
    invalid = client.get("/api/auth/check-username", params={"username": "ab"})

    assert available.status_code == 200
    assert available.json()["available"] is True
    assert taken.status_code == 200
    assert taken.json()["available"] is False
    assert "already taken" in taken.json()["message"].lower()
    assert invalid.status_code == 200
    assert invalid.json()["available"] is False
