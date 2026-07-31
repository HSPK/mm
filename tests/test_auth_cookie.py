from pathlib import Path

from fastapi.testclient import TestClient

from mm.server.app import create_app


def test_auth_cookie_login_restore_and_logout(tmp_path: Path):
    app = create_app(tmp_path / "library.db")
    with TestClient(app) as client:
        setup = client.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "secret", "display_name": "Admin"},
        )
        assert setup.status_code == 200
        token = setup.json()["token"]
        assert client.cookies.get("mm_token") == token
        assert "HttpOnly" in setup.headers["set-cookie"]

        client.cookies.clear()
        restored = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert restored.status_code == 200
        assert client.cookies.get("mm_token") == token
        assert "HttpOnly" in restored.headers["set-cookie"]

        protected_asset = client.get("/api/media/999999/thumbnail")
        assert protected_asset.status_code == 404

        logged_out = client.post("/api/auth/logout")
        assert logged_out.status_code == 200
        assert client.cookies.get("mm_token") is None
