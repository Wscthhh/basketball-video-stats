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
from typing import Annotated, Any, Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .analyzer import BasketballAnalyzer, resolve_command

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "courttrace.sqlite3"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="COURTTRACE Local Analysis API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/media", StaticFiles(directory=UPLOAD_DIR), name="media")
ANALYZER = BasketballAnalyzer()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def init_db() -> None:
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS clips (id TEXT PRIMARY KEY, match_id TEXT NOT NULL, filename TEXT NOT NULL, stored_path TEXT NOT NULL, sha256 TEXT NOT NULL UNIQUE, size_bytes INTEGER NOT NULL, duration REAL, status TEXT NOT NULL DEFAULT 'queued', confidence REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS analysis_events (id TEXT PRIMARY KEY, clip_id TEXT NOT NULL, event_type TEXT NOT NULL, seconds REAL NOT NULL, confidence REAL NOT NULL, status TEXT NOT NULL DEFAULT 'pending', player_id TEXT, description TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '', FOREIGN KEY(clip_id) REFERENCES clips(id));
        CREATE TABLE IF NOT EXISTS matches (id TEXT PRIMARY KEY, name TEXT NOT NULL, played_at TEXT, venue TEXT, status TEXT NOT NULL DEFAULT 'draft', is_test INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS teams (id TEXT PRIMARY KEY, match_id TEXT NOT NULL, side TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', color TEXT, UNIQUE(match_id, side), FOREIGN KEY(match_id) REFERENCES matches(id));
        CREATE TABLE IF NOT EXISTS players (id TEXT PRIMARY KEY, match_id TEXT NOT NULL, team_id TEXT, code TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', number TEXT, identity_type TEXT NOT NULL DEFAULT 'temporary', status TEXT NOT NULL DEFAULT 'unconfirmed', confidence REAL NOT NULL DEFAULT 0, appearance_r REAL, appearance_g REAL, appearance_b REAL, appearance_samples INTEGER NOT NULL DEFAULT 0, track_count_total INTEGER NOT NULL DEFAULT 0, UNIQUE(match_id, code), FOREIGN KEY(match_id) REFERENCES matches(id));
        CREATE TABLE IF NOT EXISTS player_tracks (id TEXT PRIMARY KEY, clip_id TEXT NOT NULL, player_id TEXT NOT NULL, local_track_key TEXT NOT NULL, team_id TEXT, confidence REAL NOT NULL DEFAULT 0, UNIQUE(clip_id, local_track_key), FOREIGN KEY(clip_id) REFERENCES clips(id), FOREIGN KEY(player_id) REFERENCES players(id));
        CREATE TABLE IF NOT EXISTS analysis_runs (id TEXT PRIMARY KEY, match_id TEXT NOT NULL, status TEXT NOT NULL, progress REAL NOT NULL DEFAULT 0, device TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', started_at TEXT, finished_at TEXT, created_at TEXT NOT NULL, version TEXT NOT NULL DEFAULT '1', FOREIGN KEY(match_id) REFERENCES matches(id));
        CREATE TABLE IF NOT EXISTS event_revisions (id TEXT PRIMARY KEY, event_id TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(event_id) REFERENCES analysis_events(id));
        """)
        run_columns = {r["name"] for r in c.execute("PRAGMA table_info(analysis_runs)")}
        for name, definition in {"total_clips": "INTEGER NOT NULL DEFAULT 0", "completed_clips": "INTEGER NOT NULL DEFAULT 0", "details_json": "TEXT NOT NULL DEFAULT '{}'"}.items():
            if name not in run_columns:
                c.execute(f"ALTER TABLE analysis_runs ADD COLUMN {name} {definition}")
        # Existing installations have no parent match table and old event columns.
        for name, definition in {
            "team_id": "TEXT", "points": "INTEGER", "shot_type": "TEXT", "shot_type_confidence": "REAL NOT NULL DEFAULT 0", "shot_type_source": "TEXT", "court_x": "REAL", "court_y": "REAL", "homography_confidence": "REAL NOT NULL DEFAULT 0", "release_frame": "INTEGER", "run_id": "TEXT", "fingerprint": "TEXT", "highlight_start": "REAL", "highlight_end": "REAL", "confirmed_at": "TEXT", "updated_at": "TEXT", "local_track_key": "TEXT"
        }.items():
            if name not in {r["name"] for r in c.execute("PRAGMA table_info(analysis_events)")}:
                c.execute(f"ALTER TABLE analysis_events ADD COLUMN {name} {definition}")
        player_columns = {r["name"] for r in c.execute("PRAGMA table_info(players)")}
        for name, definition in {"appearance_r": "REAL", "appearance_g": "REAL", "appearance_b": "REAL", "appearance_samples": "INTEGER NOT NULL DEFAULT 0", "track_count_total": "INTEGER NOT NULL DEFAULT 0"}.items():
            if name not in player_columns:
                c.execute(f"ALTER TABLE players ADD COLUMN {name} {definition}")
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
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_event_fingerprint ON analysis_events(fingerprint) WHERE fingerprint IS NOT NULL")
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


def row_payload(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def camel(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    names = {"match_id": "matchId", "team_id": "teamId", "player_id": "playerId", "clip_id": "clipId", "run_id": "runId", "event_type": "type", "event_id": "eventId", "shot_type": "shotType", "shot_type_confidence": "shotTypeConfidence", "shot_type_source": "shotTypeSource", "court_x": "courtX", "court_y": "courtY", "homography_confidence": "homographyConfidence", "release_frame": "releaseFrame", "local_track_key": "localTrackKey", "identity_type": "identityType", "is_test": "isTest", "played_at": "playedAt", "created_at": "createdAt", "updated_at": "updatedAt", "confirmed_at": "confirmedAt", "highlight_start": "highlightStart", "highlight_end": "highlightEnd", "stored_path": "storedPath", "size_bytes": "sizeBytes", "preview_url": "previewUrl", "started_at": "startedAt", "finished_at": "finishedAt"}
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
    team = c.execute("SELECT side,color FROM teams WHERE id=?", (row["team_id"],)).fetchone() if row["team_id"] else None
    value["displayName"] = row["name"] or row["code"]
    value["team"] = team["side"] if team else None
    value["color"] = team["color"] if team else None
    value["tracksCount"] = c.execute("SELECT COUNT(*) FROM player_tracks WHERE player_id=?", (row["id"],)).fetchone()[0]
    value["tracks"] = value["tracksCount"]
    return value


def clip_payload(row: sqlite3.Row) -> dict[str, Any]:
    value = camel(row)
    value["name"] = row["filename"]
    value["previewUrl"] = f"/media/{row['match_id']}/{row['id']}/{row['filename']}"
    return value


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
    name: str = Field(min_length=1, max_length=120)
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


@app.get("/api/matches")
async def list_matches(include_test: bool = True) -> list[dict[str, Any]]:
    with db() as c:
        rows = c.execute(
            "SELECT * FROM matches ORDER BY played_at DESC, created_at DESC" if include_test
            else "SELECT * FROM matches WHERE is_test=0 ORDER BY played_at DESC, created_at DESC"
        ).fetchall()
    with db() as c: return [match_payload(c, r) for r in rows]


@app.post("/api/matches", status_code=201)
async def create_match(data: MatchInput) -> dict[str, Any]:
    for team in (data.home_team, data.away_team):
        if not str(team.get("name", "")).strip():
            raise HTTPException(422, "both team names are required")
    match_id = uuid.uuid4().hex
    with db() as c:
        c.execute("INSERT INTO matches VALUES(?,?,?,?,?,?,?)", (match_id, data.name, data.played_at, data.venue, data.status, int(data.is_test), now()))
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


@app.post("/api/matches/{match_id}/clips")
async def upload_clips(match_id: str, files: Annotated[list[UploadFile], File(...)]) -> dict[str, Any]:
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
    return {"accepted": accepted, "skipped": skipped}


def stats_for(c: sqlite3.Connection, match_id: str) -> list[dict[str, Any]]:
    rows = c.execute("SELECT e.player_id,e.team_id,e.event_type,e.shot_type,e.points,p.name,p.code FROM analysis_events e JOIN clips c ON c.id=e.clip_id LEFT JOIN players p ON p.id=e.player_id WHERE c.match_id=? AND e.status='confirmed'", (match_id,)).fetchall()
    grouped: dict[str, dict[str, Any]] = {}
    empty_stats = {"attempts": 0, "makes": 0, "points": 0, "freeThrowAttempts": 0, "freeThrowMakes": 0, "twoPointAttempts": 0, "twoPointMakes": 0, "threePointAttempts": 0, "threePointMakes": 0, "unclassifiedAttempts": 0, "unclassifiedMakes": 0}
    unassigned = {"playerId": None, "teamId": None, "name": "Unassigned", "code": "unassigned", **empty_stats}
    for row in rows:
        item = unassigned if not row["player_id"] else grouped.setdefault(row["player_id"], {"playerId": row["player_id"], "teamId": row["team_id"], "name": row["name"] or row["code"], "code": row["code"], **empty_stats})
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


def event_payload(r: sqlite3.Row) -> dict[str, Any]: return camel(r)


def shot_points(shot_type: str | None) -> int | None:
    return {"freeThrow": 1, "twoPoint": 2, "threePoint": 3}.get(shot_type)


@app.get("/api/matches/{match_id}/workspace")
async def workspace(match_id: str) -> dict[str, Any]:
    with db() as c:
        match = require_match(match_id, c); teams = [team_payload(r) for r in c.execute("SELECT * FROM teams WHERE match_id=?", (match_id,))]; players = [player_payload(c, r) for r in c.execute("SELECT * FROM players WHERE match_id=?", (match_id,))]
        clips = [clip_payload(r) for r in c.execute("SELECT * FROM clips WHERE match_id=?", (match_id,))]; events = [event_payload(r) for r in c.execute("SELECT e.* FROM analysis_events e JOIN clips c ON c.id=e.clip_id WHERE c.match_id=? ORDER BY e.seconds", (match_id,))]
        runs = [run_payload(r) for r in c.execute("SELECT * FROM analysis_runs WHERE match_id=? ORDER BY created_at DESC", (match_id,))]
        return {"match": match_payload(c, match), "teams": teams, "players": players, "clips": clips, "events": events, "stats": stats_for(c, match_id), "runs": runs}


@app.get("/api/matches/{match_id}/events")
async def list_events(match_id: str) -> list[dict[str, Any]]:
    return (await workspace(match_id))["events"]


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
        c.execute("UPDATE players SET name=?,number=?,team_id=?,status=?,identity_type=? WHERE id=?", (*fields.values(), player_id))
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
        source = c.execute("SELECT id FROM players WHERE id=? AND match_id=?", (source_id, match_id)).fetchone()
        target = c.execute("SELECT id FROM players WHERE id=? AND match_id=?", (target_id, match_id)).fetchone()
        if not source or not target: raise HTTPException(404, "player not found")
        c.execute("UPDATE analysis_events SET player_id=?,updated_at=? WHERE player_id=?", (target_id, now(), source_id))
        c.execute("UPDATE player_tracks SET player_id=? WHERE player_id=?", (target_id, source_id))
        c.execute("DELETE FROM players WHERE id=?", (source_id,))
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
        clip = c.execute("SELECT duration FROM clips WHERE id=?", (old["clip_id"],)).fetchone()
        event_type = values.get("type", old["event_type"])
        if event_type not in {"attempt", "make"}: raise HTTPException(422, "type must be attempt or make")
        match_id = c.execute("SELECT match_id FROM clips WHERE id=?", (old["clip_id"],)).fetchone()[0]
        for key, table in (("player_id", "players"), ("team_id", "teams")):
            if key in values and values[key] is not None and not c.execute(f"SELECT id FROM {table} WHERE id=? AND match_id=?", (values[key], match_id)).fetchone(): raise HTTPException(422, f"{key} does not belong to match")
        shot_type = values.get("shot_type", old["shot_type"])
        shot_type_source = "manual" if "shot_type" in values else old["shot_type_source"]
        points = values.get("points", old["points"])
        if event_type == "attempt": points = None
        elif "shot_type" in values and "points" not in values: points = shot_points(shot_type)
        fields = {"status": status, "player_id": values["player_id"] if "player_id" in values else old["player_id"], "team_id": values["team_id"] if "team_id" in values else old["team_id"], "event_type": event_type, "shot_type": shot_type, "shot_type_source": shot_type_source, "points": points, "confirmed_at": now() if status == "confirmed" else old["confirmed_at"], "updated_at": now(), "highlight_start": max(0, old["seconds"] - 4) if status == "confirmed" and event_type == "make" else None, "highlight_end": min(clip["duration"] or old["seconds"] + 5, old["seconds"] + 5) if status == "confirmed" and event_type == "make" else None}
        c.execute("INSERT INTO event_revisions VALUES(?,?,?,?,?)", (uuid.uuid4().hex, event_id, status, json.dumps(values), now()))
        c.execute("UPDATE analysis_events SET status=?,player_id=?,team_id=?,event_type=?,shot_type=?,shot_type_source=?,points=?,confirmed_at=?,updated_at=?,highlight_start=?,highlight_end=? WHERE id=?", (*fields.values(), event_id))
        return event_payload(c.execute("SELECT * FROM analysis_events WHERE id=?", (event_id,)).fetchone())


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
        c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,player_id,team_id,shot_type,shot_type_confidence,shot_type_source,points,source,highlight_start,highlight_end,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (event_id,data.clip_id,data.type,data.seconds,1,"confirmed",data.player_id,data.team_id,data.shot_type,1,"manual",points,"manual",start,end,now()))
        return event_payload(c.execute("SELECT * FROM analysis_events WHERE id=?", (event_id,)).fetchone())


@app.post("/api/matches/{match_id}/events", status_code=201)
async def create_event_alias(match_id: str, data: ManualEvent) -> dict[str, Any]:
    return await manual_event(match_id, data)


@app.get("/api/matches/{match_id}/stats")
async def match_stats(match_id: str) -> list[dict[str, Any]]:
        with db() as c: require_match(match_id, c); return stats_for(c, match_id)


@app.get("/api/players/{player_id}/highlights")
async def player_highlights(player_id: str) -> list[dict[str, Any]]:
    with db() as c:
        return [event_payload(r) for r in c.execute("SELECT e.*,c.match_id,c.duration FROM analysis_events e JOIN clips c ON c.id=e.clip_id WHERE e.player_id=? AND e.event_type='make' AND e.status='confirmed' ORDER BY e.seconds", (player_id,))]


@app.get("/api/matches/{match_id}/players/{player_id}/highlights")
async def match_player_highlights(match_id: str, player_id: str) -> list[dict[str, Any]]:
    with db() as c:
        require_match(match_id, c)
        return [event_payload(r) for r in c.execute("SELECT e.*,c.match_id,c.duration FROM analysis_events e JOIN clips c ON c.id=e.clip_id WHERE c.match_id=? AND e.player_id=? AND e.event_type='make' AND e.status='confirmed' ORDER BY e.seconds", (match_id, player_id))]


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
        protected = {row["id"] for row in event_rows if row["status"] == "confirmed" and c.execute("SELECT 1 FROM event_revisions WHERE event_id=? LIMIT 1", (row["id"],)).fetchone()}
        removable = [row["id"] for row in event_rows if row["id"] not in protected]
        if removable:
            marks = ",".join("?" for _ in removable)
            c.execute(f"DELETE FROM event_revisions WHERE event_id IN ({marks})", removable)
            c.execute(f"DELETE FROM analysis_events WHERE id IN ({marks})", removable)
        track_rows = c.execute("SELECT pt.id FROM player_tracks pt JOIN clips cl ON cl.id=pt.clip_id WHERE cl.match_id=? AND cl.status IS NOT NULL", (match_id,)).fetchall()
        c.execute("DELETE FROM player_tracks WHERE clip_id IN (SELECT id FROM clips WHERE match_id=?)", (match_id,))
        player_rows = c.execute("SELECT id FROM players WHERE match_id=? AND identity_type IN ('temporary','unconfirmed')", (match_id,)).fetchall()
        if player_rows:
            marks = ",".join("?" for _ in player_rows)
            c.execute(f"DELETE FROM players WHERE id IN ({marks})", [row["id"] for row in player_rows])
        runs = c.execute("SELECT COUNT(*) FROM analysis_runs WHERE match_id=?", (match_id,)).fetchone()[0]
        c.execute("DELETE FROM analysis_runs WHERE match_id=?", (match_id,))
        c.execute("UPDATE clips SET status='queued',confidence=0 WHERE match_id=?", (match_id,))
        return {"events": len(removable), "protectedEvents": len(protected), "tracks": len(track_rows), "players": len(player_rows), "runs": runs}
def infer_team_id(c: sqlite3.Connection, match_id: str, rgb: tuple[float, float, float] | None) -> str | None:
    teams = c.execute("SELECT id,color FROM teams WHERE match_id=? AND color IS NOT NULL", (match_id,)).fetchall()
    if not rgb or len(teams) < 2:
        return None
    ranked = sorted((color_distance(rgb, team["color"]), team["id"]) for team in teams)
    if ranked[0][0] < 0.7 and ranked[1][0] - ranked[0][0] >= 0.08:
        return ranked[0][1]
    return None


async def run_analysis(run_id: str, match_id: str, clip_ids: list[str], device: str) -> None:
    errors: dict[str, str] = {}
    try:
        for index, clip_id in enumerate(clip_ids, 1):
            with db() as c: clip = c.execute("SELECT * FROM clips WHERE id=? AND match_id=?", (clip_id, match_id)).fetchone()
            if not clip: continue
            inspection = await asyncio.to_thread(ANALYZER.inspect, Path(clip["stored_path"]), device)
            if inspection.error:
                errors[clip_id] = inspection.error
                with db() as c:
                    c.execute("UPDATE clips SET status='failed' WHERE id=?", (clip_id,))
                    c.execute("UPDATE analysis_runs SET progress=?,completed_clips=?,details_json=? WHERE id=?", (round(index / max(len(clip_ids), 1) * 100, 1), index, json.dumps({"errors": errors}), run_id))
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
                        c.execute("INSERT INTO players(id,match_id,team_id,code,name,identity_type,status,confidence,appearance_r,appearance_g,appearance_b,appearance_samples,track_count_total) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (player["id"], match_id, team_id, f"tmp-{uuid.uuid4().hex[:12]}", "", "temporary", "unconfirmed", track.confidence, None, None, None, 0, 0))
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
                    track_players[track.local_track_key] = player_id
                    prior_track = c.execute("SELECT id FROM player_tracks WHERE clip_id=? AND local_track_key=?", (clip_id, track.local_track_key)).fetchone()
                    c.execute("INSERT OR REPLACE INTO player_tracks(id,clip_id,player_id,local_track_key,team_id,confidence) VALUES(?,?,?,?,?,?)", (prior_track["id"] if prior_track else uuid.uuid4().hex, clip_id, player_id, track.local_track_key, team_id, track.confidence))
                for candidate in inspection.events:
                    event_type = {"投篮": "attempt", "命中": "make"}.get(candidate.event_type, candidate.event_type)
                    fingerprint = f"{clip_id}/{event_type}/{int(candidate.seconds/0.2)}/{candidate.source}"
                    existing = c.execute("SELECT id,status,shot_type_source FROM analysis_events WHERE fingerprint=?", (fingerprint,)).fetchone()
                    event_team_id = c.execute("SELECT team_id FROM players WHERE id=?", (track_players.get(candidate.local_track_key),)).fetchone() if candidate.local_track_key else None
                    inferred_team_id = event_team_id["team_id"] if event_team_id else None
                    if existing and existing["status"] in {"confirmed", "ignored"}: continue
                    if existing:
                        if existing["shot_type_source"] == "manual":
                            c.execute("UPDATE analysis_events SET event_type=?,seconds=?,confidence=?,description=?,source=?,run_id=?,local_track_key=?,player_id=?,team_id=?,updated_at=? WHERE id=?", (event_type,candidate.seconds,candidate.confidence,candidate.description,candidate.source,run_id,candidate.local_track_key,track_players.get(candidate.local_track_key),inferred_team_id,now(),existing["id"]))
                        else:
                            c.execute("UPDATE analysis_events SET event_type=?,seconds=?,confidence=?,description=?,source=?,run_id=?,local_track_key=?,player_id=?,team_id=?,shot_type=?,shot_type_confidence=?,shot_type_source=?,court_x=?,court_y=?,homography_confidence=?,release_frame=?,updated_at=? WHERE id=?", (event_type,candidate.seconds,candidate.confidence,candidate.description,candidate.source,run_id,candidate.local_track_key,track_players.get(candidate.local_track_key),inferred_team_id,candidate.shot_type,candidate.shot_type_confidence,candidate.shot_type_source,candidate.court_x,candidate.court_y,candidate.homography_confidence,candidate.release_frame,now(),existing["id"]))
                    else:
                        c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,description,source,run_id,fingerprint,local_track_key,player_id,team_id,shot_type,shot_type_confidence,shot_type_source,court_x,court_y,homography_confidence,release_frame,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (f"ai-{uuid.uuid4().hex}",clip_id,event_type,candidate.seconds,candidate.confidence,"pending",candidate.description,candidate.source,run_id,fingerprint,candidate.local_track_key,track_players.get(candidate.local_track_key),inferred_team_id,candidate.shot_type,candidate.shot_type_confidence,candidate.shot_type_source,candidate.court_x,candidate.court_y,candidate.homography_confidence,candidate.release_frame,now()))
                c.execute("UPDATE analysis_runs SET progress=?,completed_clips=? WHERE id=?", (round(index / max(len(clip_ids), 1) * 100, 1), index, run_id))
        with db() as c:
            c.execute("UPDATE analysis_runs SET status=?,progress=100,error=?,details_json=?,finished_at=? WHERE id=?", ("failed" if errors else "completed", "; ".join(errors.values()), json.dumps({"errors": errors}), now(), run_id))
    except Exception as error:
        with db() as c:
            marks = ",".join("?" for _ in clip_ids)
            if marks:
                c.execute(f"UPDATE clips SET status='failed' WHERE id IN ({marks}) AND status='processing'", clip_ids)
            c.execute("UPDATE analysis_runs SET status='failed',error=?,details_json=?,finished_at=? WHERE id=?", (str(error),json.dumps({"error": str(error)}),now(),run_id))


@app.post("/api/matches/{match_id}/analyze")
async def analyze(match_id: str, request: AnalyzeRequest) -> dict[str, Any]:
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        require_match(match_id, c)
        active = c.execute("SELECT id FROM analysis_runs WHERE match_id=? AND status='running' LIMIT 1", (match_id,)).fetchone()
        if active:
            raise HTTPException(409, f"analysis already running: {active['id']}")
        if request.clip_ids:
            marks = ",".join("?" for _ in request.clip_ids)
            rows = c.execute(f"SELECT id,status FROM clips WHERE match_id=? AND id IN ({marks})", [match_id,*request.clip_ids]).fetchall()
            if len(rows) != len(set(request.clip_ids)):
                raise HTTPException(422, "one or more clipIds do not belong to this match")
            if any(row["status"] == "processing" for row in rows):
                raise HTTPException(409, "one or more clips are already processing")
        else: rows = c.execute("SELECT id FROM clips WHERE match_id=? AND status IN ('queued','failed','interrupted')", (match_id,)).fetchall()
        clip_ids = [r["id"] for r in rows]; run_id = uuid.uuid4().hex; selected = "cuda" if cuda_available() and request.device != "cpu" else "cpu"
        c.execute("INSERT INTO analysis_runs(id,match_id,status,device,total_clips,completed_clips,details_json,created_at,started_at) VALUES(?,?,?,?,?,?,?,?,?)", (run_id,match_id,"completed" if not clip_ids else "running",selected,len(clip_ids),0,"{}",now(),now()))
        if clip_ids:
            marks = ",".join("?" for _ in clip_ids)
            c.execute(f"UPDATE clips SET status='processing' WHERE id IN ({marks})", clip_ids)
    if clip_ids: asyncio.create_task(run_analysis(run_id, match_id, clip_ids, selected))
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
