from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "courttrace.sqlite3"
UPLOAD_DIR = ROOT / "data" / "uploads"
MATCH_ID = "integration-test"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def consolidate_test_matches(connection: sqlite3.Connection) -> None:
    rows = connection.execute("SELECT id FROM matches WHERE is_test=1 AND id<>?", (MATCH_ID,)).fetchall()
    for row in rows:
        match_id = row["id"]
        clips = connection.execute("SELECT * FROM clips WHERE match_id=?", (match_id,)).fetchall()
        clip_ids = [item["id"] for item in clips]
        event_ids = [item["id"] for item in connection.execute(
            "SELECT e.id FROM analysis_events e JOIN clips c ON c.id=e.clip_id WHERE c.match_id=?", (match_id,)
        )]
        for event_id in event_ids:
            connection.execute("DELETE FROM event_revisions WHERE event_id=?", (event_id,))
        for clip_id in clip_ids:
            connection.execute("DELETE FROM analysis_events WHERE clip_id=?", (clip_id,))
            connection.execute("DELETE FROM player_tracks WHERE clip_id=?", (clip_id,))
        connection.execute("DELETE FROM analysis_runs WHERE match_id=?", (match_id,))
        connection.execute("DELETE FROM players WHERE match_id=?", (match_id,))
        connection.execute("DELETE FROM teams WHERE match_id=?", (match_id,))
        connection.execute("DELETE FROM matches WHERE id=?", (match_id,))
        for clip in clips:
            source = Path(clip["stored_path"]).parent
            destination = UPLOAD_DIR / MATCH_ID / clip["id"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.exists() and source.resolve() != destination.resolve():
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.move(str(source), str(destination))
            stored_path = destination / clip["filename"]
            connection.execute("UPDATE clips SET match_id=?,stored_path=? WHERE id=?", (MATCH_ID, str(stored_path), clip["id"]))
        shutil.rmtree(UPLOAD_DIR / match_id, ignore_errors=True)


def seed() -> None:
    if not DB_PATH.exists():
        raise SystemExit("Database not found. Start the backend once before seeding test data.")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    with connection:
        consolidate_test_matches(connection)
        connection.execute(
            "INSERT OR IGNORE INTO matches(id,name,played_at,venue,status,is_test,created_at) VALUES(?,?,?,?,?,?,?)",
            (MATCH_ID, "测试赛 · 城南火焰 vs 江北疾风", "2026-08-28T19:30", "城市篮球馆 1 号场", "completed", 1, now()),
        )
        connection.execute(
            "UPDATE matches SET name=?,played_at=?,venue=?,status='completed',is_test=1 WHERE id=?",
            ("测试赛 · 城南火焰 vs 江北疾风", "2026-08-28T19:30", "城市篮球馆 1 号场", MATCH_ID),
        )
        teams = {
            "home": (f"{MATCH_ID}-home", "城南火焰", "#d7ff4d"),
            "away": (f"{MATCH_ID}-away", "江北疾风", "#ff765c"),
        }
        for side, (team_id, name, color) in teams.items():
            connection.execute(
                "INSERT INTO teams(id,match_id,side,name,color) VALUES(?,?,?,?,?) ON CONFLICT(match_id,side) DO UPDATE SET name=excluded.name,color=excluded.color",
                (team_id, MATCH_ID, side, name, color),
            )

        roster = [
            ("demo-h07", teams["home"][0], "H-07", "林远", "07"),
            ("demo-h11", teams["home"][0], "H-11", "周野", "11"),
            ("demo-h12", teams["home"][0], "H-12", "陈屿", "12"),
            ("demo-h21", teams["home"][0], "H-21", "赵川", "21"),
            ("demo-h33", teams["home"][0], "H-33", "许晨", "33"),
            ("demo-a05", teams["away"][0], "A-05", "沈锋", "05"),
            ("demo-a09", teams["away"][0], "A-09", "秦越", "09"),
            ("demo-a18", teams["away"][0], "A-18", "顾航", "18"),
            ("demo-a23", teams["away"][0], "A-23", "唐骁", "23"),
            ("demo-a30", teams["away"][0], "A-30", "韩松", "30"),
        ]
        for player_id, team_id, code, name, number in roster:
            connection.execute(
                "INSERT INTO players(id,match_id,team_id,code,name,number,identity_type,status,confidence) VALUES(?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET team_id=excluded.team_id,name=excluded.name,number=excluded.number,identity_type='manual',status='confirmed',confidence=excluded.confidence",
                (player_id, MATCH_ID, team_id, code, name, number, "manual", "confirmed", 1.0),
            )

        clips = connection.execute("SELECT * FROM clips WHERE match_id=? ORDER BY created_at", (MATCH_ID,)).fetchall()
        if not clips:
            print("Test match and roster seeded. No integration-test clip exists, so events were skipped.")
            return

        for clip in clips:
            fixture_event_ids = [row["id"] for row in connection.execute(
                "SELECT id FROM analysis_events WHERE clip_id=? AND source='test-fixture'", (clip["id"],)
            )]
            for event_id in fixture_event_ids:
                connection.execute("DELETE FROM event_revisions WHERE event_id=?", (event_id,))
            connection.execute("DELETE FROM analysis_events WHERE clip_id=? AND source='test-fixture'", (clip["id"],))
        timeline = [
            ("demo-e01", "attempt", "threePoint", .08, "demo-h07", teams["home"][0], None, "弧顶持球后急停出手"),
            ("demo-e02", "make", "threePoint", .12, "demo-h07", teams["home"][0], 3, "篮球穿过篮筐区域，三分命中"),
            ("demo-e03", "attempt", "threePoint", .20, "demo-a23", teams["away"][0], None, "右侧底角接球出手"),
            ("demo-e04", "make", "threePoint", .25, "demo-a23", teams["away"][0], 3, "右侧底角三分命中"),
            ("demo-e05", "attempt", "twoPoint", .34, "demo-h12", teams["home"][0], None, "突破至篮下完成出手"),
            ("demo-e06", "make", "twoPoint", .39, "demo-h12", teams["home"][0], 2, "篮下出手命中"),
            ("demo-e07", "attempt", "twoPoint", .48, "demo-a05", teams["away"][0], None, "中距离急停跳投"),
            ("demo-e08", "attempt", "threePoint", .57, "demo-h21", teams["home"][0], None, "左侧 45 度外线出手"),
            ("demo-e09", "make", "threePoint", .62, "demo-h21", teams["home"][0], 3, "左侧外线命中"),
            ("demo-e10", "attempt", "twoPoint", .70, "demo-a18", teams["away"][0], None, "快攻上篮出手"),
            ("demo-e11", "make", "twoPoint", .75, "demo-a18", teams["away"][0], 2, "快攻上篮命中"),
            ("demo-e12", "attempt", "twoPoint", .83, "demo-h11", teams["home"][0], None, "罚球线附近跳投"),
            ("demo-e13", "make", "twoPoint", .88, "demo-h11", teams["home"][0], 2, "中距离投篮命中"),
            ("demo-e14", "attempt", "threePoint", .94, "demo-a30", teams["away"][0], None, "左侧底角出手，等待复核"),
            ("demo-e15", "attempt", "freeThrow", .46, "demo-h33", teams["home"][0], None, "罚球出手"),
            ("demo-e16", "make", "freeThrow", .51, "demo-h33", teams["home"][0], 1, "罚球命中"),
        ]
        for index, (event_id, event_type, shot_type, ratio, player_id, team_id, points, description) in enumerate(timeline):
            clip = clips[index % len(clips)]
            duration = float(clip["duration"] or 10)
            seconds = min(max(duration * ratio, 0), duration)
            status = "pending" if event_id == "demo-e14" else "confirmed"
            start = max(0, seconds - 4) if event_type == "make" else None
            end = min(duration, seconds + 5) if event_type == "make" else None
            connection.execute(
                "INSERT OR REPLACE INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,player_id,description,source,team_id,shot_type,shot_type_confidence,shot_type_source,points,fingerprint,highlight_start,highlight_end,confirmed_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (event_id, clip["id"], event_type, seconds, .96 - index * .01, status, player_id, description, "test-fixture", team_id, shot_type, 1, "manual", points, f"test-fixture/{event_id}", start, end, now() if status == "confirmed" else None, now()),
            )

        connection.execute(
            "INSERT OR REPLACE INTO analysis_runs(id,match_id,status,progress,device,error,started_at,finished_at,created_at,version,total_clips,completed_clips,details_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("demo-run-completed", MATCH_ID, "completed", 100, "cuda", "", now(), now(), now(), "fixture-1", len(clips), len(clips), json.dumps({"fixture": True, "events": len(timeline), "clips": len(clips)})),
        )
        connection.execute("UPDATE clips SET status='review',confidence=.96 WHERE match_id=?", (MATCH_ID,))
    print("Detailed integration-test match seeded successfully.")


if __name__ == "__main__":
    seed()
