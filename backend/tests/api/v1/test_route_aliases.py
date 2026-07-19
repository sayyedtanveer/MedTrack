from fastapi.testclient import TestClient

from backend.app.main import app


def test_trailing_slash_variants_are_supported_for_notifications_and_number_series():
    client = TestClient(app)

    for path in [
        "/api/v1/notifications/",
        "/api/v1/settings/number-series/",
    ]:
        response = client.get(path, follow_redirects=False)

        assert response.status_code != 307, f"{path} should not redirect to a trailing-slash variant"
        assert response.status_code in {200, 401, 403}, f"Unexpected status for {path}: {response.status_code}"
