from main import create_verification_code_for_user


def _user_id(client, headers):
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["user_id"]


def test_send_verification_rejects_recent_resend(client, auth_headers):
    headers = auth_headers(email="cooldown@example.com")
    user_id = _user_id(client, headers)
    create_verification_code_for_user(user_id, "EMAIL", "cooldown@example.com")

    response = client.post(
        "/api/auth/send-verification",
        headers=headers,
        json={"channel": "EMAIL"},
    )

    assert response.status_code == 429
    assert "60 seconds" in response.json()["detail"]


def test_verify_user_locks_code_after_five_failed_attempts(client, auth_headers):
    headers = auth_headers(email="attempts@example.com")
    user_id = _user_id(client, headers)
    correct_code = create_verification_code_for_user(user_id, "EMAIL", "attempts@example.com")
    invalid_code = "000000" if correct_code != "000000" else "000001"

    for _ in range(4):
        response = client.post(
            "/api/auth/verify",
            headers=headers,
            json={"channel": "EMAIL", "code": invalid_code},
        )
        assert response.status_code == 400

    locked = client.post(
        "/api/auth/verify",
        headers=headers,
        json={"channel": "EMAIL", "code": invalid_code},
    )

    assert locked.status_code == 429
    assert "Too many failed attempts" in locked.json()["detail"]
