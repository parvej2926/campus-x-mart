from auth_sessions import ACCESS_COOKIE, CSRF_COOKIE, REFRESH_COOKIE, rotate_session


def test_login_sets_http_only_cookie_session_and_requires_csrf_for_writes(client, make_user):
    account = make_user(verified=True)
    response = client.post(
        "/api/auth/login",
        json={"email": account["user"]["email"], "password": account["password"]},
    )

    assert response.status_code == 200, response.text
    assert "access_token" not in response.json()
    set_cookies = response.headers.get_list("set-cookie")
    assert any(cookie.startswith(f"{ACCESS_COOKIE}=") and "HttpOnly" in cookie for cookie in set_cookies)
    assert any(cookie.startswith(f"{REFRESH_COOKIE}=") and "HttpOnly" in cookie for cookie in set_cookies)
    assert any(cookie.startswith(f"{CSRF_COOKIE}=") and "HttpOnly" not in cookie for cookie in set_cookies)
    assert client.get("/api/auth/me").json()["user"]["user_id"] == account["user"]["user_id"]

    denied = client.post("/api/ws/ticket")
    assert denied.status_code == 403

    csrf_header = {"X-CSRF-Token": client.cookies.get(CSRF_COOKIE)}
    allowed = client.post("/api/ws/ticket", headers=csrf_header)
    assert allowed.status_code == 200, allowed.text


def test_refresh_rotates_token_and_logout_revokes_cookie_session(client, make_user):
    account = make_user()
    login = client.post(
        "/api/auth/login",
        json={"email": account["user"]["email"], "password": account["password"]},
    )
    assert login.status_code == 200, login.text
    old_access_token = client.cookies.get(ACCESS_COOKIE)
    old_refresh_token = client.cookies.get(REFRESH_COOKIE)
    csrf_header = {"X-CSRF-Token": client.cookies.get(CSRF_COOKIE)}

    refreshed = client.post("/api/auth/refresh", headers=csrf_header)
    assert refreshed.status_code == 200, refreshed.text
    assert client.cookies.get(REFRESH_COOKIE) != old_refresh_token
    assert rotate_session(old_refresh_token) is None
    assert client.get("/api/auth/me").status_code == 200

    logged_out = client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": client.cookies.get(CSRF_COOKIE)},
    )
    assert logged_out.status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert client.get(
        "/api/auth/me",
        cookies={ACCESS_COOKIE: old_access_token},
    ).status_code == 401


def test_unsafe_cross_origin_requests_are_rejected(client):
    response = client.post(
        "/api/auth/login",
        headers={"Origin": "https://attacker.example"},
        json={"email": "nobody@example.com", "password": "Password123!"},
    )

    assert response.status_code == 403
    assert response.headers.get("X-Request-ID")


def test_api_clients_can_request_short_lived_bearer_tokens(client, make_user):
    account = make_user()
    response = client.post(
        "/api/auth/token",
        json={"email": account["user"]["email"], "password": account["password"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["token_type"] == "bearer"
    assert client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {response.json()['access_token']}"},
    ).status_code == 200
    assert not response.headers.get_list("set-cookie")
