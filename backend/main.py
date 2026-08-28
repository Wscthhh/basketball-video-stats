from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .analyzer import BasketballAnalyzer, analyzer_status

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "courttrace.sqlite3"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="COURTTRACE Local Analysis API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/media", StaticFiles(directory=UPLOAD_DIR), name="media")
ANALYZER = BasketballAnalyzer()

tasks: dict[str, dict[str, object]] = {}


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS clips (
              id TEXT PRIMARY KEY,
              match_id TEXT NOT NULL,
              filename TEXT NOT NULL,
              stored_path TEXT NOT NULL,
              sha256 TEXT NOT NULL UNIQUE,
              size_bytes INTEGER NOT NULL,
              duration REAL,
              status TEXT NOT NULL DEFAULT 'queued',
              confidence REAL NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analysis_events (
              id TEXT PRIMARY KEY,
              clip_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              seconds REAL NOT NULL,
              confidence REAL NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending',
              player_id TEXT,
              FOREIGN KEY(clip_id) REFERENCES clips(id)
            );
            """
        )


def command_available(command: str) -> bool:
    return shutil.which(command) is not None


def cuda_available() -> bool:
    try:
        import torch  # type: ignore

        return bool(torch.cuda.is_available())
    except ImportError:
        return False


def probe_duration(path: Path) -> float | None:
    if not command_available("ffprobe"):
        return None
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return float(result.stdout.strip())
    except (ValueError, subprocess.SubprocessError):
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clip_payload(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "matchId": row["match_id"],
        "name": row["filename"],
        "sizeBytes": row["size_bytes"],
        "duration": row["duration"],
        "status": row["status"],
        "confidence": row["confidence"],
        "previewUrl": f"/media/{row['match_id']}/{row['id']}/{row['filename']}",
        "createdAt": row["created_at"],
    }


class AnalyzeRequest(BaseModel):
    clip_ids: list[str] | None = None
    device: str = "auto"


@app.on_event("startup")
async def startup() -> None:
    init_db()


@app.get("/api/health")
async def health() -> dict[str, object]:
    has_cuda = cuda_available()
    return {
        "ok": True,
        "device": "cuda" if has_cuda else "cpu",
        "cuda": has_cuda,
        "torchInstalled": has_cuda,
        "ffmpeg": command_available("ffmpeg"),
        "ffprobe": command_available("ffprobe"),
        "mode": "GPU 加速" if has_cuda else "CPU fallback",
        "analyzer": analyzer_status(),
    }


@app.get("/api/matches/{match_id}/clips")
async def list_clips(match_id: str) -> list[dict[str, object]]:
    with db() as connection:
        rows = connection.execute("SELECT * FROM clips WHERE match_id = ? ORDER BY created_at DESC", (match_id,)).fetchall()
    return [clip_payload(row) for row in rows]


@app.post("/api/matches/{match_id}/clips")
async def upload_clips(match_id: str, files: Annotated[list[UploadFile], File(...)]) -> dict[str, object]:
    accepted: list[dict[str, object]] = []
    skipped: list[str] = []
    for file in files:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".mp4", ".mov", ".m4v", ".webm"}:
            skipped.append(file.filename or "unknown")
            continue
        clip_id = uuid.uuid4().hex
        clip_dir = UPLOAD_DIR / match_id / clip_id
        clip_dir.mkdir(parents=True, exist_ok=True)
        target = clip_dir / Path(file.filename or f"clip-{clip_id}{suffix}").name
        with target.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                output.write(chunk)
        digest = sha256_file(target)
        with db() as connection:
            duplicate = connection.execute("SELECT id FROM clips WHERE sha256 = ?", (digest,)).fetchone()
            if duplicate:
                target.unlink(missing_ok=True)
                shutil.rmtree(clip_dir, ignore_errors=True)
                skipped.append(file.filename or "duplicate")
                continue
            created_at = datetime.now(timezone.utc).isoformat()
            connection.execute(
                "INSERT INTO clips (id, match_id, filename, stored_path, sha256, size_bytes, duration, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (clip_id, match_id, target.name, str(target), digest, target.stat().st_size, probe_duration(target), created_at),
            )
            row = connection.execute("SELECT * FROM clips WHERE id = ?", (clip_id,)).fetchone()
        accepted.append(clip_payload(row))
    return {"accepted": accepted, "skipped": skipped}


async def run_analysis(task_id: str, match_id: str, clip_ids: list[str], device: str) -> None:
    task = tasks[task_id]
    total = len(clip_ids)
    for index, clip_id in enumerate(clip_ids, start=1):
        with db() as connection:
            clip = connection.execute("SELECT stored_path FROM clips WHERE id = ? AND match_id = ?", (clip_id, match_id)).fetchone()
        candidates = await asyncio.to_thread(ANALYZER.inspect, Path(clip["stored_path"]), device) if clip else []
        with db() as connection:
            connection.execute("UPDATE clips SET status = 'review', confidence = ? WHERE id = ? AND match_id = ?", (0.82, clip_id, match_id))
            for candidate in candidates:
                connection.execute("INSERT INTO analysis_events (id, clip_id, event_type, seconds, confidence) VALUES (?, ?, ?, ?, ?)", (f"ai-{uuid.uuid4().hex}", clip_id, candidate.event_type, candidate.seconds, candidate.confidence))
        task["completed"] = index
        task["progress"] = round(index / total * 100, 1) if total else 100
    task["status"] = "completed"


@app.post("/api/matches/{match_id}/analyze")
async def analyze(match_id: str, request: AnalyzeRequest) -> dict[str, object]:
    with db() as connection:
        if request.clip_ids:
            placeholders = ",".join("?" for _ in request.clip_ids)
            rows = connection.execute(f"SELECT id FROM clips WHERE match_id = ? AND id IN ({placeholders})", [match_id, *request.clip_ids]).fetchall()
        else:
            rows = connection.execute("SELECT id FROM clips WHERE match_id = ? AND status IN ('queued', 'failed')", (match_id,)).fetchall()
    clip_ids = [row["id"] for row in rows]
    task_id = uuid.uuid4().hex
    tasks[task_id] = {"id": task_id, "status": "running", "progress": 0, "completed": 0, "total": len(clip_ids), "device": "cuda" if cuda_available() and request.device != "cpu" else "cpu"}
    asyncio.create_task(run_analysis(task_id, match_id, clip_ids, str(tasks[task_id]["device"])))
    return tasks[task_id]


@app.get("/api/tasks/{task_id}")
async def task_status(task_id: str) -> dict[str, object]:
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="analysis task not found")
    return task


@app.get("/api/matches/{match_id}/events")
async def list_events(match_id: str) -> list[dict[str, object]]:
    with db() as connection:
        rows = connection.execute(
            "SELECT e.*, c.match_id FROM analysis_events e JOIN clips c ON c.id = e.clip_id WHERE c.match_id = ? ORDER BY e.seconds",
            (match_id,),
        ).fetchall()
    return [dict(row) for row in rows]
