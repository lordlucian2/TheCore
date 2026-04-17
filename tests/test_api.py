from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_create_and_list_event() -> None:
    payload = {
        "student_id": "st_001",
        "kind": "xp",
        "value": 50,
        "started_at": datetime.now(tz=timezone.utc).isoformat(),
        "ended_at": (datetime.now(tz=timezone.utc) + timedelta(minutes=5)).isoformat(),
        "nonce": "api-1",
    }
    response = client.post("/v1/events", json=payload)
    assert response.status_code == 200
    assert "signature" in response.json()

    pending = client.get("/v1/events/pending/st_001")
    assert pending.status_code == 200
    assert len(pending.json()) >= 1


def test_award_xp_and_sync_batch() -> None:
    session_payload = {
        "session_id": "session-1",
        "student_id": "st_001",
        "room_type": "solo",
        "started_at": datetime.now(tz=timezone.utc).isoformat(),
        "ended_at": (datetime.now(tz=timezone.utc) + timedelta(minutes=25)).isoformat(),
        "completed_pomodoros": 1,
        "is_first_session_of_day": True,
        "bonus_xp": 0,
    }
    xp_resp = client.post("/v1/xp/award", json=session_payload)
    assert xp_resp.status_code == 200
    assert xp_resp.json()["xp_awarded"] > 0

    event_payload = {
        "student_id": "st_001",
        "kind": "pomodoro",
        "value": 1,
        "started_at": datetime.now(tz=timezone.utc).isoformat(),
        "ended_at": (datetime.now(tz=timezone.utc) + timedelta(minutes=1)).isoformat(),
        "nonce": "api-2",
    }
    event_response = client.post("/v1/events", json=event_payload)
    assert event_response.status_code == 200
    signature = event_response.json()["signature"]

    batch = {
        "events": [event_payload],
        "signatures": [signature],
    }
    sync_resp = client.post("/v1/sync/batch", json=batch)
    assert sync_resp.status_code == 200
    assert sync_resp.json()["count"] == 1


def test_vault_and_ai_endpoints() -> None:
    resource_payload = {
        "resource_id": "res_api_1",
        "author_id": "st_001",
        "title": "Sample Notes",
        "subject": "Math",
        "description": "A compact revision note.",
        "tags": ["math", "revision"],
        "content_url": "https://example.com",
        "visibility": "public",
    }
    resource_resp = client.post("/v1/vault/resources", json=resource_payload)
    assert resource_resp.status_code == 200
    assert resource_resp.json()["resource_id"] == "res_api_1"

    list_resp = client.get("/v1/vault/resources", params={"author_id": "st_001"})
    assert list_resp.status_code == 200
    assert any(item["resource_id"] == "res_api_1" for item in list_resp.json())

    vote_resp = client.post("/v1/vault/resources/res_api_1/vote", params={"upvote": True})
    assert vote_resp.status_code == 200
    assert vote_resp.json()["score"] == 1

    ai_payload = {
        "query_id": "q_api_1",
        "student_id": "st_001",
        "subject": "Biology",
        "prompt": "Explain photosynthesis.",
        "mode": "hint",
        "context": {},
    }
    ai_resp = client.post("/v1/ai/query", json=ai_payload)
    assert ai_resp.status_code == 200
    assert ai_resp.json()["query_id"] == "q_api_1"
    assert "response" in ai_resp.json()

    query_list = client.get("/v1/ai/queries/st_001")
    assert query_list.status_code == 200
    assert len(query_list.json()) >= 1

    responses = client.get("/v1/ai/responses/q_api_1")
    assert responses.status_code == 200
    assert len(responses.json()) >= 1


def test_room_endpoints() -> None:
    room_payload = {
        "room_id": "room_api_1",
        "room_type": "group",
        "participant_ids": ["st_001"],
        "presence": {"st_001": "focusing"},
        "last_seen_at": {"st_001": datetime.now(tz=timezone.utc).isoformat()},
        "ambient_mode": "lofi",
    }
    create_resp = client.post("/v1/rooms", json=room_payload)
    assert create_resp.status_code == 200
    assert create_resp.json()["room_id"] == "room_api_1"

    get_resp = client.get("/v1/rooms/room_api_1")
    assert get_resp.status_code == 200
    assert get_resp.json()["room_id"] == "room_api_1"

    presence_payload = {
        "student_id": "st_001",
        "state": "break",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
    update_resp = client.post("/v1/rooms/room_api_1/presence", json=presence_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["state"] == "break"


def test_student_endpoints_and_room_ghosts() -> None:
    student_payload = {
        "student_id": "st_002",
        "display_name": "Nia",
        "school": "Southbridge High",
    }
    create_student_resp = client.post("/v1/students", json=student_payload)
    assert create_student_resp.status_code == 200
    assert create_student_resp.json()["student_id"] == "st_002"

    get_student_resp = client.get("/v1/students/st_002")
    assert get_student_resp.status_code == 200
    assert get_student_resp.json()["display_name"] == "Nia"

    list_students_resp = client.get("/v1/students")
    assert list_students_resp.status_code == 200
    assert any(item["student_id"] == "st_002" for item in list_students_resp.json())

    event_payload = {
        "student_id": "st_002",
        "kind": "pomodoro",
        "value": 1,
        "started_at": datetime.now(tz=timezone.utc).isoformat(),
        "ended_at": (datetime.now(tz=timezone.utc) + timedelta(minutes=1)).isoformat(),
        "nonce": "api-ghost-1",
    }
    event_response = client.post("/v1/events", json=event_payload)
    assert event_response.status_code == 200

    room_payload = {
        "room_id": "room_api_ghosts",
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

    ghosts_resp = client.get("/v1/rooms/room_api_ghosts/ghosts")
    assert ghosts_resp.status_code == 200
    ghosts = ghosts_resp.json()
    assert any(ghost["student_id"] == "st_002" for ghost in ghosts)
