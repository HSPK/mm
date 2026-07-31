from pathlib import Path

from fastapi.testclient import TestClient

from mm.server.app import create_app


def test_music_catalog_is_not_exposed_under_organizer(tmp_path: Path):
    with TestClient(create_app(tmp_path / "library.db")) as client:
        response = client.get("/api/music/albums")
        assert response.status_code == 200
        assert response.json()["albums"] == []

        assert client.get("/api/organizer/music/albums").status_code == 404
        assert client.get("/api/organizer/music/tracks").status_code == 404
        assert client.get("/api/organizer/music/artists").status_code == 404
