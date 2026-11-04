import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DB_PATH", BASE.parent / "data" / "sessions.db"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-this-local-demo-token")

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="Phishing Awareness Lab", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


with connect() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            consented INTEGER NOT NULL,
            user_agent TEXT,
            platform TEXT,
            language TEXT,
            screen_width INTEGER,
            screen_height INTEGER,
            camera_permission TEXT,
            location_permission TEXT,
            latitude REAL,
            longitude REAL,
            accuracy REAL
        )
    """)


class SessionIn(BaseModel):
    consent: bool
    user_agent: str = Field(default="", max_length=600)
    platform: str = Field(default="", max_length=120)
    language: str = Field(default="", max_length=80)
    screen_width: int | None = Field(default=None, ge=0, le=20000)
    screen_height: int | None = Field(default=None, ge=0, le=20000)
    camera_permission: str = Field(default="not_requested", max_length=40)
    location_permission: str = Field(default="not_requested", max_length=40)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0, le=100000)


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.post("/api/session")
def create_session(data: SessionIn):
    if not data.consent:
        raise HTTPException(status_code=400, detail="Consent is required.")
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute("""
            INSERT INTO sessions (
                id, created_at, consented, user_agent, platform, language,
                screen_width, screen_height, camera_permission,
                location_permission, latitude, longitude, accuracy
            ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sid, now, data.user_agent, data.platform, data.language,
            data.screen_width, data.screen_height, data.camera_permission,
            data.location_permission, data.latitude, data.longitude, data.accuracy
        ))
    return {"saved": True, "session_id": sid}


@app.get("/admin")
def admin_page():
    return FileResponse(BASE / "static" / "admin.html")


@app.get("/api/sessions")
def sessions(x_admin_token: str | None = Header(default=None)):
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token.")
    with connect() as conn:
        rows = conn.execute("""
            SELECT id, created_at, user_agent, platform, language,
                   screen_width, screen_height, camera_permission,
                   location_permission, latitude, longitude, accuracy
            FROM sessions ORDER BY created_at DESC LIMIT 250
        """).fetchall()
    return [dict(row) for row in rows]


@app.get("/health")
def health():
    return {"status": "ok"}
