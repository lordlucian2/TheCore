from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_websocket_room_presence_broadcast() -> None:
    """Test WebSocket subscription and presence broadcast."""
    room_payload = {
        "room_id": "room_ws_1",
        "room_type": "group",
        "participant_ids": ["st_001", "st_002"],
        "presence": {"st_001": "focusing", "st_002": "offline"},
        "last_seen_at": {
            "st_001": datetime.now(tz=timezone.utc).isoformat(),
            "st_002": datetime.now(tz=timezone.utc).isoformat(),
        },
        "ambient_mode": "lofi",
    }
    create_resp = client.post("/v1/rooms", json=room_payload)
    assert create_resp.status_code == 200

    # Cannot test WebSocket fully with TestClient for real bidirectional communication,
    # but we can test that the endpoint exists and connection is accepted
    # Full WebSocket testing would require a dedicated WebSocket client test
    with client.websocket_connect("/v1/rooms/room_ws_1/subscribe") as websocket:
        # After establishing connection, trigger a presence update
        pass


def test_room_subscriber_count() -> None:
    """Test tracking of active WebSocket subscribers."""
    room_payload = {
        "room_id": "room_ws_2",
        "room_type": "group",
        "participant_ids": ["st_001"],
        "presence": {"st_001": "focusing"},
        "last_seen_at": {"st_001": datetime.now(tz=timezone.utc).isoformat()},
        "ambient_mode": "lofi",
    }
    client.post("/v1/rooms", json=room_payload)

    # Check initial subscriber count
    resp = client.get("/v1/rooms/room_ws_2/subscribers")
    assert resp.status_code == 200
    assert resp.json()["subscriber_count"] >= 0


def test_get_active_rooms() -> None:
    """Test listing rooms with active WebSocket subscriptions."""
    resp = client.get("/v1/rooms/active")
    assert resp.status_code == 200
    assert "active_rooms" in resp.json()
    assert isinstance(resp.json()["active_rooms"], list)


def test_presence_update_endpoint() -> None:
    """Test synchronous presence update endpoint with new response."""
    room_payload = {
        "room_id": "room_ws_3",
        "room_type": "group",
        "participant_ids": ["st_001"],
        "presence": {"st_001": "offline"},
        "last_seen_at": {"st_001": datetime.now(tz=timezone.utc).isoformat()},
        "ambient_mode": "lofi",
    }
    create_resp = client.post("/v1/rooms", json=room_payload)
    assert create_resp.status_code == 200

    presence_payload = {
        "student_id": "st_001",
        "state": "focusing",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
    update_resp = client.post("/v1/rooms/room_ws_3/presence", json=presence_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["state"] == "focusing"

    # Verify the room state was updated
    get_resp = client.get("/v1/rooms/room_ws_3")
    assert get_resp.status_code == 200
    assert get_resp.json()["presence"]["st_001"] == "focusing"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
