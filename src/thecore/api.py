from __future__ import annotations

from datetime import datetime
from dataclasses import asdict
from typing import List
import json
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from .ai import AIQuery, AIResponse, AIResponseMode, ClutchAI
from .engine import StudyEvent, StudentProfile, SyncBatch
from .room import PresenceState, RoomTimer, StudyRoom
from .service import TheCoreService
from .session import RoomType, StudySession
from .storage import SQLiteAIStore, SQLiteEventStore, SQLiteRoomStore, SQLiteStudentStore, SQLiteVaultStore
from .vault import VaultResource
from .websocket import manager as ws_manager
from .observability import metrics


def _validate_event_kind(kind: str) -> str:
    if kind not in {"xp", "pomodoro"}:
        raise ValueError("kind must be either 'xp' or 'pomodoro'")
    return kind


class StudyEventPayload(BaseModel):
    student_id: str
    kind: str
    value: int
    started_at: datetime
    ended_at: datetime
    nonce: str

    _validate_kind = validator("kind", allow_reuse=True)(_validate_event_kind)

    @validator("value")
    def positive_value(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("value must be positive")
        return value

    def to_event(self) -> StudyEvent:
        return StudyEvent(
            student_id=self.student_id,
            kind=self.kind,
            value=self.value,
            started_at=self.started_at,
            ended_at=self.ended_at,
            nonce=self.nonce,
        )


class SyncBatchPayload(BaseModel):
    events: List[StudyEventPayload]
    signatures: List[str]

    def to_batch(self) -> SyncBatch:
        return SyncBatch(
            student_id=None,
            events=[event.to_event() for event in self.events],
            signatures=self.signatures,
        )


class StudySessionPayload(BaseModel):
    session_id: str
    student_id: str
    room_type: RoomType
    started_at: datetime
    ended_at: datetime
    completed_pomodoros: int = 0
    is_first_session_of_day: bool = False
    bonus_xp: int = 0

    @validator("completed_pomodoros")
    def non_negative_pomodoros(cls, value: int) -> int:
        if value < 0:
            raise ValueError("completed_pomodoros must be non-negative")
        return value

    def to_session(self) -> StudySession:
        return StudySession(
            session_id=self.session_id,
            student_id=self.student_id,
            room_type=self.room_type,
            started_at=self.started_at,
            ended_at=self.ended_at,
            completed_pomodoros=self.completed_pomodoros,
            is_first_session_of_day=self.is_first_session_of_day,
            bonus_xp=self.bonus_xp,
        )


class VaultResourcePayload(BaseModel):
    resource_id: str
    author_id: str
    title: str
    subject: str
    description: str
    tags: List[str] = Field(default_factory=list)
    content_url: str | None = None
    visibility: str = "public"

    def to_resource(self) -> VaultResource:
        return VaultResource(
            resource_id=self.resource_id,
            author_id=self.author_id,
            title=self.title,
            subject=self.subject,
            description=self.description,
            tags=self.tags,
            content_url=self.content_url,
            visibility=self.visibility,
        )


class AIQueryPayload(BaseModel):
    query_id: str
    student_id: str
    subject: str
    prompt: str
    mode: AIResponseMode
    context: dict[str, str] = Field(default_factory=dict)

    def to_query(self) -> AIQuery:
        return AIQuery(
            query_id=self.query_id,
            student_id=self.student_id,
            subject=self.subject,
            prompt=self.prompt,
            mode=self.mode,
            context=self.context,
        )


class RoomTimerPayload(BaseModel):
    cycle_type: str
    duration_seconds: int
    started_at: datetime
    last_sync_at: datetime | None = None
    paused: bool = False

    def to_timer(self) -> RoomTimer:
        return RoomTimer(
            cycle_type=self.cycle_type,
            duration_seconds=self.duration_seconds,
            started_at=self.started_at,
            last_sync_at=self.last_sync_at,
            paused=self.paused,
        )

    @classmethod
    def from_timer(cls, timer: RoomTimer) -> "RoomTimerPayload":
        return cls(
            cycle_type=timer.cycle_type,
            duration_seconds=timer.duration_seconds,
            started_at=timer.started_at,
            last_sync_at=timer.last_sync_at,
            paused=timer.paused,
        )


class StudyRoomPayload(BaseModel):
    room_id: str
    room_type: RoomType
    participant_ids: List[str] = Field(default_factory=list)
    presence: dict[str, PresenceState] = Field(default_factory=dict)
    last_seen_at: dict[str, datetime] = Field(default_factory=dict)
    ambient_mode: str = "lofi"
    timer: RoomTimerPayload | None = None

    def to_room(self) -> StudyRoom:
        return StudyRoom(
            room_id=self.room_id,
            room_type=self.room_type,
            participant_ids=set(self.participant_ids),
            presence=self.presence,
            last_seen_at=self.last_seen_at,
            ambient_mode=self.ambient_mode,
            timer=self.timer.to_timer() if self.timer else None,
        )

    @classmethod
    def from_room(cls, room: StudyRoom) -> "StudyRoomPayload":
        return cls(
            room_id=room.room_id,
            room_type=room.room_type,
            participant_ids=list(room.participant_ids),
            presence=room.presence,
            last_seen_at=room.last_seen_at,
            ambient_mode=room.ambient_mode,
            timer=RoomTimerPayload.from_timer(room.timer) if room.timer else None,
        )


class RoomPresencePayload(BaseModel):
    student_id: str
    state: PresenceState
    timestamp: datetime


class RoomSubscriberPayload(BaseModel):
    room_id: str
    subscriber_count: int


class StudentProfilePayload(BaseModel):
    student_id: str
    display_name: str
    school: str

    def to_profile(self) -> StudentProfile:
        return StudentProfile(
            student_id=self.student_id,
            display_name=self.display_name,
            school=self.school,
        )


class StudyGhostPayload(BaseModel):
    student_id: str
    display_name: str
    last_seen_at: datetime
    summary: str


class AuthPayload(BaseModel):
    display_name: str
    school: str


class AuthResponse(BaseModel):
    student_id: str
    display_name: str
    school: str


app = FastAPI(title="TheCore API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_event_store = SQLiteEventStore()
_vault_store = SQLiteVaultStore()
_ai_store = SQLiteAIStore()
_room_store = SQLiteRoomStore()
_student_store = SQLiteStudentStore()
_service = TheCoreService.from_store(
    _event_store,
    vault_store=_vault_store,
    ai_store=_ai_store,
    room_store=_room_store,
    student_store=_student_store,
)
_ai = ClutchAI()


@app.post("/v1/events")
def create_event(payload: StudyEventPayload) -> dict[str, str]:
    event = payload.to_event()
    signature = _service.record_event(event)
    return {"signature": signature}


@app.get("/v1/events/pending/{student_id}")
def pending_events(student_id: str) -> List[StudyEventPayload]:
    pending = _service.engine.pending_events(student_id)
    return [StudyEventPayload(**asdict(event)) for event in pending]


@app.post("/v1/sync/batch")
def sync_batch(payload: SyncBatchPayload) -> dict[str, int]:
    batch = payload.to_batch()
    try:
        return _service.acknowledge_batch(batch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/sessions/start")
def start_session(payload: StudySessionPayload) -> dict[str, str]:
    return {
        "session_id": payload.session_id,
        "status": "started",
        "room_type": payload.room_type.value,
    }


@app.post("/v1/xp/award")
def award_xp(payload: StudySessionPayload) -> dict[str, int]:
    session = payload.to_session()
    xp = _service.engine.session_xp(session)
    return {"xp_awarded": xp}


@app.post("/v1/vault/resources")
def create_vault_resource(payload: VaultResourcePayload) -> dict[str, str]:
    resource = payload.to_resource()
    _service.record_resource(resource)
    return {"resource_id": resource.resource_id}


@app.post("/v1/vault/resources/{resource_id}/vote")
def vote_vault_resource(resource_id: str, upvote: bool = True) -> dict[str, int]:
    score = _service.vote_resource(resource_id, upvote=upvote)
    return {"score": score}


@app.get("/v1/vault/resources")
def list_vault_resources(author_id: str | None = None, subject: str | None = None) -> List[VaultResourcePayload]:
    resources = _service.load_resources(author_id=author_id, subject=subject)
    return [VaultResourcePayload(**asdict(resource)) for resource in resources]


@app.post("/v1/rooms")
def create_room(payload: StudyRoomPayload) -> dict[str, str]:
    room = payload.to_room()
    _service.create_room(room)
    return {"room_id": room.room_id}


@app.get("/v1/rooms/active")
def get_active_rooms() -> dict[str, list[str]]:
    """Get all rooms with active WebSocket subscriptions."""
    rooms = ws_manager.get_active_rooms()
    return {"active_rooms": rooms}


@app.get("/v1/rooms/{room_id}")
def get_room(room_id: str) -> StudyRoomPayload:
    room = _service.load_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    return StudyRoomPayload.from_room(room)


@app.post("/v1/rooms/{room_id}/presence")
async def update_room_presence(room_id: str, payload: RoomPresencePayload) -> dict[str, str]:
    room = _service.load_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    room.update_presence(payload.student_id, payload.state, payload.timestamp)
    _service.update_room(room)
    
    # Broadcast presence update to all WebSocket subscribers
    await ws_manager.broadcast(
        room_id,
        {
            "type": "presence_update",
            "room_id": room_id,
            "student_id": payload.student_id,
            "state": payload.state.value,
            "timestamp": payload.timestamp.isoformat(),
        },
    )
    
    return {"room_id": room.room_id, "student_id": payload.student_id, "state": payload.state.value}


@app.websocket("/v1/rooms/{room_id}/subscribe")
async def websocket_subscribe(websocket: WebSocket, room_id: str) -> None:
    """Subscribe to real-time presence updates for a room."""
    await ws_manager.connect(room_id, websocket)
    try:
        while True:
            # Keep connection open and listen for client messages (optional)
            data = await websocket.receive_text()
            # Could implement client commands here if needed
    except WebSocketDisconnect:
        await ws_manager.disconnect(room_id, websocket)


@app.get("/v1/rooms/{room_id}/subscribers")
def get_room_subscribers(room_id: str) -> RoomSubscriberPayload:
    """Get the number of active WebSocket subscribers for a room."""
    count = ws_manager.get_room_subscriber_count(room_id)
    return RoomSubscriberPayload(room_id=room_id, subscriber_count=count)


@app.post("/v1/students")
def create_student(payload: StudentProfilePayload) -> dict[str, str]:
    profile = payload.to_profile()
    _service.record_student(profile)
    return {"student_id": profile.student_id}


@app.post("/v1/auth/login", response_model=AuthResponse)
def auth_login(payload: AuthPayload) -> AuthResponse:
    students = _service.load_student()
    for student in students:
        if student.display_name.lower() == payload.display_name.lower() and student.school.lower() == payload.school.lower():
            return AuthResponse(
                student_id=student.student_id,
                display_name=student.display_name,
                school=student.school,
            )

    new_id = f"st_{uuid4().hex[:8]}"
    profile = StudentProfile(
        student_id=new_id,
        display_name=payload.display_name,
        school=payload.school,
    )
    _service.record_student(profile)
    return AuthResponse(
        student_id=profile.student_id,
        display_name=profile.display_name,
        school=profile.school,
    )


@app.get("/v1/students/{student_id}")
def get_student(student_id: str) -> StudentProfilePayload:
    students = _service.load_student(student_id)
    if not students:
        raise HTTPException(status_code=404, detail="student not found")
    profile = students[0]
    return StudentProfilePayload(**asdict(profile))


@app.get("/v1/students")
def list_students() -> List[StudentProfilePayload]:
    profiles = _service.load_student()
    return [StudentProfilePayload(**asdict(profile)) for profile in profiles]


@app.get("/v1/rooms/{room_id}/ghosts")
def get_room_ghosts(room_id: str) -> List[StudyGhostPayload]:
    room = _service.load_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    if _student_store is None:
        raise HTTPException(status_code=500, detail="student store not configured")

    profiles = _service.load_student()
    ghosts = room.offline_ghosts(profiles, _service.engine)
    return [StudyGhostPayload(**asdict(ghost)) for ghost in ghosts]


@app.post("/v1/ai/query")
def create_ai_query(payload: AIQueryPayload) -> dict[str, str]:
    query = payload.to_query()
    _service.log_ai_query(query)
    response = _ai.generate_response(query)
    _service.log_ai_response(response)
    return {"query_id": query.query_id, "mode": query.mode.value, "response": response.text}


@app.get("/v1/ai/queries/{student_id}")
def get_ai_queries(student_id: str) -> List[dict[str, str]]:
    queries = _service.load_ai_queries(student_id)
    return [
        {
            "query_id": query.query_id,
            "student_id": query.student_id,
            "subject": query.subject,
            "prompt": query.prompt,
            "mode": query.mode.value,
            "context": json.dumps(query.context),
            "created_at": query.created_at.isoformat(),
        }
        for query in queries
    ]


@app.get("/v1/ai/responses/{query_id}")
def get_ai_responses(query_id: str) -> List[dict[str, str]]:
    responses = _service.load_ai_responses(query_id)
    return [
        {
            "query_id": response.query_id,
            "mode": response.mode.value,
            "text": response.text,
            "created_at": response.created_at.isoformat(),
        }
        for response in responses
    ]


@app.get("/v1/metrics")
def get_metrics() -> dict:
    """Get system metrics for sync reliability and feature usage."""
    return metrics.to_dict()
