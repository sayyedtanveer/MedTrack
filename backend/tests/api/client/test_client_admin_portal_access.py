import uuid


def _admin_headers(token_headers: dict) -> dict:
    return {
        "Authorization": token_headers["Authorization"],
        "X-Tenant-ID": token_headers["X-Tenant-ID"],
    }


async def test_admin_can_create_and_reset_client_portal_user(async_client, token_headers):
    headers = _admin_headers(token_headers)
    email = f"client-admin-{uuid.uuid4().hex[:8]}@example.com"

    client_resp = await async_client.post(
        "/api/v1/sales/clients",
        json={
            "code": f"CLI-{uuid.uuid4().hex[:8]}",
            "name": "Portal Client",
            "email": email,
            "credit_limit": 50000,
            "payment_terms_days": 30,
        },
        headers=headers,
    )
    assert client_resp.status_code == 201
    client_id = client_resp.json()["id"]

    user_resp = await async_client.post(
        "/api/v1/users",
        json={
            "email": email,
            "first_name": "Portal",
            "last_name": "Client",
            "role": "client",
            "is_active": True,
            "client_id": client_id,
        },
        headers=headers,
    )
    assert user_resp.status_code == 201
    user_body = user_resp.json()
    assert user_body["client_id"] == client_id
    assert user_body["temporary_password"]

    login_resp = await async_client.post(
        "/api/v1/client/auth/login",
        json={
            "email": email,
            "password": user_body["temporary_password"],
            "tenant_id": token_headers["X-Tenant-ID"],
        },
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["client_id"] == client_id

    reset_resp = await async_client.post(
        f"/api/v1/users/{user_body['id']}/temporary-password",
        headers=headers,
    )
    assert reset_resp.status_code == 200
    reset_body = reset_resp.json()
    assert reset_body["client_id"] == client_id
    assert reset_body["temporary_password"] != user_body["temporary_password"]

    refreshed_login_resp = await async_client.post(
        "/api/v1/client/auth/login",
        json={
            "email": email,
            "password": reset_body["temporary_password"],
            "tenant_id": token_headers["X-Tenant-ID"],
        },
    )
    assert refreshed_login_resp.status_code == 200


async def test_client_create_rejects_email_already_used_by_user(async_client, token_headers):
    headers = _admin_headers(token_headers)
    email = f"existing-user-{uuid.uuid4().hex[:8]}@example.com"

    user_resp = await async_client.post(
        "/api/v1/users",
        json={
            "email": email,
            "first_name": "Existing",
            "last_name": "User",
            "role": "operator",
            "is_active": True,
        },
        headers=headers,
    )
    assert user_resp.status_code == 201

    client_resp = await async_client.post(
        "/api/v1/sales/clients",
        json={
            "code": f"CLI-{uuid.uuid4().hex[:8]}",
            "name": "Duplicate Email Client",
            "email": email,
            "credit_limit": 50000,
            "payment_terms_days": 30,
        },
        headers=headers,
    )
    assert client_resp.status_code == 409
    assert "Email already exists as a user login" in client_resp.json()["detail"]
