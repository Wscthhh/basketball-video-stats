from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .analyzer import BasketballAnalyzer, classify_clip_team, resolve_command
from .team_classifier import classify as classify_team

ROOT = Path(os.getenv("COURTTRACE_APP_ROOT", str(Path(__file__).resolve().parent.parent)))
DATA_DIR = Path(os.getenv("COURTTRACE_DATA_DIR", str(ROOT / "data")))
UPLOAD_DIR = DATA_DIR / "uploads"
COVERS_DIR = DATA_DIR / "covers"
CATEGORY_DATA_DIR = DATA_DIR / "training" / "review"
CLIP_TEAM_DATA_DIR = DATA_DIR / "training" / "clip-team"
TRAINING_ARCHIVE_DIR = DATA_DIR / "training" / "archive"
EXPORT_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "courttrace.sqlite3"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
COVERS_DIR.mkdir(parents=True, exist_ok=True)
CATEGORY_DATA_DIR.mkdir(parents=True, exist_ok=True)
CLIP_TEAM_DATA_DIR.mkdir(parents=True, exist_ok=True)
TRAINING_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="COURTTRACE Local Analysis API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
app.mount("/media", StaticFiles(directory=UPLOAD_DIR), name="media")
app.mount("/media-covers", StaticFiles(directory=COVERS_DIR), name="media-covers")
app.mount("/media-exports", StaticFiles(directory=EXPORT_DIR), name="media-exports")
ANALYZER = BasketballAnalyzer()
MOBILE_TOKEN = os.getenv("COURTTRACE_LAN_TOKEN", "")
SSE_SUBSCRIBERS: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_mobile_token(token: str | None) -> None:
    if not MOBILE_TOKEN or not token or not secrets.compare_digest(token, MOBILE_TOKEN):
        raise HTTPException(403, "手机上传链接无效或已失效")


@app.middleware("http")
async def protect_lan_api(request: Request, call_next):
    client = request.client.host if request.client else ""
    if MOBILE_TOKEN and client not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        path = request.url.path
        mobile_api = path == "/mobile" or path == "/api/matches" or bool(re.fullmatch(r"/api/matches/[^/]+/(clips|analyze)", path))
        token = request.query_params.get("token")
        if not mobile_api or not token or not secrets.compare_digest(token, MOBILE_TOKEN):
            return JSONResponse({"detail": "局域网请求无权访问此接口"}, status_code=403)
    return await call_next(request)


async def publish_event(match_id: str, event_type: str, payload: dict[str, Any] | None = None) -> None:
    message = {"type": event_type, "matchId": match_id, **(payload or {})}
    for queue in list(SSE_SUBSCRIBERS.get(match_id, set())):
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            pass


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def init_db() -> None:
    stale_analysis_dirs: list[Path] = []
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS clips (id TEXT PRIMARY KEY, match_id TEXT NOT NULL, filename TEXT NOT NULL, stored_path TEXT NOT NULL, sha256 TEXT NOT NULL UNIQUE, size_bytes INTEGER NOT NULL, duration REAL, status TEXT NOT NULL DEFAULT 'queued', confidence REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL, team_id TEXT, team_source TEXT NOT NULL DEFAULT 'unresolved', team_confidence REAL NOT NULL DEFAULT 0, team_evidence TEXT NOT NULL DEFAULT '无法从片段可靠判断球队');
        CREATE TABLE IF NOT EXISTS analysis_events (id TEXT PRIMARY KEY, clip_id TEXT NOT NULL, event_type TEXT NOT NULL, seconds REAL NOT NULL, confidence REAL NOT NULL, status TEXT NOT NULL DEFAULT 'pending', player_id TEXT, description TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '', team_source TEXT, confirmed_by TEXT, confirmation_rule TEXT, FOREIGN KEY(clip_id) REFERENCES clips(id));
        CREATE TABLE IF NOT EXISTS matches (id TEXT PRIMARY KEY, name TEXT NOT NULL, played_at TEXT, venue TEXT, status TEXT NOT NULL DEFAULT 'draft', is_test INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS teams (id TEXT PRIMARY KEY, match_id TEXT NOT NULL, side TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', color TEXT, UNIQUE(match_id, side), FOREIGN KEY(match_id) REFERENCES matches(id));
        CREATE TABLE IF NOT EXISTS players (id TEXT PRIMARY KEY, match_id TEXT NOT NULL, team_id TEXT, code TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', number TEXT, number_confidence REAL NOT NULL DEFAULT 0, number_source TEXT, number_candidates_json TEXT NOT NULL DEFAULT '[]', identity_type TEXT NOT NULL DEFAULT 'temporary', status TEXT NOT NULL DEFAULT 'unconfirmed', confidence REAL NOT NULL DEFAULT 0, appearance_r REAL, appearance_g REAL, appearance_b REAL, appearance_samples INTEGER NOT NULL DEFAULT 0, track_count_total INTEGER NOT NULL DEFAULT 0, cover_path TEXT, cover_score REAL, cover_source_clip_id TEXT, cover_source_seconds REAL, UNIQUE(match_id, code), FOREIGN KEY(match_id) REFERENCES matches(id));
        CREATE TABLE IF NOT EXISTS player_tracks (id TEXT PRIMARY KEY, clip_id TEXT NOT NULL, player_id TEXT NOT NULL, local_track_key TEXT NOT NULL, team_id TEXT, confidence REAL NOT NULL DEFAULT 0, UNIQUE(clip_id, local_track_key), FOREIGN KEY(clip_id) REFERENCES clips(id), FOREIGN KEY(player_id) REFERENCES players(id));
        CREATE TABLE IF NOT EXISTS analysis_runs (id TEXT PRIMARY KEY, match_id TEXT NOT NULL, status TEXT NOT NULL, progress REAL NOT NULL DEFAULT 0, device TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', started_at TEXT, finished_at TEXT, created_at TEXT NOT NULL, version TEXT NOT NULL DEFAULT '1', FOREIGN KEY(match_id) REFERENCES matches(id));
        CREATE TABLE IF NOT EXISTS event_revisions (id TEXT PRIMARY KEY, event_id TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(event_id) REFERENCES analysis_events(id));
         CREATE TABLE IF NOT EXISTS review_samples (id TEXT PRIMARY KEY, match_id TEXT NOT NULL, clip_id TEXT NOT NULL, event_id TEXT NOT NULL UNIQUE, label TEXT NOT NULL, shot_type TEXT, player_id TEXT, seconds REAL NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, FOREIGN KEY(match_id) REFERENCES matches(id), FOREIGN KEY(clip_id) REFERENCES clips(id), FOREIGN KEY(event_id) REFERENCES analysis_events(id));
         CREATE TABLE IF NOT EXISTS clip_review_samples (id TEXT PRIMARY KEY, match_id TEXT NOT NULL, clip_id TEXT NOT NULL UNIQUE, team_id TEXT NOT NULL, label TEXT NOT NULL, frames_json TEXT NOT NULL DEFAULT '[]', metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(match_id) REFERENCES matches(id), FOREIGN KEY(clip_id) REFERENCES clips(id), FOREIGN KEY(team_id) REFERENCES teams(id));
         CREATE TABLE IF NOT EXISTS team_highlight_exports (id TEXT PRIMARY KEY, match_id TEXT NOT NULL, team_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued', progress REAL NOT NULL DEFAULT 0, clip_ids_json TEXT NOT NULL DEFAULT '[]', output_path TEXT, error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(match_id) REFERENCES matches(id), FOREIGN KEY(team_id) REFERENCES teams(id));
         CREATE TABLE IF NOT EXISTS team_classifier_profiles (team_id TEXT PRIMARY KEY, match_id TEXT NOT NULL, sample_count INTEGER NOT NULL DEFAULT 0, rgb_json TEXT NOT NULL, trained_at TEXT NOT NULL, FOREIGN KEY(team_id) REFERENCES teams(id));
         CREATE TABLE IF NOT EXISTS archived_team_training_samples (id TEXT PRIMARY KEY, source_match_id TEXT NOT NULL, source_team_id TEXT NOT NULL, label TEXT NOT NULL, frames_json TEXT NOT NULL DEFAULT '[]', metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, archived_at TEXT NOT NULL);
         CREATE TABLE IF NOT EXISTS archived_team_classifier_profiles (id TEXT PRIMARY KEY, source_match_id TEXT NOT NULL, source_team_id TEXT NOT NULL, side TEXT, sample_count INTEGER NOT NULL, rgb_json TEXT NOT NULL, trained_at TEXT NOT NULL, archived_at TEXT NOT NULL);
         CREATE TABLE IF NOT EXISTS archived_scoring_training_samples (id TEXT PRIMARY KEY, source_match_id TEXT NOT NULL, source_clip_id TEXT NOT NULL, source_event_id TEXT NOT NULL, label TEXT NOT NULL, team_id TEXT, shot_type TEXT, seconds REAL NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}', archived_at TEXT NOT NULL);
          """)
        run_columns = {r["name"] for r in c.execute("PRAGMA table_info(analysis_runs)")}
        clip_columns = {r["name"] for r in c.execute("PRAGMA table_info(clips)")}
        for name, definition in {"team_id": "TEXT", "team_source": "TEXT", "team_confidence": "REAL NOT NULL DEFAULT 0", "team_evidence": "TEXT"}.items():
            if name not in clip_columns:
                c.execute(f"ALTER TABLE clips ADD COLUMN {name} {definition}")
        c.execute("UPDATE clips SET team_source='unresolved' WHERE team_source IS NULL")
        c.execute("UPDATE clips SET team_confidence=0 WHERE team_confidence IS NULL")
        c.execute("UPDATE clips SET team_evidence='无法从片段可靠判断球队' WHERE team_evidence IS NULL")
        for name, definition in {"total_clips": "INTEGER NOT NULL DEFAULT 0", "completed_clips": "INTEGER NOT NULL DEFAULT 0", "details_json": "TEXT NOT NULL DEFAULT '{}'"}.items():
            if name not in run_columns:
                c.execute(f"ALTER TABLE analysis_runs ADD COLUMN {name} {definition}")
        # Existing installations have no parent match table and old event columns.
        for name, definition in {
            "team_id": "TEXT", "team_source": "TEXT", "team_confidence": "REAL NOT NULL DEFAULT 0", "team_evidence": "TEXT NOT NULL DEFAULT ''", "points": "INTEGER", "shot_type": "TEXT", "shot_type_confidence": "REAL NOT NULL DEFAULT 0", "shot_type_source": "TEXT", "court_x": "REAL", "court_y": "REAL", "homography_confidence": "REAL NOT NULL DEFAULT 0", "release_frame": "INTEGER", "run_id": "TEXT", "fingerprint": "TEXT", "highlight_start": "REAL", "highlight_end": "REAL", "confirmed_at": "TEXT", "updated_at": "TEXT", "local_track_key": "TEXT", "confirmed_by": "TEXT", "confirmation_rule": "TEXT"
        }.items():
            if name not in {r["name"] for r in c.execute("PRAGMA table_info(analysis_events)")}:
                c.execute(f"ALTER TABLE analysis_events ADD COLUMN {name} {definition}")
        player_columns = {r["name"] for r in c.execute("PRAGMA table_info(players)")}
        for name, definition in {"appearance_r": "REAL", "appearance_g": "REAL", "appearance_b": "REAL", "appearance_samples": "INTEGER NOT NULL DEFAULT 0", "track_count_total": "INTEGER NOT NULL DEFAULT 0", "number_confidence": "REAL NOT NULL DEFAULT 0", "number_source": "TEXT", "number_candidates_json": "TEXT NOT NULL DEFAULT '[]'", "cover_path": "TEXT", "cover_score": "REAL", "cover_source_clip_id": "TEXT", "cover_source_seconds": "REAL"}.items():
            if name not in player_columns:
                c.execute(f"ALTER TABLE players ADD COLUMN {name} {definition}")
        c.execute("UPDATE players SET number_source='manual',number_confidence=1 WHERE number IS NOT NULL AND number_source IS NULL")
        c.execute("UPDATE analysis_events SET confirmed_by='manual' WHERE status='confirmed' AND confirmed_by IS NULL AND (source='manual' OR EXISTS (SELECT 1 FROM event_revisions r WHERE r.event_id=analysis_events.id))")
        duplicate_fingerprints = c.execute(
            "SELECT fingerprint FROM analysis_events WHERE fingerprint IS NOT NULL GROUP BY fingerprint HAVING COUNT(*)>1"
        ).fetchall()
        for duplicate in duplicate_fingerprints:
            rows = c.execute(
                "SELECT id FROM analysis_events WHERE fingerprint=? ORDER BY CASE status WHEN 'confirmed' THEN 0 WHEN 'ignored' THEN 1 ELSE 2 END, updated_at DESC",
                (duplicate["fingerprint"],),
            ).fetchall()
            for row in rows[1:]:
                c.execute("UPDATE analysis_events SET fingerprint=NULL WHERE id=?", (row["id"],))
        review_columns = {r["name"] for r in c.execute("PRAGMA table_info(review_samples)")}
        if "team_id" not in review_columns:
            c.execute("ALTER TABLE review_samples ADD COLUMN team_id TEXT")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_event_fingerprint ON analysis_events(fingerprint) WHERE fingerprint IS NOT NULL")
        clip_review_columns = {r["name"] for r in c.execute("PRAGMA table_info(clip_review_samples)")}
        for name, definition in {
            "match_id": "TEXT",
            "clip_id": "TEXT",
            "team_id": "TEXT",
            "label": "TEXT",
            "frames_json": "TEXT NOT NULL DEFAULT '[]'",
            "metadata_json": "TEXT NOT NULL DEFAULT '{}'",
            "created_at": "TEXT",
            "updated_at": "TEXT",
        }.items():
            if name not in clip_review_columns:
                c.execute(f"ALTER TABLE clip_review_samples ADD COLUMN {name} {definition}")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_clip_review_samples_clip_id ON clip_review_samples(clip_id)")
        c.execute("UPDATE analysis_events SET event_type='attempt' WHERE event_type='投篮'")
        c.execute("UPDATE analysis_events SET event_type='make' WHERE event_type='命中'")
        c.execute("UPDATE analysis_events SET shot_type=CASE points WHEN 1 THEN 'freeThrow' WHEN 2 THEN 'twoPoint' WHEN 3 THEN 'threePoint' END WHERE event_type='make' AND shot_type IS NULL AND points IN (1,2,3)")
        legacy_ids = [r[0] for r in c.execute("SELECT DISTINCT match_id FROM clips").fetchall()]
        for match_id in legacy_ids:
            test = 1 if match_id == "integration-test" else 0
            c.execute("INSERT OR IGNORE INTO matches(id,name,is_test,created_at,status) VALUES(?,?,?,?,?)", (match_id, match_id, test, now(), "active"))
            for side in ("home", "away"):
                c.execute("INSERT OR IGNORE INTO teams(id,match_id,side,name) VALUES(?,?,?,?)", (f"{match_id}-{side}", match_id, side, ""))
        # A process restart cannot leave a run looking active.
        c.execute("UPDATE analysis_runs SET status='interrupted', error='service restarted', finished_at=? WHERE status='running'", (now(),))
        c.execute("UPDATE clips SET status='queued' WHERE status='processing'")
        analysis_root = DATA_DIR / "analysis"
        if analysis_root.is_dir():
            active_runs = {row["id"] for row in c.execute("SELECT id FROM analysis_runs WHERE status='running'")}
            stale_analysis_dirs = [path for path in analysis_root.iterdir() if path.is_dir() and path.name not in active_runs]
    for path in stale_analysis_dirs:
        shutil.rmtree(path, ignore_errors=True)


def row_payload(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def camel(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    names = {"match_id": "matchId", "team_id": "teamId", "team_source": "teamSource", "team_confidence": "teamConfidence", "team_evidence": "teamEvidence", "player_id": "playerId", "clip_id": "clipId", "run_id": "runId", "event_type": "type", "event_id": "eventId", "shot_type": "shotType", "shot_type_confidence": "shotTypeConfidence", "shot_type_source": "shotTypeSource", "court_x": "courtX", "court_y": "courtY", "homography_confidence": "homographyConfidence", "release_frame": "releaseFrame", "local_track_key": "localTrackKey", "identity_type": "identityType", "is_test": "isTest", "played_at": "playedAt", "created_at": "createdAt", "updated_at": "updatedAt", "confirmed_at": "confirmedAt", "confirmed_by": "confirmedBy", "confirmation_rule": "confirmationRule", "highlight_start": "highlightStart", "highlight_end": "highlightEnd", "stored_path": "storedPath", "size_bytes": "sizeBytes", "preview_url": "previewUrl", "started_at": "startedAt", "finished_at": "finishedAt", "number_confidence": "numberConfidence", "number_source": "numberSource", "number_candidates_json": "numberCandidates"}
    return {names.get(k, k): v for k, v in dict(row).items()}


def team_payload(row: sqlite3.Row) -> dict[str, Any]:
    return camel(row)


def match_payload(c: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    value = camel(row)
    teams = {r["side"]: team_payload(r) for r in c.execute("SELECT * FROM teams WHERE match_id=?", (row["id"],))}
    value["homeTeam"] = teams.get("home", {"side": "home", "name": "", "color": None})
    value["awayTeam"] = teams.get("away", {"side": "away", "name": "", "color": None})
    return value


def player_payload(c: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    value = camel(row)
    value["numberCandidates"] = json.loads(row["number_candidates_json"] or "[]")
    team = c.execute("SELECT side,color FROM teams WHERE id=?", (row["team_id"],)).fetchone() if row["team_id"] else None
    value["displayName"] = row["name"] or row["code"]
    value["team"] = team["side"] if team else None
    value["color"] = team["color"] if team else None
    value["tracksCount"] = c.execute("SELECT COUNT(*) FROM player_tracks WHERE player_id=?", (row["id"],)).fetchone()[0]
    value["tracks"] = value["tracksCount"]
    value["coverUrl"] = f"/media-covers/{row['match_id']}/{row['id']}.jpg" if row["cover_path"] else None
    return value


def clip_payload(row: sqlite3.Row) -> dict[str, Any]:
    value = camel(row)
    value["name"] = row["filename"]
    value["previewUrl"] = f"/media/{row['match_id']}/{row['id']}/{row['filename']}"
    value["teamConfirmed"] = row["team_source"] == "manual"
    return value


def clip_team_is_confirmed(row: sqlite3.Row) -> bool:
    return row["team_source"] == "manual"


def clip_has_team_assignment(row: sqlite3.Row) -> bool:
    return row["team_id"] is not None and row["team_source"] in ("ai", "manual")


def learned_team_prototypes(c: sqlite3.Connection, match_id: str) -> dict[str, tuple[float, float, float]]:
    return {row["team_id"]: tuple(json.loads(row["rgb_json"])) for row in c.execute("SELECT team_id,rgb_json FROM team_classifier_profiles WHERE match_id=?", (match_id,))}


TRAINING_SAMPLE_THRESHOLD = 10


def team_training_status(c: sqlite3.Connection, match_id: str) -> dict[str, Any]:
    teams = c.execute("SELECT id,side,name FROM teams WHERE match_id=? ORDER BY side", (match_id,)).fetchall()
    counts = {row["team_id"]: row["count"] for row in c.execute("SELECT team_id,COUNT(*) AS count FROM clip_review_samples WHERE match_id=? GROUP BY team_id", (match_id,))}
    profiles = {row["team_id"]: row for row in c.execute("SELECT team_id,sample_count,trained_at FROM team_classifier_profiles WHERE match_id=?", (match_id,))}
    team_status = [{"teamId": team["id"], "side": team["side"], "name": team["name"], "sampleCount": counts.get(team["id"], 0), "trainedSampleCount": profiles[team["id"]]["sample_count"] if team["id"] in profiles else 0, "trainedAt": profiles[team["id"]]["trained_at"] if team["id"] in profiles else None} for team in teams]
    ready = len(team_status) == 2 and all(item["sampleCount"] >= TRAINING_SAMPLE_THRESHOLD for item in team_status)
    trained = len(team_status) == 2 and all(item["trainedSampleCount"] >= TRAINING_SAMPLE_THRESHOLD for item in team_status)
    stale = trained and any(item["sampleCount"] > item["trainedSampleCount"] for item in team_status)
    return {"threshold": TRAINING_SAMPLE_THRESHOLD, "ready": ready, "trained": trained, "suggestion": ready and (not trained or stale), "teams": team_status}


def train_team_classifier(match_id: str) -> dict[str, Any]:
    try:
        import cv2
    except ImportError as error:
        raise RuntimeError("缺少 OpenCV，无法训练球队识别模型") from error
    with db() as c:
        require_match(match_id, c)
        rows = c.execute("SELECT team_id,frames_json FROM clip_review_samples WHERE match_id=? ORDER BY created_at", (match_id,)).fetchall()
        samples: dict[str, list[tuple[float, float, float]]] = {}
        for row in rows:
            for frame in json.loads(row["frames_json"] or "[]"):
                path = DATA_DIR / frame
                image = cv2.imread(str(path)) if not Path(frame).is_absolute() else cv2.imread(str(path))
                if image is None:
                    continue
                height, width = image.shape[:2]
                crop = image[int(height * .2):int(height * .8), int(width * .2):int(width * .8)]
                if crop.size:
                    blue, green, red = [float(value) for value in cv2.mean(crop)[:3]]
                    samples.setdefault(row["team_id"], []).append((red, green, blue))
        teams = c.execute("SELECT id FROM teams WHERE match_id=? ORDER BY side", (match_id,)).fetchall()
        if len(teams) != 2 or any(len(samples.get(team["id"], [])) < TRAINING_SAMPLE_THRESHOLD for team in teams):
            raise ValueError(f"每支球队至少需要 {TRAINING_SAMPLE_THRESHOLD} 个有效训练片段")
        trained_at = now()
        for team in teams:
            values = samples[team["id"]]
            prototype = tuple(sum(value[index] for value in values) / len(values) for index in range(3))
            sample_count = c.execute("SELECT COUNT(*) FROM clip_review_samples WHERE team_id=?", (team["id"],)).fetchone()[0]
            c.execute("INSERT INTO team_classifier_profiles(team_id,match_id,sample_count,rgb_json,trained_at) VALUES(?,?,?,?,?) ON CONFLICT(team_id) DO UPDATE SET sample_count=excluded.sample_count,rgb_json=excluded.rgb_json,trained_at=excluded.trained_at", (team["id"], match_id, sample_count, json.dumps(prototype), trained_at))
        return team_training_status(c, match_id)


def capture_clip_team_sample(clip: sqlite3.Row, sample_dir: Path) -> list[str]:
    frames: list[str] = []
    sample_dir.mkdir(parents=True, exist_ok=True)
    try:
        import cv2
        capture = cv2.VideoCapture(str(clip["stored_path"]))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if frame_count <= 0:
            capture.release()
            return frames
        for index, ratio in enumerate((0.0, 0.5, 0.9)):
            capture.set(cv2.CAP_PROP_POS_FRAMES, min(frame_count - 1, int(frame_count * ratio)))
            ok, frame = capture.read()
            if not ok:
                continue
            frame_path = sample_dir / f"frame-{index:02d}.jpg"
            if cv2.imwrite(str(frame_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92]):
                frames.append(str(frame_path.relative_to(DATA_DIR)))
        capture.release()
    except Exception:
        frames = []
    return frames


def run_payload(row: sqlite3.Row) -> dict[str, Any]:
    value = camel(row)
    value["total"] = row["total_clips"]
    value["completed"] = row["completed_clips"]
    value["details"] = json.loads(row["details_json"] or "{}")
    return value


class InputModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=lambda value: value.split("_")[0] + "".join(part.title() for part in value.split("_")[1:]),
    )


class MatchInput(InputModel):
    name: str | None = Field(default=None, max_length=120)
    played_at: str | None = None
    venue: str | None = None
    status: str = "draft"
    is_test: bool = False
    home_team: dict[str, Any] = Field(default_factory=dict)
    away_team: dict[str, Any] = Field(default_factory=dict)


class MatchPatch(InputModel):
    name: str | None = None
    played_at: str | None = None
    venue: str | None = None
    status: str | None = None
    is_test: bool | None = None
    home_team: dict[str, Any] | None = None
    away_team: dict[str, Any] | None = None


class AnalyzeRequest(InputModel):
    clip_ids: list[str] | None = None
    device: Literal["auto", "cpu", "cuda"] = "auto"


class EventPatch(InputModel):
    status: Literal["pending", "confirmed", "ignored"] | None = None
    player_id: str | None = None
    team_id: str | None = None
    type: Literal["attempt", "make"] | None = None
    shot_type: Literal["freeThrow", "twoPoint", "threePoint"] | None = None
    points: int | None = Field(None, ge=0, le=3)


class ClipPatch(InputModel):
    team_id: str | None = None


class PlayerPatch(InputModel):
    name: str | None = None
    number: str | None = None
    team_id: str | None = None
    status: str | None = None
    identity_type: str | None = None


class ManualEvent(InputModel):
    clip_id: str
    type: Literal["attempt", "make"]
    shot_type: Literal["freeThrow", "twoPoint", "threePoint"] | None = None
    seconds: float = Field(ge=0)
    points: int | None = Field(None, ge=0, le=3)
    player_id: str | None = None
    team_id: str | None = None


@app.on_event("startup")
async def startup() -> None:
    init_db()


@app.get("/api/health")
async def health() -> dict[str, Any]:
    has_cuda = cuda_available()
    return {"ok": True, "device": "cuda" if has_cuda else "cpu", "cuda": has_cuda, "torchInstalled": torch_installed(), "ffmpeg": command_available("ffmpeg"), "ffprobe": command_available("ffprobe"), "mode": "GPU 加速" if has_cuda else "CPU fallback", "analyzer": ANALYZER.status()}


def match_storage_path(match_id: str) -> Path:
    return UPLOAD_DIR / match_id


@app.get("/api/matches/{match_id}/storage")
async def match_storage(match_id: str) -> dict[str, Any]:
    with db() as c:
        require_match(match_id, c)
        clip_count = c.execute("SELECT COUNT(*) FROM clips WHERE match_id=?", (match_id,)).fetchone()[0]
    root = match_storage_path(match_id)
    files = [path for path in root.rglob("*") if path.is_file()] if root.is_dir() else []
    return {"matchId": match_id, "path": str(root.resolve()), "exists": root.is_dir(), "fileCount": len(files), "sizeBytes": sum(path.stat().st_size for path in files), "clipCount": clip_count}


@app.post("/api/matches/{match_id}/open-folder")
async def open_match_folder(match_id: str) -> dict[str, Any]:
    with db() as c:
        require_match(match_id, c)
    root = match_storage_path(match_id)
    root.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        subprocess.Popen(["explorer.exe", str(root.resolve())])
    else:
        raise HTTPException(501, "当前系统不支持打开文件夹")
    return {"opened": True, "path": str(root.resolve())}


def archive_training_for_match(c: sqlite3.Connection, match_id: str) -> tuple[int, int]:
    archived_at = now()
    samples = c.execute("SELECT * FROM clip_review_samples WHERE match_id=?", (match_id,)).fetchall()
    for sample in samples:
        archived_frames = []
        for frame in json.loads(sample["frames_json"] or "[]"):
            source = DATA_DIR / frame
            target = TRAINING_ARCHIVE_DIR / "team" / match_id / sample["clip_id"] / Path(frame).name
            if source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                archived_frames.append(str(target.relative_to(DATA_DIR)))
        c.execute("INSERT INTO archived_team_training_samples(id,source_match_id,source_team_id,label,frames_json,metadata_json,created_at,archived_at) VALUES(?,?,?,?,?,?,?,?)", (uuid.uuid4().hex, match_id, sample["team_id"], sample["label"], json.dumps(archived_frames), sample["metadata_json"], sample["created_at"], archived_at))
    scoring_samples = c.execute("SELECT * FROM review_samples WHERE match_id=?", (match_id,)).fetchall()
    for sample in scoring_samples:
        metadata = json.loads(sample["metadata_json"] or "{}")
        frames = metadata.get("frames", [])
        archived_frames = []
        for frame in frames:
            source = DATA_DIR / frame
            target = TRAINING_ARCHIVE_DIR / "scoring" / match_id / sample["id"] / Path(frame).name
            if source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                archived_frames.append(str(target.relative_to(DATA_DIR)))
        metadata["frames"] = archived_frames
        c.execute("INSERT INTO archived_scoring_training_samples(id,source_match_id,source_clip_id,source_event_id,label,team_id,shot_type,seconds,metadata_json,archived_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (uuid.uuid4().hex, match_id, sample["clip_id"], sample["event_id"], sample["label"], sample["team_id"], sample["shot_type"], sample["seconds"], json.dumps(metadata), archived_at))
    profiles = c.execute("SELECT p.*,t.side FROM team_classifier_profiles p LEFT JOIN teams t ON t.id=p.team_id WHERE p.match_id=?", (match_id,)).fetchall()
    for profile in profiles:
        c.execute("INSERT INTO archived_team_classifier_profiles(id,source_match_id,source_team_id,side,sample_count,rgb_json,trained_at,archived_at) VALUES(?,?,?,?,?,?,?,?)", (uuid.uuid4().hex, match_id, profile["team_id"], profile["side"], profile["sample_count"], profile["rgb_json"], profile["trained_at"], archived_at))
    return len(samples), len(profiles)


@app.delete("/api/matches/{match_id}")
async def delete_match(match_id: str) -> dict[str, Any]:
    paths = {UPLOAD_DIR / match_id, COVERS_DIR / match_id, CATEGORY_DATA_DIR / match_id, CLIP_TEAM_DATA_DIR / match_id, EXPORT_DIR / match_id}
    with db() as c:
        require_match(match_id, c)
        sample_count, profile_count = archive_training_for_match(c, match_id)
        run_ids = [row["id"] for row in c.execute("SELECT id FROM analysis_runs WHERE match_id=?", (match_id,)).fetchall()]
        paths.update(DATA_DIR / "analysis" / run_id for run_id in run_ids)
        clip_ids = [row["id"] for row in c.execute("SELECT id FROM clips WHERE match_id=?", (match_id,)).fetchall()]
        if clip_ids:
            marks = ",".join("?" for _ in clip_ids)
            c.execute(f"DELETE FROM event_revisions WHERE event_id IN (SELECT id FROM analysis_events WHERE clip_id IN ({marks}))", clip_ids)
            c.execute(f"DELETE FROM analysis_events WHERE clip_id IN ({marks})", clip_ids)
            c.execute(f"DELETE FROM player_tracks WHERE clip_id IN ({marks})", clip_ids)
        c.execute("DELETE FROM review_samples WHERE match_id=?", (match_id,))
        c.execute("DELETE FROM clip_review_samples WHERE match_id=?", (match_id,))
        c.execute("DELETE FROM team_highlight_exports WHERE match_id=?", (match_id,))
        c.execute("DELETE FROM team_classifier_profiles WHERE match_id=?", (match_id,))
        c.execute("DELETE FROM analysis_runs WHERE match_id=?", (match_id,))
        c.execute("DELETE FROM players WHERE match_id=?", (match_id,))
        c.execute("DELETE FROM clips WHERE match_id=?", (match_id,))
        c.execute("DELETE FROM teams WHERE match_id=?", (match_id,))
        c.execute("DELETE FROM matches WHERE id=?", (match_id,))
    for path in paths:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    return {"id": match_id, "deleted": True, "trainingSamplesPreserved": sample_count, "modelProfilesPreserved": profile_count}


@app.get("/api/matches/{match_id}/team-classifier/training-status")
async def get_team_training_status(match_id: str) -> dict[str, Any]:
    with db() as c:
        require_match(match_id, c)
        return team_training_status(c, match_id)


@app.post("/api/matches/{match_id}/team-classifier/train")
async def train_team_classifier_endpoint(match_id: str) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(train_team_classifier, match_id)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(422, str(error)) from error


@app.get("/api/matches")
async def list_matches(include_test: bool = True, token: str | None = None) -> list[dict[str, Any]]:
    if token is not None:
        require_mobile_token(token)
    with db() as c:
        rows = c.execute(
            "SELECT * FROM matches ORDER BY created_at DESC" if include_test
            else "SELECT * FROM matches WHERE is_test=0 ORDER BY created_at DESC"
        ).fetchall()
    with db() as c: return [match_payload(c, r) for r in rows]


@app.get("/api/matches/{match_id}/events/stream")
async def event_stream(match_id: str, token: str | None = None) -> StreamingResponse:
    with db() as c:
        require_match(match_id, c)
    if token is not None:
        require_mobile_token(token)
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=32)
    subscribers = SSE_SUBSCRIBERS.setdefault(match_id, set())
    subscribers.add(queue)

    async def stream():
        try:
            yield "event: ready\ndata: {}\n\n"
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"event: {message['type']}\ndata: {json.dumps(message, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            subscribers.discard(queue)
            if not subscribers:
                SSE_SUBSCRIBERS.pop(match_id, None)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/matches", status_code=201)
async def create_match(data: MatchInput) -> dict[str, Any]:
    for team in (data.home_team, data.away_team):
        if not str(team.get("name", "")).strip():
            raise HTTPException(422, "both team names are required")
    match_name = f"{str(data.home_team.get('name', '')).strip()} VS {str(data.away_team.get('name', '')).strip()}"
    match_id = uuid.uuid4().hex
    with db() as c:
        c.execute("INSERT INTO matches VALUES(?,?,?,?,?,?,?)", (match_id, match_name, data.played_at, data.venue, data.status, int(data.is_test), now()))
        for side, team in (("home", data.home_team), ("away", data.away_team)):
            c.execute("INSERT INTO teams(id,match_id,side,name,color) VALUES(?,?,?,?,?)", (f"{match_id}-{side}", match_id, side, team.get("name", ""), team.get("color")))
        return match_payload(c, c.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone())


def require_match(match_id: str, c: sqlite3.Connection) -> sqlite3.Row:
    row = c.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone()
    if not row:
        raise HTTPException(404, "match not found")
    return row


@app.get("/api/matches/{match_id}")
async def get_match(match_id: str) -> dict[str, Any]:
    with db() as c: return match_payload(c, require_match(match_id, c))


@app.patch("/api/matches/{match_id}")
async def patch_match(match_id: str, data: MatchPatch) -> dict[str, Any]:
    with db() as c:
        require_match(match_id, c)
        old = dict(c.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone())
        values = data.model_dump(exclude_unset=True)
        values = {key: values.get(key, old[key]) for key in ("name", "played_at", "venue", "status", "is_test")}
        c.execute("UPDATE matches SET name=?,played_at=?,venue=?,status=?,is_test=? WHERE id=?", (values["name"], values["played_at"], values["venue"], values["status"], int(values["is_test"]), match_id))
        for side, team in (("home", data.home_team), ("away", data.away_team)):
            if team is not None:
                c.execute("UPDATE teams SET name=?,color=? WHERE match_id=? AND side=?", (team.get("name", ""), team.get("color"), match_id, side))
        return match_payload(c, c.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone())


@app.get("/api/matches/{match_id}/clips")
async def list_clips(match_id: str) -> list[dict[str, Any]]:
    with db() as c:
        require_match(match_id, c); return [clip_payload(r) for r in c.execute("SELECT * FROM clips WHERE match_id=? ORDER BY created_at DESC", (match_id,))]


@app.patch("/api/clips/{clip_id}")
async def patch_clip(clip_id: str, data: ClipPatch) -> dict[str, Any]:
    sample_dir_to_remove: Path | None = None
    with db() as c:
        clip = c.execute("SELECT * FROM clips WHERE id=?", (clip_id,)).fetchone()
        if not clip:
            raise HTTPException(404, "clip not found")
        values = data.model_dump(exclude_unset=True)
        if "team_id" not in values:
            return clip_payload(clip)
        team_id = values["team_id"]
        if team_id is not None and not c.execute("SELECT id FROM teams WHERE id=? AND match_id=?", (team_id, clip["match_id"])).fetchone():
            raise HTTPException(422, "team does not belong to match")
        if team_id is None:
            c.execute("UPDATE clips SET team_id=NULL,team_source='unresolved',team_confidence=0,team_evidence='无法从片段可靠判断球队' WHERE id=?", (clip_id,))
            if c.execute("DELETE FROM clip_review_samples WHERE clip_id=?", (clip_id,)).rowcount:
                sample_dir_to_remove = CLIP_TEAM_DATA_DIR / clip["match_id"] / clip_id
        else:
            c.execute("UPDATE clips SET team_id=?,team_source='manual',team_confidence=1,team_evidence='手动指定球队' WHERE id=?", (team_id, clip_id))
            team = c.execute("SELECT side FROM teams WHERE id=?", (team_id,)).fetchone()
            sample_dir = CLIP_TEAM_DATA_DIR / clip["match_id"] / clip_id
            shutil.rmtree(sample_dir, ignore_errors=True)
            frames = capture_clip_team_sample(clip, sample_dir)
            timestamp = now()
            metadata = {"source": "manual", "clipFilename": clip["filename"], "duration": clip["duration"]}
            c.execute(
                """INSERT INTO clip_review_samples
                (id,match_id,clip_id,team_id,label,frames_json,metadata_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(clip_id) DO UPDATE SET team_id=excluded.team_id,label=excluded.label,
                frames_json=excluded.frames_json,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at""",
                (uuid.uuid4().hex, clip["match_id"], clip_id, team_id,
                 f"team_{team['side']}", json.dumps(frames), json.dumps(metadata), timestamp, timestamp),
            )
        result = clip_payload(c.execute("SELECT * FROM clips WHERE id=?", (clip_id,)).fetchone())
    if sample_dir_to_remove:
        shutil.rmtree(sample_dir_to_remove, ignore_errors=True)
    return result


@app.delete("/api/clips/{clip_id}")
async def delete_clip(clip_id: str) -> dict[str, Any]:
    paths_to_remove: set[Path] = set()
    files_to_remove: set[Path] = set()
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        clip = c.execute("SELECT match_id,stored_path FROM clips WHERE id=?", (clip_id,)).fetchone()
        if not clip:
            raise HTTPException(404, "clip not found")

        stored_path = Path(clip["stored_path"])
        if stored_path.parent.name == clip_id:
            paths_to_remove.add(stored_path.parent)
        else:
            files_to_remove.add(stored_path)
        analysis_root = DATA_DIR / "analysis"
        if analysis_root.is_dir():
            paths_to_remove.update(run_dir / clip_id for run_dir in analysis_root.iterdir() if (run_dir / clip_id).exists())

        sample_rows = c.execute("SELECT id FROM review_samples WHERE clip_id=?", (clip_id,)).fetchall()
        paths_to_remove.update(CATEGORY_DATA_DIR / clip["match_id"] / row["id"] for row in sample_rows)
        if c.execute("SELECT 1 FROM clip_review_samples WHERE clip_id=?", (clip_id,)).fetchone():
            paths_to_remove.add(CLIP_TEAM_DATA_DIR / clip["match_id"] / clip_id)
        affected_player_ids = {
            row["player_id"] for row in c.execute("SELECT DISTINCT player_id FROM player_tracks WHERE clip_id=?", (clip_id,))
        }
        cover_rows = c.execute("SELECT id,cover_path FROM players WHERE cover_source_clip_id=?", (clip_id,)).fetchall()
        affected_player_ids.update(row["id"] for row in cover_rows)
        files_to_remove.update(Path(row["cover_path"]) for row in cover_rows if row["cover_path"])

        c.execute("DELETE FROM review_samples WHERE clip_id=?", (clip_id,))
        c.execute("DELETE FROM clip_review_samples WHERE clip_id=?", (clip_id,))
        c.execute("DELETE FROM event_revisions WHERE event_id IN (SELECT id FROM analysis_events WHERE clip_id=?)", (clip_id,))
        c.execute("DELETE FROM analysis_events WHERE clip_id=?", (clip_id,))
        c.execute("DELETE FROM player_tracks WHERE clip_id=?", (clip_id,))
        c.execute("UPDATE players SET cover_path=NULL,cover_score=NULL,cover_source_clip_id=NULL,cover_source_seconds=NULL WHERE cover_source_clip_id=?", (clip_id,))

        if affected_player_ids:
            marks = ",".join("?" for _ in affected_player_ids)
            removable_players = c.execute(
                f"SELECT id,cover_path FROM players WHERE id IN ({marks}) "
                "AND identity_type IN ('temporary','unconfirmed') "
                "AND NOT EXISTS (SELECT 1 FROM player_tracks WHERE player_tracks.player_id=players.id)",
                list(affected_player_ids),
            ).fetchall()
            if removable_players:
                removable_ids = [row["id"] for row in removable_players]
                removable_marks = ",".join("?" for _ in removable_ids)
                files_to_remove.update(Path(row["cover_path"]) for row in removable_players if row["cover_path"])
                c.execute(f"DELETE FROM players WHERE id IN ({removable_marks})", removable_ids)
        c.execute("DELETE FROM clips WHERE id=?", (clip_id,))

    for path in paths_to_remove:
        shutil.rmtree(path, ignore_errors=True)
    for path in files_to_remove:
        delete_cover_file(str(path))
    return {"id": clip_id, "deleted": True}


@app.get("/api/matches/{match_id}/clips/collections")
async def clip_collections(match_id: str, token: str | None = None) -> dict[str, Any]:
    if token is not None:
        require_mobile_token(token)
    with db() as c:
        require_match(match_id, c)
        teams = {row["side"]: team_payload(row) for row in c.execute("SELECT * FROM teams WHERE match_id=?", (match_id,))}
        groups: dict[str, Any] = {"home": {"team": teams.get("home"), "clips": []}, "away": {"team": teams.get("away"), "clips": []}, "unresolved": []}
        team_sides = {team["id"]: side for side, team in teams.items() if team.get("id")}
        for row in c.execute("SELECT * FROM clips WHERE match_id=? ORDER BY created_at DESC", (match_id,)):
            clip = clip_payload(row)
            side = team_sides.get(row["team_id"])
            groups[side]["clips"].append(clip) if clip_has_team_assignment(row) and side in ("home", "away") else groups["unresolved"].append(clip)
        return groups


def export_payload(row: sqlite3.Row) -> dict[str, Any]:
    value = camel(row)
    value["clipIds"] = json.loads(row["clip_ids_json"] or "[]")
    value["downloadUrl"] = f"/media-exports/{row['match_id']}/{row['id']}.mp4" if row["output_path"] and row["status"] == "completed" else None
    return value


def highlight_output_name(team_name: str) -> str:
    clean = re.sub(r"[^0-9A-Za-z_-]+", "-", team_name).strip("-")
    return clean or "team-highlight"


def generate_team_highlight(export_id: str, match_id: str, team_id: str, clip_ids: list[str], output_path: str) -> None:
    try:
        ffmpeg = resolve_command("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("未找到 FFmpeg，无法生成球队集锦")
        export_file = Path(output_path)
        export_file.parent.mkdir(parents=True, exist_ok=True)
        concat_file = export_file.with_suffix(".txt")
        with concat_file.open("w", encoding="utf-8") as handle:
            with db() as c:
                rows = c.execute("SELECT stored_path FROM clips WHERE match_id=? AND id IN ({}) AND team_id=? AND team_source IN ('ai','manual') ORDER BY CASE team_source WHEN 'ai' THEN 0 ELSE 1 END, created_at".format(",".join("?" for _ in clip_ids)), [match_id, *clip_ids, team_id]).fetchall()
            for row in rows:
                path = Path(row["stored_path"]).resolve().as_posix().replace("'", "'\\''")
                handle.write(f"file '{path}'\n")
        with db() as c:
            c.execute("UPDATE team_highlight_exports SET status='running',progress=10,updated_at=? WHERE id=?", (now(), export_id))
        command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "aac", "-movflags", "+faststart", str(export_file)]
        subprocess.run(command, check=True, timeout=1800)
        with db() as c:
            c.execute("UPDATE team_highlight_exports SET status='completed',progress=100,output_path=?,updated_at=? WHERE id=?", (str(export_file), now(), export_id))
    except Exception as error:
        with db() as c:
            c.execute("UPDATE team_highlight_exports SET status='failed',error=?,updated_at=? WHERE id=?", (str(error), now(), export_id))
    finally:
        Path(output_path).with_suffix(".txt").unlink(missing_ok=True)


@app.get("/api/clips/{clip_id}/download")
async def download_clip(clip_id: str) -> FileResponse:
    with db() as c:
        clip = c.execute("SELECT filename,stored_path FROM clips WHERE id=?", (clip_id,)).fetchone()
    if not clip or not Path(clip["stored_path"]).is_file():
        raise HTTPException(404, "clip file not found")
    return FileResponse(clip["stored_path"], media_type="video/mp4", filename=clip["filename"])


@app.get("/api/matches/{match_id}/team-highlights")
async def list_team_highlights(match_id: str) -> list[dict[str, Any]]:
    with db() as c:
        require_match(match_id, c)
        return [export_payload(row) for row in c.execute("SELECT * FROM team_highlight_exports WHERE match_id=? ORDER BY created_at DESC", (match_id,))]


@app.post("/api/matches/{match_id}/team-highlights/{team_id}/generate")
async def create_team_highlight(match_id: str, team_id: str, background_tasks: BackgroundTasks) -> dict[str, Any]:
    with db() as c:
        require_match(match_id, c)
        team = c.execute("SELECT * FROM teams WHERE id=? AND match_id=?", (team_id, match_id)).fetchone()
        if not team:
            raise HTTPException(404, "team not found")
        clips = c.execute("SELECT id FROM clips WHERE match_id=? AND team_id=? AND team_source IN ('ai','manual') ORDER BY CASE team_source WHEN 'ai' THEN 0 ELSE 1 END, created_at", (match_id, team_id)).fetchall()
        if not clips:
            raise HTTPException(422, "没有已确认归属的片段")
        previous = c.execute("SELECT * FROM team_highlight_exports WHERE match_id=? AND team_id=? AND status IN ('queued','running') ORDER BY created_at DESC LIMIT 1", (match_id, team_id)).fetchone()
        if previous:
            return export_payload(previous)
        export_id = uuid.uuid4().hex
        output_dir = EXPORT_DIR / match_id
        output_path = output_dir / f"{export_id}.mp4"
        c.execute("INSERT INTO team_highlight_exports(id,match_id,team_id,status,progress,clip_ids_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (export_id, match_id, team_id, "queued", 0, json.dumps([row["id"] for row in clips]), now(), now()))
        result = export_payload(c.execute("SELECT * FROM team_highlight_exports WHERE id=?", (export_id,)).fetchone())
    background_tasks.add_task(generate_team_highlight, export_id, match_id, team_id, result["clipIds"], str(output_path))
    return result


@app.post("/api/matches/{match_id}/clips")
async def upload_clips(match_id: str, files: Annotated[list[UploadFile], File(...)], token: str | None = None) -> dict[str, Any]:
    if token is not None:
        require_mobile_token(token)
    accepted, skipped = [], []
    with db() as c: require_match(match_id, c)
    for file in files:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".mp4", ".mov", ".m4v", ".webm"}: skipped.append(file.filename or "unknown"); continue
        clip_id = uuid.uuid4().hex
        clip_dir = UPLOAD_DIR / match_id / clip_id
        clip_dir.mkdir(parents=True, exist_ok=True)
        target = clip_dir / Path(file.filename or f"clip-{clip_id}{suffix}").name
        try:
            with target.open("wb") as output:
                while chunk := await file.read(1024 * 1024): output.write(chunk)
            digest = sha256_file(target)
            with db() as c:
                if c.execute("SELECT id FROM clips WHERE sha256=?", (digest,)).fetchone():
                    skipped.append(file.filename or "duplicate")
                    shutil.rmtree(clip_dir, ignore_errors=True)
                    continue
                try:
                    c.execute("INSERT INTO clips(id,match_id,filename,stored_path,sha256,size_bytes,duration,created_at) VALUES(?,?,?,?,?,?,?,?)", (clip_id, match_id, target.name, str(target), digest, target.stat().st_size, probe_duration(target), now()))
                except sqlite3.IntegrityError:
                    skipped.append(file.filename or "duplicate")
                    shutil.rmtree(clip_dir, ignore_errors=True)
                    continue
                accepted.append(clip_payload(c.execute("SELECT * FROM clips WHERE id=?", (clip_id,)).fetchone()))
        except Exception:
            shutil.rmtree(clip_dir, ignore_errors=True)
            raise
    if accepted:
        await publish_event(match_id, "clip.uploaded", {"clipIds": [clip["id"] for clip in accepted], "count": len(accepted)})
    return {"accepted": accepted, "skipped": skipped}


@app.get("/mobile")
async def mobile_upload_page(token: str | None = None) -> HTMLResponse:
    require_mobile_token(token)
    return HTMLResponse("""<!doctype html><html lang='zh-CN'><meta name='viewport' content='width=device-width,initial-scale=1'><title>COURTTRACE 手机上传</title><style>body{margin:0;padding:20px;background:#0d1210;color:#edf3ed;font-family:Arial,sans-serif}main{max-width:620px;margin:auto}h1{font-size:25px}section{padding:18px;background:#17211d;border:1px solid #304137;border-radius:8px}label{display:grid;gap:8px;color:#aab8ac;font-size:13px}select,input,button{font:inherit}select,input{min-height:44px;padding:0 10px;color:#edf3ed;background:#0d1511;border:1px solid #425348;border-radius:5px}input{padding:12px 10px}button{width:100%;min-height:46px;margin-top:14px;color:#0d1210;font-weight:bold;background:#d7ff4d;border:0;border-radius:5px}button:disabled{opacity:.5}.muted{color:#8d9b93;font-size:12px;line-height:1.5}.status{margin-top:14px;color:#d7ff4d;white-space:pre-wrap}</style><main><h1>COURTTRACE 手机上传</h1><p class='muted'>选择比赛后上传多个视频。上传完成后电脑会自动开始分析。</p><section><label>比赛<select id='match'></select></label><label style='margin-top:14px'>视频<input id='files' type='file' accept='video/mp4,video/quicktime,video/webm,.mp4,.mov,.m4v,.webm' multiple></label><button id='upload'>上传并开始分析</button><div id='status' class='status'></div></section></main><script>const token=new URLSearchParams(location.search).get('token');const match=document.querySelector('#match'),files=document.querySelector('#files'),button=document.querySelector('#upload'),status=document.querySelector('#status');async function request(url,options){const response=await fetch(url,options);if(!response.ok)throw new Error((await response.json()).detail||'请求失败');return response.json()}async function boot(){try{const matches=await request(`/api/matches?include_test=false&token=${encodeURIComponent(token)}`);match.innerHTML=matches.map(item=>`<option value="${item.id}">${item.name}</option>`).join('')}catch(error){status.textContent=error.message}}boot();button.onclick=async()=>{if(!match.value||!files.files.length)return status.textContent='请选择比赛和视频';button.disabled=true;status.textContent='正在上传，请保持页面打开...';try{const body=new FormData();for(const file of files.files)body.append('files',file);const result=await request(`/api/matches/${encodeURIComponent(match.value)}/clips?token=${encodeURIComponent(token)}`,{method:'POST',body});if(result.accepted.length){await request(`/api/matches/${encodeURIComponent(match.value)}/analyze?token=${encodeURIComponent(token)}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({clipIds:result.accepted.map(item=>item.id),device:'auto'})})}status.textContent=`上传完成：${result.accepted.length} 个\n跳过重复或不支持：${result.skipped.length} 个\n电脑端已开始分析。`;files.value=''}catch(error){status.textContent=error.message}finally{button.disabled=false}}</script></html>", { media_type: "text/html" })

    """, media_type="text/html")


def stats_for(c: sqlite3.Connection, match_id: str) -> list[dict[str, Any]]:
    rows = c.execute("SELECT e.player_id,e.team_id,e.event_type,e.shot_type,e.points,p.name,p.code,p.number,p.number_confidence,p.number_source,p.number_candidates_json FROM analysis_events e JOIN clips c ON c.id=e.clip_id LEFT JOIN players p ON p.id=e.player_id WHERE c.match_id=? AND e.status='confirmed'", (match_id,)).fetchall()
    grouped: dict[str, dict[str, Any]] = {}
    empty_stats = {"attempts": 0, "makes": 0, "points": 0, "freeThrowAttempts": 0, "freeThrowMakes": 0, "twoPointAttempts": 0, "twoPointMakes": 0, "threePointAttempts": 0, "threePointMakes": 0, "unclassifiedAttempts": 0, "unclassifiedMakes": 0}
    unassigned = {"playerId": None, "teamId": None, "name": "Unassigned", "code": "unassigned", **empty_stats}
    for row in rows:
        item = unassigned if not row["player_id"] else grouped.setdefault(row["player_id"], {"playerId": row["player_id"], "teamId": row["team_id"], "name": row["name"] or row["code"], "code": row["code"], "number": row["number"], "numberConfidence": row["number_confidence"], "numberSource": row["number_source"], "numberCandidates": json.loads(row["number_candidates_json"] or "[]"), **empty_stats})
        is_attempt, is_make = row["event_type"] == "attempt", row["event_type"] == "make"
        item["attempts"] += is_attempt; item["makes"] += is_make
        item["points"] += (row["points"] or 0) if is_make else 0
        prefix = {"freeThrow": "freeThrow", "twoPoint": "twoPoint", "threePoint": "threePoint"}.get(row["shot_type"])
        if prefix:
            item[f"{prefix}Attempts"] += is_attempt
            item[f"{prefix}Makes"] += is_make
        else:
            item["unclassifiedAttempts"] += is_attempt
            item["unclassifiedMakes"] += is_make
    result = list(grouped.values())
    if any(unassigned[k] for k in ("attempts", "makes", "points")): result.append(unassigned)
    return result


def event_payload(r: sqlite3.Row, c: sqlite3.Connection | None = None) -> dict[str, Any]:
    value = camel(r)
    if c is not None:
        if r["player_id"]:
            player = c.execute("SELECT number,number_confidence,number_source,number_candidates_json FROM players WHERE id=?", (r["player_id"],)).fetchone()
            if player:
                value.update({"number": player["number"], "numberConfidence": player["number_confidence"], "numberSource": player["number_source"], "numberCandidates": json.loads(player["number_candidates_json"] or "[]")})
        clip = c.execute("SELECT match_id,filename FROM clips WHERE id=?", (r["clip_id"],)).fetchone()
        if clip:
            value["previewUrl"] = f"/media/{clip['match_id']}/{r['clip_id']}/{clip['filename']}"
        value["teamSource"] = r["team_source"] or ("unassigned" if not r["team_id"] else ("manual" if r["confirmed_by"] == "manual" or r["source"] == "manual" else "ai"))
        value["teamConfidence"] = r["team_confidence"] if "team_confidence" in r.keys() else 0
        value["teamEvidence"] = r["team_evidence"] if "team_evidence" in r.keys() else ""
    return value


def shot_points(shot_type: str | None) -> int | None:
    return {"freeThrow": 1, "twoPoint": 2, "threePoint": 3}.get(shot_type)


def capture_review_sample(c: sqlite3.Connection, event: sqlite3.Row, match_id: str, clip: sqlite3.Row) -> dict[str, Any]:
    existing = c.execute("SELECT id FROM review_samples WHERE event_id=?", (event["id"],)).fetchone()
    if existing:
        return {"id": existing["id"], "created": False}
    sample_id = uuid.uuid4().hex
    sample_dir = CATEGORY_DATA_DIR / match_id / sample_id
    sample_dir.mkdir(parents=True, exist_ok=True)
    source = Path(clip["stored_path"])
    frames: list[str] = []
    try:
        import cv2
        capture = cv2.VideoCapture(str(source))
        fps = capture.get(cv2.CAP_PROP_FPS) or 30
        for index, offset in enumerate((-1.5, -0.5, 0, 0.5, 1.5)):
            capture.set(cv2.CAP_PROP_POS_MSEC, max(0, event["seconds"] + offset) * 1000)
            ok, frame = capture.read()
            if not ok:
                continue
            frame_path = sample_dir / f"frame-{index:02d}.jpg"
            cv2.imwrite(str(frame_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
            frames.append(str(frame_path.relative_to(DATA_DIR)))
        capture.release()
    except Exception:
        frames = []
    metadata = {"frames": frames, "source": "manual-review", "eventType": event["event_type"], "playerId": event["player_id"], "teamId": event["team_id"]}
    c.execute("INSERT INTO review_samples(id,match_id,clip_id,event_id,label,shot_type,player_id,team_id,seconds,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (sample_id, match_id, clip["id"], event["id"], "make", event["shot_type"], event["player_id"], event["team_id"], event["seconds"], json.dumps(metadata), now()))
    return {"id": sample_id, "created": True, "frames": frames}


def automatic_confirmation(candidate: Any, player_id: str | None, team_id: str | None, duration: float | None) -> dict[str, Any]:
    # Automatic confirmation is intentionally disabled for the first team-only workflow.
    return {"status": "pending", "points": None, "confirmed_at": None, "confirmed_by": None, "confirmation_rule": None, "highlight_start": None, "highlight_end": None}


@app.get("/api/matches/{match_id}/workspace")
async def workspace(match_id: str) -> dict[str, Any]:
    with db() as c:
        match = require_match(match_id, c); teams = [team_payload(r) for r in c.execute("SELECT * FROM teams WHERE match_id=?", (match_id,))]; players = [player_payload(c, r) for r in c.execute("SELECT * FROM players WHERE match_id=?", (match_id,))]
        clips = [clip_payload(r) for r in c.execute("SELECT * FROM clips WHERE match_id=?", (match_id,))]; events = [event_payload(r, c) for r in c.execute("SELECT e.* FROM analysis_events e JOIN clips c ON c.id=e.clip_id WHERE c.match_id=? ORDER BY e.seconds", (match_id,))]
        runs = [run_payload(r) for r in c.execute("SELECT * FROM analysis_runs WHERE match_id=? ORDER BY created_at DESC", (match_id,))]
        return {"match": match_payload(c, match), "teams": teams, "players": players, "clips": clips, "events": events, "stats": stats_for(c, match_id), "runs": runs}


@app.get("/api/matches/{match_id}/events")
async def list_events(match_id: str) -> list[dict[str, Any]]:
    return (await workspace(match_id))["events"]


@app.get("/api/matches/{match_id}/scoring")
async def scoring(match_id: str) -> dict[str, Any]:
    with db() as c:
        require_match(match_id, c)
        teams = {row["side"]: team_payload(row) for row in c.execute("SELECT * FROM teams WHERE match_id=?", (match_id,))}
        events = [
            event_payload(row, c)
            for row in c.execute(
                "SELECT e.* FROM analysis_events e JOIN clips cl ON cl.id=e.clip_id "
                "WHERE cl.match_id=? AND e.event_type='make' ORDER BY e.seconds, e.id",
                (match_id,),
            )
        ]
        result: dict[str, Any] = {
            "home": {"team": teams.get("home"), "events": []},
            "away": {"team": teams.get("away"), "events": []},
            "unassigned": [],
        }
        team_sides = {team["id"]: side for side, team in teams.items() if team.get("id")}
        for event in events:
            side = team_sides.get(event.get("teamId"))
            if side in ("home", "away"):
                result[side]["events"].append(event)
            else:
                result["unassigned"].append(event)
        return result


@app.get("/api/matches/{match_id}/players")
async def list_players(match_id: str) -> list[dict[str, Any]]:
    with db() as c:
        require_match(match_id, c)
        return [player_payload(c, r) for r in c.execute("SELECT * FROM players WHERE match_id=? ORDER BY code", (match_id,))]


@app.patch("/api/players/{player_id}")
async def patch_player(player_id: str, data: PlayerPatch) -> dict[str, Any]:
    with db() as c:
        old = c.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
        if not old: raise HTTPException(404, "player not found")
        values = data.model_dump(exclude_unset=True)
        team_id = values.get("team_id", old["team_id"])
        if team_id is not None and not c.execute("SELECT id FROM teams WHERE id=? AND match_id=?", (team_id, old["match_id"])).fetchone():
            raise HTTPException(422, "team does not belong to match")
        fields = {
            "name": values.get("name", old["name"]),
            "number": values.get("number", old["number"]),
            "team_id": team_id,
            "status": values.get("status", old["status"]),
            "identity_type": values.get("identity_type", old["identity_type"]),
        }
        number_source = "manual" if "number" in values else old["number_source"]
        number_confidence = 1 if "number" in values and values["number"] is not None else old["number_confidence"]
        c.execute("UPDATE players SET name=?,number=?,team_id=?,status=?,identity_type=?,number_source=?,number_confidence=? WHERE id=?", (*fields.values(), number_source, number_confidence, player_id))
        return player_payload(c, c.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone())


@app.patch("/api/matches/{match_id}/players/{player_id}")
async def patch_match_player(match_id: str, player_id: str, data: PlayerPatch) -> dict[str, Any]:
    with db() as c:
        require_match(match_id, c)
        if not c.execute("SELECT id FROM players WHERE id=? AND match_id=?", (player_id, match_id)).fetchone():
            raise HTTPException(404, "player not found")
    return await patch_player(player_id, data)


@app.post("/api/matches/{match_id}/players/merge")
async def merge_players(match_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    source_id, target_id = payload.get("sourcePlayerId"), payload.get("targetPlayerId")
    if not source_id or not target_id or source_id == target_id: raise HTTPException(422, "sourceId and targetId are required")
    with db() as c:
        require_match(match_id, c)
        source = c.execute("SELECT id,identity_type,cover_path FROM players WHERE id=? AND match_id=?", (source_id, match_id)).fetchone()
        target = c.execute("SELECT id FROM players WHERE id=? AND match_id=?", (target_id, match_id)).fetchone()
        if not source or not target: raise HTTPException(404, "player not found")
        c.execute("UPDATE analysis_events SET player_id=?,updated_at=? WHERE player_id=?", (target_id, now(), source_id))
        c.execute("UPDATE player_tracks SET player_id=? WHERE player_id=?", (target_id, source_id))
        c.execute("DELETE FROM players WHERE id=?", (source_id,))
        if source and source["identity_type"] in ("temporary", "unconfirmed"):
            delete_cover_file(source["cover_path"])
        return player_payload(c, c.execute("SELECT * FROM players WHERE id=?", (target_id,)).fetchone())


@app.post("/api/players/merge")
async def merge_players_global(payload: dict[str, Any]) -> dict[str, Any]:
    source_id, target_id = payload.get("sourcePlayerId"), payload.get("targetPlayerId")
    with db() as c:
        source = c.execute("SELECT match_id FROM players WHERE id=?", (source_id,)).fetchone() if source_id else None
        target = c.execute("SELECT match_id FROM players WHERE id=?", (target_id,)).fetchone() if target_id else None
        if not source or not target or source["match_id"] != target["match_id"]: raise HTTPException(422, "players must belong to the same match")
    return await merge_players(source["match_id"], payload)


@app.patch("/api/events/{event_id}")
async def patch_event(event_id: str, data: EventPatch) -> dict[str, Any]:
    with db() as c:
        old = c.execute("SELECT * FROM analysis_events WHERE id=?", (event_id,)).fetchone()
        if not old: raise HTTPException(404, "event not found")
        values = data.model_dump(exclude_unset=True); status = values.get("status", old["status"])
        if status not in {"pending", "confirmed", "ignored"}: raise HTTPException(422, "status must be pending, confirmed, or ignored")
        clip = c.execute("SELECT * FROM clips WHERE id=?", (old["clip_id"],)).fetchone()
        event_type = values.get("type", old["event_type"])
        if event_type not in {"attempt", "make"}: raise HTTPException(422, "type must be attempt or make")
        match_id = c.execute("SELECT match_id FROM clips WHERE id=?", (old["clip_id"],)).fetchone()[0]
        for key, table in (("player_id", "players"), ("team_id", "teams")):
            if key in values and values[key] is not None and not c.execute(f"SELECT id FROM {table} WHERE id=? AND match_id=?", (values[key], match_id)).fetchone(): raise HTTPException(422, f"{key} does not belong to match")
        team_id = values["team_id"] if "team_id" in values else old["team_id"]
        if status == "confirmed" and event_type == "make" and not team_id:
            status = "pending"
        shot_type = values.get("shot_type", old["shot_type"])
        shot_type_source = "manual" if "shot_type" in values else old["shot_type_source"]
        points = values.get("points", old["points"])
        if status != "confirmed" or event_type == "attempt": points = None
        elif "shot_type" in values and "points" not in values: points = shot_points(shot_type)
        fields = {"status": status, "player_id": values["player_id"] if "player_id" in values else old["player_id"], "team_id": team_id, "team_source": "manual" if "team_id" in values and team_id else ("unassigned" if "team_id" in values else old["team_source"]), "event_type": event_type, "shot_type": shot_type, "shot_type_source": shot_type_source, "points": points, "confirmed_at": now() if status == "confirmed" else None, "updated_at": now(), "highlight_start": max(0, old["seconds"] - 4) if status == "confirmed" and event_type == "make" else None, "highlight_end": min(clip["duration"] or old["seconds"] + 5, old["seconds"] + 5) if status == "confirmed" and event_type == "make" else None, "confirmed_by": "manual" if status == "confirmed" else None, "confirmation_rule": None}
        c.execute("INSERT INTO event_revisions VALUES(?,?,?,?,?)", (uuid.uuid4().hex, event_id, status, json.dumps(values), now()))
        c.execute("UPDATE analysis_events SET status=?,player_id=?,team_id=?,team_source=?,event_type=?,shot_type=?,shot_type_source=?,points=?,confirmed_at=?,updated_at=?,highlight_start=?,highlight_end=?,confirmed_by=?,confirmation_rule=? WHERE id=?", (*fields.values(), event_id))
        updated = c.execute("SELECT * FROM analysis_events WHERE id=?", (event_id,)).fetchone()
        sample = None
        if status == "confirmed" and event_type == "make":
            sample = capture_review_sample(c, updated, match_id, clip)
        payload = event_payload(updated, c)
        if sample:
            payload["reviewSample"] = sample
        return payload


@app.patch("/api/matches/{match_id}/events/{event_id}")
async def patch_match_event(match_id: str, event_id: str, data: EventPatch) -> dict[str, Any]:
    with db() as c:
        require_match(match_id, c)
        if not c.execute("SELECT e.id FROM analysis_events e JOIN clips c ON c.id=e.clip_id WHERE e.id=? AND c.match_id=?", (event_id, match_id)).fetchone():
            raise HTTPException(404, "event not found")
    return await patch_event(event_id, data)


@app.post("/api/matches/{match_id}/events/manual", status_code=201)
async def manual_event(match_id: str, data: ManualEvent) -> dict[str, Any]:
    with db() as c:
        require_match(match_id, c); clip = c.execute("SELECT * FROM clips WHERE id=? AND match_id=?", (data.clip_id, match_id)).fetchone()
        if not clip: raise HTTPException(404, "clip not found")
        if data.type not in {"attempt", "make"}: raise HTTPException(422, "type must be attempt or make")
        if data.seconds < 0 or (clip["duration"] is not None and data.seconds > clip["duration"]): raise HTTPException(422, "seconds outside clip duration")
        if data.player_id and not c.execute("SELECT id FROM players WHERE id=? AND match_id=?", (data.player_id, match_id)).fetchone(): raise HTTPException(422, "player does not belong to match")
        if data.team_id and not c.execute("SELECT id FROM teams WHERE id=? AND match_id=?", (data.team_id, match_id)).fetchone(): raise HTTPException(422, "team does not belong to match")
        event_id = uuid.uuid4().hex
        start = max(0, data.seconds - 4) if data.type == "make" else None
        end = min(clip["duration"] or data.seconds + 5, data.seconds + 5) if data.type == "make" else None
        points = shot_points(data.shot_type) if data.type == "make" and data.shot_type else data.points
        if data.type == "make" and not data.team_id:
            raise HTTPException(422, "teamId is required for a confirmed make")
        c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,player_id,team_id,shot_type,shot_type_confidence,shot_type_source,points,source,highlight_start,highlight_end,updated_at,confirmed_at,confirmed_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (event_id,data.clip_id,data.type,data.seconds,1,"confirmed",data.player_id,data.team_id,data.shot_type,1,"manual",points,"manual",start,end,now(),now(),"manual"))
        updated = c.execute("SELECT * FROM analysis_events WHERE id=?", (event_id,)).fetchone()
        payload = event_payload(updated, c)
        if data.type == "make":
            payload["reviewSample"] = capture_review_sample(c, updated, match_id, clip)
        return payload


@app.post("/api/matches/{match_id}/events", status_code=201)
async def create_event_alias(match_id: str, data: ManualEvent) -> dict[str, Any]:
    return await manual_event(match_id, data)


@app.get("/api/matches/{match_id}/stats")
async def match_stats(match_id: str) -> list[dict[str, Any]]:
        with db() as c: require_match(match_id, c); return stats_for(c, match_id)


@app.get("/api/players/{player_id}/highlights")
async def player_highlights(player_id: str) -> list[dict[str, Any]]:
    with db() as c:
        return [event_payload(r, c) for r in c.execute("SELECT e.*,c.match_id,c.duration FROM analysis_events e JOIN clips c ON c.id=e.clip_id WHERE e.player_id=? AND e.event_type='make' AND e.status='confirmed' ORDER BY e.seconds", (player_id,))]


@app.get("/api/matches/{match_id}/review-samples")
async def review_samples(match_id: str) -> list[dict[str, Any]]:
    with db() as c:
        require_match(match_id, c)
        rows = c.execute("SELECT * FROM review_samples WHERE match_id=? ORDER BY created_at DESC", (match_id,)).fetchall()
        result = []
        for row in rows:
            value = camel(row)
            value["metadata"] = json.loads(row["metadata_json"] or "{}")
            result.append(value)
        return result


@app.get("/api/matches/{match_id}/clip-review-samples")
async def clip_review_samples(match_id: str) -> list[dict[str, Any]]:
    with db() as c:
        require_match(match_id, c)
        rows = c.execute("SELECT * FROM clip_review_samples WHERE match_id=? ORDER BY created_at DESC", (match_id,)).fetchall()
        result = []
        for row in rows:
            value = camel(row)
            value["frames"] = json.loads(row["frames_json"] or "[]")
            value["metadata"] = json.loads(row["metadata_json"] or "{}")
            result.append(value)
        return result


@app.get("/api/matches/{match_id}/players/{player_id}/highlights")
async def match_player_highlights(match_id: str, player_id: str) -> list[dict[str, Any]]:
    with db() as c:
        require_match(match_id, c)
        return [event_payload(r, c) for r in c.execute("SELECT e.*,c.match_id,c.duration FROM analysis_events e JOIN clips c ON c.id=e.clip_id WHERE c.match_id=? AND e.player_id=? AND e.event_type='make' AND e.status='confirmed' ORDER BY e.seconds", (match_id, player_id))]


def command_available(command: str) -> bool: return resolve_command(command) is not None
def cuda_available() -> bool:
    try:
        import torch  # type: ignore
        return bool(torch.cuda.is_available())
    except ImportError: return False
def torch_installed() -> bool:
    try:
        import torch  # type: ignore
        return bool(torch.__version__)
    except ImportError: return False
def probe_duration(path: Path) -> float | None:
    if not command_available("ffprobe"): return None
    try:
        result = subprocess.run([resolve_command("ffprobe") or "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True, timeout=30, check=True)
        return float(result.stdout.strip())
    except (ValueError, subprocess.SubprocessError): return None
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def delete_cover_file(path: str | None) -> None:
    if not path:
        return
    candidate = Path(path)
    try:
        candidate.unlink(missing_ok=True)
    except OSError:
        pass


def color_distance(rgb: tuple[float, float, float] | None, hex_color: str | None) -> float:
    if rgb is None or not hex_color or not hex_color.startswith("#") or len(hex_color) != 7:
        return 999.0
    try:
        target = tuple(int(hex_color[index:index + 2], 16) for index in (1, 3, 5))
        return sum((rgb[index] - target[index]) ** 2 for index in range(3)) ** 0.5 / 441.7
    except ValueError:
        return 999.0


def appearance_distance(rgb: tuple[float, float, float] | None, row: sqlite3.Row | dict[str, Any]) -> float:
    samples = row["appearance_samples"] or 0
    values = (row["appearance_r"], row["appearance_g"], row["appearance_b"])
    if rgb is None or samples == 0 or any(value is None for value in values):
        return 999.0
    return sum((rgb[i] - values[i]) ** 2 for i in range(3)) ** 0.5 / 441.7


def match_track_candidate(track: Any, players: list[sqlite3.Row | dict[str, Any]], team_id: str | None = None) -> sqlite3.Row | dict[str, Any] | None:
    """Match one clip-local track to the best temporary identity for this match."""
    if getattr(track, "number", None) is not None:
        for player in players:
            keys = player.keys()
            player_number = player["number"] if "number" in keys else None
            player_team = player["team_id"]
            if player_number == track.number and (not team_id or not player_team or player_team == team_id):
                return player
    ranked = []
    for player in players:
        player_team = player["team_id"]
        same_team = bool(team_id and player_team == team_id)
        if team_id and player_team and not same_team:
            continue
        distance = appearance_distance(track.jersey_rgb, player)
        has_color = distance < 999
        if not has_color and (not same_team or track.confidence < 0.75 or track.detections < 5):
            continue
        threshold = 0.30 if same_team else (0.20 if has_color else 0.12)
        if not has_color:
            threshold = 0.12
        if distance > threshold:
            continue
        score = (distance if has_color else 0.4) - (0.035 * min(track.confidence, 1.0)) - (0.01 * min(track.detections, 20) / 20)
        if same_team:
            score -= 0.12
        ranked.append((score, player))
    return min(ranked, key=lambda item: item[0])[1] if ranked else None


def cleanup_match_analysis(match_id: str) -> dict[str, int]:
    """Remove AI output while preserving clips, match setup, and manual fixtures."""
    with db() as c:
        require_match(match_id, c)
        event_rows = c.execute(
            "SELECT e.id,e.status FROM analysis_events e JOIN clips cl ON cl.id=e.clip_id "
            "WHERE cl.match_id=? AND (e.source IS NULL OR e.source NOT IN ('manual','test-fixture'))", (match_id,)
        ).fetchall()
        protected = {row["id"] for row in event_rows if row["status"] == "confirmed" and (c.execute("SELECT 1 FROM event_revisions WHERE event_id=? LIMIT 1", (row["id"],)).fetchone() or c.execute("SELECT 1 FROM review_samples WHERE event_id=? LIMIT 1", (row["id"],)).fetchone())}
        removable = [row["id"] for row in event_rows if row["id"] not in protected]
        if removable:
            marks = ",".join("?" for _ in removable)
            c.execute(f"DELETE FROM event_revisions WHERE event_id IN ({marks})", removable)
            c.execute(f"DELETE FROM analysis_events WHERE id IN ({marks})", removable)
        track_rows = c.execute("SELECT pt.id FROM player_tracks pt JOIN clips cl ON cl.id=pt.clip_id WHERE cl.match_id=? AND cl.status IS NOT NULL", (match_id,)).fetchall()
        c.execute("DELETE FROM player_tracks WHERE clip_id IN (SELECT id FROM clips WHERE match_id=?)", (match_id,))
        player_rows = c.execute("SELECT id,cover_path FROM players WHERE match_id=? AND identity_type IN ('temporary','unconfirmed')", (match_id,)).fetchall()
        if player_rows:
            marks = ",".join("?" for _ in player_rows)
            c.execute(f"DELETE FROM players WHERE id IN ({marks})", [row["id"] for row in player_rows])
            for row in player_rows:
                delete_cover_file(row["cover_path"])
        runs = c.execute("SELECT COUNT(*) FROM analysis_runs WHERE match_id=?", (match_id,)).fetchone()[0]
        c.execute("DELETE FROM analysis_runs WHERE match_id=?", (match_id,))
        c.execute("UPDATE clips SET status='queued',confidence=0 WHERE match_id=?", (match_id,))
        return {"events": len(removable), "protectedEvents": len(protected), "tracks": len(track_rows), "players": len(player_rows), "runs": runs}
def infer_team_id(c: sqlite3.Connection, match_id: str, rgb: tuple[float, float, float] | None) -> str | None:
    teams = [dict(row) for row in c.execute("SELECT id,color FROM teams WHERE match_id=? AND color IS NOT NULL", (match_id,)).fetchall()]
    return classify_team(rgb, teams, learned_team_prototypes(c, match_id)).team_id


def infer_event_team(c: sqlite3.Connection, match_id: str, track: Any) -> tuple[str | None, float, str]:
    teams = [dict(row) for row in c.execute("SELECT id,color FROM teams WHERE match_id=? AND color IS NOT NULL", (match_id,)).fetchall()]
    if not track or track.jersey_rgb is None or not teams:
        return None, 0, "缺少出手轨迹球衣颜色证据"
    decision = classify_team(track.jersey_rgb, teams, learned_team_prototypes(c, match_id))
    if decision.team_id is None:
        return None, decision.confidence, "出手轨迹球衣颜色无法区分球队"
    return decision.team_id, decision.confidence, f"出手轨迹 {track.local_track_key} 的多帧球衣颜色匹配球队"


async def run_analysis(run_id: str, match_id: str, clip_ids: list[str], device: str) -> None:
    errors: dict[str, str] = {}
    try:
        for index, clip_id in enumerate(clip_ids, 1):
            with db() as c: clip = c.execute("SELECT * FROM clips WHERE id=? AND match_id=?", (clip_id, match_id)).fetchone()
            if not clip: continue
            analysis_dir = DATA_DIR / "analysis" / run_id / clip_id
            analysis_dir.mkdir(parents=True, exist_ok=True)
            try:
                inspection = await asyncio.to_thread(ANALYZER.inspect, Path(clip["stored_path"]), device, analysis_dir)
            except TypeError:
                inspection = await asyncio.to_thread(ANALYZER.inspect, Path(clip["stored_path"]), device)
            if inspection.error:
                errors[clip_id] = inspection.error
                with db() as c:
                    c.execute("UPDATE clips SET status='failed' WHERE id=?", (clip_id,))
                    c.execute("UPDATE analysis_runs SET progress=?,completed_clips=?,details_json=? WHERE id=?", (round(index / max(len(clip_ids), 1) * 100, 1), index, json.dumps({"errors": errors}), run_id))
                await publish_event(match_id, "analysis.progress", {"runId": run_id, "completed": index, "total": len(clip_ids), "progress": round(index / max(len(clip_ids), 1) * 100, 1), "errors": errors})
                shutil.rmtree(analysis_dir, ignore_errors=True)
                continue
            with db() as c:
                c.execute("UPDATE clips SET status='review',confidence=? WHERE id=?", (max((e.confidence for e in inspection.events), default=0), clip_id))
                track_players = {}
                existing_players = c.execute("SELECT * FROM players WHERE match_id=? AND identity_type IN ('temporary','unconfirmed')", (match_id,)).fetchall()
                used_player_ids: set[str] = set()
                for track in inspection.tracks:
                    team_id = infer_team_id(c, match_id, track.jersey_rgb)
                    player = match_track_candidate(track, [item for item in existing_players if item["id"] not in used_player_ids], team_id)
                    if player is None:
                        player = {"id": uuid.uuid4().hex, "team_id": team_id}
                        c.execute("INSERT INTO players(id,match_id,team_id,code,name,identity_type,status,confidence,appearance_r,appearance_g,appearance_b,appearance_samples,track_count_total,number,number_confidence,number_source,number_candidates_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (player["id"], match_id, team_id, f"tmp-{uuid.uuid4().hex[:12]}", "", "temporary", "unconfirmed", track.confidence, None, None, None, 0, 0, track.number, track.number_confidence, "ai" if track.number else None, json.dumps(track.number_candidates)))
                        existing_players.append(c.execute("SELECT * FROM players WHERE id=?", (player["id"],)).fetchone())
                    player_id = player["id"]
                    used_player_ids.add(player_id)
                    old = c.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
                    rgb = track.jersey_rgb
                    samples = old["appearance_samples"] or 0
                    if rgb:
                        total = samples + 1
                        appearance = tuple(((old[f"appearance_{channel}"] or 0) * samples + rgb[index]) / total for index, channel in enumerate(("r", "g", "b")))
                        c.execute("UPDATE players SET appearance_r=?,appearance_g=?,appearance_b=?,appearance_samples=?,confidence=MAX(confidence,?),track_count_total=track_count_total+?,team_id=COALESCE(team_id,?) WHERE id=?", (*appearance, total, track.confidence, track.detections, team_id, player_id))
                    else:
                        c.execute("UPDATE players SET confidence=MAX(confidence,?),track_count_total=track_count_total+?,team_id=COALESCE(team_id,?) WHERE id=?", (track.confidence, track.detections, team_id, player_id))
                    old = c.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
                    if track.cover_image_path and track.cover_score > (old["cover_score"] or 0):
                        persistent_path = COVERS_DIR / match_id / f"{player_id}.jpg"
                        persistent_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(track.cover_image_path, persistent_path)
                        c.execute("UPDATE players SET cover_path=?,cover_score=?,cover_source_clip_id=?,cover_source_seconds=? WHERE id=?", (str(persistent_path), track.cover_score, clip_id, (track.cover_frame_index or 0) / 5, player_id))
                    if old["number_source"] != "manual" and track.number_candidates:
                        if track.number:
                            c.execute("UPDATE players SET number=?,number_confidence=?,number_source='ai',number_candidates_json=? WHERE id=?", (track.number, track.number_confidence, json.dumps(track.number_candidates), player_id))
                            side = c.execute("SELECT side FROM teams WHERE id=?", (old["team_id"] or team_id,)).fetchone()
                            numbered_code = f"{side['side'] if side else 'player'}-{track.number}"
                            if not c.execute("SELECT 1 FROM players WHERE match_id=? AND code=? AND id<>?", (match_id, numbered_code, player_id)).fetchone():
                                c.execute("UPDATE players SET code=? WHERE id=? AND identity_type IN ('temporary','unconfirmed')", (numbered_code, player_id))
                        else:
                            c.execute("UPDATE players SET number_candidates_json=? WHERE id=?", (json.dumps(track.number_candidates), player_id))
                    track_players[track.local_track_key] = player_id
                    prior_track = c.execute("SELECT id FROM player_tracks WHERE clip_id=? AND local_track_key=?", (clip_id, track.local_track_key)).fetchone()
                    c.execute("INSERT OR REPLACE INTO player_tracks(id,clip_id,player_id,local_track_key,team_id,confidence) VALUES(?,?,?,?,?,?)", (prior_track["id"] if prior_track else uuid.uuid4().hex, clip_id, player_id, track.local_track_key, team_id, track.confidence))
                current_clip = c.execute("SELECT team_source FROM clips WHERE id=?", (clip_id,)).fetchone()
                if not current_clip or current_clip["team_source"] != "manual":
                    teams = [dict(row) for row in c.execute("SELECT id,color FROM teams WHERE match_id=? ORDER BY side", (match_id,)).fetchall()]
                    decision = classify_clip_team(inspection.tracks, teams, learned_team_prototypes(c, match_id))
                    if decision.team_id is None:
                        c.execute("UPDATE clips SET team_id=NULL,team_source='unresolved',team_confidence=0,team_evidence=? WHERE id=?", (decision.evidence, clip_id))
                    else:
                        c.execute("UPDATE clips SET team_id=?,team_source='ai',team_confidence=?,team_evidence=? WHERE id=?", (decision.team_id, decision.confidence, decision.evidence, clip_id))
                for candidate in inspection.events:
                    event_type = {"投篮": "attempt", "命中": "make"}.get(candidate.event_type, candidate.event_type)
                    fingerprint = f"{clip_id}/{event_type}/{int(candidate.seconds/0.2)}/{candidate.source}"
                    existing = c.execute("SELECT * FROM analysis_events WHERE fingerprint=?", (fingerprint,)).fetchone()
                    player_id = track_players.get(candidate.local_track_key)
                    shooter_track = next((track for track in inspection.tracks if track.local_track_key == candidate.local_track_key), None)
                    inferred_team_id, team_confidence, team_evidence = infer_event_team(c, match_id, shooter_track)
                    confirmation = automatic_confirmation(candidate, player_id, inferred_team_id, clip["duration"])
                    if existing and (existing["confirmed_by"] == "manual" or existing["status"] == "ignored"):
                        continue
                    if existing:
                        update = {
                            "event_type": event_type, "seconds": candidate.seconds, "confidence": candidate.confidence,
                            "description": candidate.description, "source": candidate.source, "run_id": run_id,
                            "local_track_key": candidate.local_track_key, "player_id": player_id, "team_id": inferred_team_id,
                            "team_confidence": team_confidence, "team_evidence": team_evidence,
                            "court_x": candidate.court_x, "court_y": candidate.court_y,
                            "homography_confidence": candidate.homography_confidence, "release_frame": candidate.release_frame,
                            "updated_at": now(), **confirmation,
                        }
                        if existing["shot_type_source"] == "manual":
                            update["shot_type"], update["shot_type_confidence"], update["shot_type_source"] = existing["shot_type"], existing["shot_type_confidence"], existing["shot_type_source"]
                            update["points"] = existing["points"]
                            if confirmation["status"] == "confirmed":
                                update["points"] = existing["points"] if existing["points"] is not None else shot_points(existing["shot_type"])
                        else:
                            update["shot_type"], update["shot_type_confidence"], update["shot_type_source"] = candidate.shot_type, candidate.shot_type_confidence, candidate.shot_type_source
                        revision = {"source": "reanalysis", "before": dict(existing), "after": update}
                        c.execute("INSERT INTO event_revisions VALUES(?,?,?,?,?)", (uuid.uuid4().hex, existing["id"], update["status"], json.dumps(revision), now()))
                        assignments = ",".join(f"{name}=:{name}" for name in update)
                        c.execute(f"UPDATE analysis_events SET {assignments} WHERE id=:id", {**update, "id": existing["id"]})
                    else:
                        c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,description,source,run_id,fingerprint,local_track_key,player_id,team_id,team_confidence,team_evidence,shot_type,shot_type_confidence,shot_type_source,court_x,court_y,homography_confidence,release_frame,updated_at,points,confirmed_at,confirmed_by,confirmation_rule,highlight_start,highlight_end) VALUES(" + ",".join("?" for _ in range(29)) + ")", (f"ai-{uuid.uuid4().hex}",clip_id,event_type,candidate.seconds,candidate.confidence,confirmation["status"],candidate.description,candidate.source,run_id,fingerprint,candidate.local_track_key,player_id,inferred_team_id,team_confidence,team_evidence,candidate.shot_type,candidate.shot_type_confidence,candidate.shot_type_source,candidate.court_x,candidate.court_y,candidate.homography_confidence,candidate.release_frame,now(),confirmation["points"],confirmation["confirmed_at"],confirmation["confirmed_by"],confirmation["confirmation_rule"],confirmation["highlight_start"],confirmation["highlight_end"]))
                progress = round(index / max(len(clip_ids), 1) * 100, 1)
                c.execute("UPDATE analysis_runs SET progress=?,completed_clips=? WHERE id=?", (progress, index, run_id))
                await publish_event(match_id, "analysis.progress", {"runId": run_id, "completed": index, "total": len(clip_ids), "progress": progress})
            shutil.rmtree(analysis_dir, ignore_errors=True)
        with db() as c:
            c.execute("UPDATE analysis_runs SET status=?,progress=100,error=?,details_json=?,finished_at=? WHERE id=?", ("failed" if errors else "completed", "; ".join(errors.values()), json.dumps({"errors": errors}), now(), run_id))
        await publish_event(match_id, "analysis.completed" if not errors else "analysis.failed", {"runId": run_id, "completed": len(clip_ids), "total": len(clip_ids), "progress": 100, "errors": errors})
    except Exception as error:
        with db() as c:
            marks = ",".join("?" for _ in clip_ids)
            if marks:
                c.execute(f"UPDATE clips SET status='failed' WHERE id IN ({marks}) AND status='processing'", clip_ids)
            c.execute("UPDATE analysis_runs SET status='failed',error=?,details_json=?,finished_at=? WHERE id=?", (str(error),json.dumps({"error": str(error)}),now(),run_id))
        await publish_event(match_id, "analysis.failed", {"runId": run_id, "error": str(error)})


@app.post("/api/matches/{match_id}/analyze")
async def analyze(match_id: str, request: AnalyzeRequest, token: str | None = None) -> dict[str, Any]:
    if token is not None:
        require_mobile_token(token)
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        require_match(match_id, c)
        active = c.execute("SELECT id FROM analysis_runs WHERE match_id=? AND status='running' LIMIT 1", (match_id,)).fetchone()
        if active:
            raise HTTPException(409, f"analysis already running: {active['id']}")
        if request.clip_ids:
            marks = ",".join("?" for _ in request.clip_ids)
            rows = c.execute(f"SELECT cl.id,cl.status,cl.team_source FROM clips cl WHERE cl.match_id=? AND cl.id IN ({marks})", [match_id,*request.clip_ids]).fetchall()
            if len(rows) != len(set(request.clip_ids)):
                raise HTTPException(422, "one or more clipIds do not belong to this match")
            clip_ids = [r["id"] for r in rows if r["team_source"] != "manual"]
            active_marks = ",".join("?" for _ in clip_ids)
            active_processing = c.execute(f"SELECT DISTINCT cl.id FROM clips cl WHERE cl.match_id=? AND cl.id IN ({active_marks}) AND cl.status='processing'", [match_id,*clip_ids]).fetchall() if clip_ids else []
            if active_processing:
                raise HTTPException(409, "one or more clips are already processing")
            if clip_ids:
                c.execute(f"UPDATE clips SET status='queued' WHERE match_id=? AND id IN ({active_marks}) AND status='processing'", [match_id,*clip_ids])
        else:
            rows = c.execute("SELECT id FROM clips WHERE match_id=? AND status IN ('queued','failed','interrupted') AND team_source != 'manual'", (match_id,)).fetchall()
            clip_ids = [r["id"] for r in rows]
        run_id = uuid.uuid4().hex; selected = "cuda" if cuda_available() and request.device != "cpu" else "cpu"
        c.execute("INSERT INTO analysis_runs(id,match_id,status,device,total_clips,completed_clips,details_json,created_at,started_at) VALUES(?,?,?,?,?,?,?,?,?)", (run_id,match_id,"completed" if not clip_ids else "running",selected,len(clip_ids),0,"{}",now(),now()))
        if clip_ids:
            marks = ",".join("?" for _ in clip_ids)
            c.execute(f"UPDATE clips SET status='processing' WHERE id IN ({marks})", clip_ids)
    if clip_ids: asyncio.create_task(run_analysis(run_id, match_id, clip_ids, selected))
    await publish_event(match_id, "analysis.started", {"runId": run_id, "total": len(clip_ids), "progress": 0})
    return await task_status(run_id)


@app.get("/api/tasks/{task_id}")
async def task_status(task_id: str) -> dict[str, Any]:
    with db() as c:
        row = c.execute("SELECT * FROM analysis_runs WHERE id=?", (task_id,)).fetchone()
        if not row: raise HTTPException(404, "analysis task not found")
        result = run_payload(row)
        return result


@app.post("/api/matches/{match_id}/cleanup-analysis")
async def cleanup_analysis(match_id: str) -> dict[str, Any]:
    return cleanup_match_analysis(match_id)
