from fastapi.testclient import TestClient

from aurey_route_builder.app import app


def test_route_builder_health() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
