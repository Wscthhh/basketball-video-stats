import builtins
import asyncio
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.main as main
from backend.analyzer import AnalysisResult, BasketballAnalyzer, InspectionResult, TrackCandidate


class AutomaticConfirmationTest(unittest.TestCase):
    def candidate(self, **changes):
        values = {
            "event_type": "make",
            "confidence": .89,
            "source": "ball-hoop-crossing",
            "shot_type": "threePoint",
            "shot_type_confidence": .63,
            "seconds": 8,
        }
        values.update(changes)
        return SimpleNamespace(**values)

    def test_high_confidence_make_stays_pending(self) -> None:
        result = main.automatic_confirmation(self.candidate(), "player", "team", 20)
        self.assertEqual(result["status"], "pending")
        self.assertIsNone(result["points"])
        self.assertIsNone(result["confirmed_by"])

    def test_make_must_meet_every_auto_confirmation_condition(self) -> None:
        cases = (
            (self.candidate(confidence=.879), "player", "team"),
            (self.candidate(event_type="attempt"), "player", "team"),
            (self.candidate(source="ball-trajectory"), "player", "team"),
            (self.candidate(shot_type=None), "player", "team"),
            (self.candidate(shot_type_confidence=.619), "player", "team"),
            (self.candidate(), None, "team"),
            (self.candidate(), "player", None),
        )
        for candidate, player_id, team_id in cases:
            with self.subTest(candidate=vars(candidate), player_id=player_id, team_id=team_id):
                result = main.automatic_confirmation(candidate, player_id, team_id, 20)
                self.assertEqual(result["status"], "pending")
                self.assertIsNone(result["points"])
                self.assertIsNone(result["confirmed_by"])


class OcrTest(unittest.TestCase):
    def test_missing_paddleocr_falls_back_without_raising(self) -> None:
        analyzer = BasketballAnalyzer.__new__(BasketballAnalyzer)
        analyzer._ocr = None
        analyzer._ocr_attempted = False
        analyzer._ocr_error = ""
        real_import = builtins.__import__

        def blocked_import(name, *args, **kwargs):
            if name == "paddleocr":
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=blocked_import):
            self.assertIsNone(analyzer._get_ocr())
        self.assertTrue(analyzer._ocr_attempted)
        self.assertIn("not installed", analyzer._ocr_error)

    def test_v3_results_confirm_number_after_five_matching_frames(self) -> None:
        class FakeOcr:
            def predict(self, input):
                return [{"res": {"rec_texts": ["#23"], "rec_scores": [.84]}}]

        analyzer = BasketballAnalyzer.__new__(BasketballAnalyzer)
        analyzer._ocr = FakeOcr()
        analyzer._ocr_attempted = True
        analyzer._ocr_error = ""
        track = TrackCandidate("local-001", .9, 8)
        players = [{"local_track_key": track.local_track_key, "frame": float(index), "x1": 0, "y1": 0, "x2": 20, "y2": 60} for index in range(10)]
        with patch.object(BasketballAnalyzer, "_upper_body_crop", return_value=object()) as crop:
            analyzer._recognize_track_numbers([track], players, [Path(f"{index}.jpg") for index in range(10)])
        self.assertEqual(crop.call_count, 8)
        self.assertEqual(track.number, "23")
        self.assertEqual(track.number_confidence, .84)
        self.assertEqual(track.number_candidates, [{"number": "23", "votes": 8, "confidence": .84}])


class NumberIdentityTest(unittest.TestCase):
    def test_number_reuses_temporary_player_on_same_team(self) -> None:
        players = [
            {"id": "home-23", "team_id": "home", "number": "23"},
            {"id": "away-23", "team_id": "away", "number": "23"},
        ]
        track = SimpleNamespace(number="23", jersey_rgb=None, confidence=.9, detections=8)
        self.assertEqual(main.match_track_candidate(track, players, "home")["id"], "home-23")
        self.assertEqual(main.match_track_candidate(track, players, "away")["id"], "away-23")


class MigrationTest(unittest.TestCase):
    def test_old_database_receives_ocr_and_confirmation_columns(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            old_path = main.DB_PATH
            main.DB_PATH = Path(directory) / "old.sqlite3"
            try:
                connection = sqlite3.connect(main.DB_PATH)
                connection.executescript("""
                    CREATE TABLE players (id TEXT PRIMARY KEY, match_id TEXT NOT NULL, team_id TEXT, code TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', number TEXT, identity_type TEXT NOT NULL DEFAULT 'temporary', status TEXT NOT NULL DEFAULT 'unconfirmed', confidence REAL NOT NULL DEFAULT 0, UNIQUE(match_id, code));
                    CREATE TABLE analysis_events (id TEXT PRIMARY KEY, clip_id TEXT NOT NULL, event_type TEXT NOT NULL, seconds REAL NOT NULL, confidence REAL NOT NULL, status TEXT NOT NULL DEFAULT 'pending', player_id TEXT, description TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '');
                    INSERT INTO players(id,match_id,code,number) VALUES('old-player','match','old','7');
                """)
                connection.close()
                main.init_db()
                with main.db() as migrated:
                    player_columns = {row["name"] for row in migrated.execute("PRAGMA table_info(players)")}
                    event_columns = {row["name"] for row in migrated.execute("PRAGMA table_info(analysis_events)")}
                self.assertTrue({"number_confidence", "number_source", "number_candidates_json", "cover_path", "cover_score", "cover_source_clip_id", "cover_source_seconds"} <= player_columns)
                self.assertTrue({"confirmed_by", "confirmation_rule"} <= event_columns)
                with main.db() as migrated:
                    player = migrated.execute("SELECT number_source,number_confidence FROM players WHERE id='old-player'").fetchone()
                self.assertEqual((player["number_source"], player["number_confidence"]), ("manual", 1))
            finally:
                main.DB_PATH = old_path


class CoverTest(unittest.TestCase):
    def test_sharp_synthetic_frame_scores_higher_than_blurred_frame(self) -> None:
        cv2 = __import__("cv2")
        import numpy as np

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            sharp = np.zeros((240, 160, 3), dtype=np.uint8)
            cv2.rectangle(sharp, (35, 30), (125, 210), (255, 255, 255), 2)
            cv2.line(sharp, (35, 100), (125, 100), (255, 255, 255), 2)
            sharp_path = Path(directory) / "sharp.jpg"
            blurred_path = Path(directory) / "blurred.jpg"
            cv2.imwrite(str(sharp_path), sharp)
            cv2.imwrite(str(blurred_path), cv2.GaussianBlur(sharp, (21, 21), 0))
            detection = {"x1": 35, "y1": 30, "x2": 125, "y2": 210}
            self.assertGreater(BasketballAnalyzer.cover_score(sharp_path, detection), BasketballAnalyzer.cover_score(blurred_path, detection))

    def test_player_payload_exposes_cover_url_only_when_path_exists(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            old_path = main.DB_PATH
            main.DB_PATH = Path(directory) / "cover.sqlite3"
            try:
                main.init_db()
                with main.db() as connection:
                    connection.execute("INSERT INTO matches VALUES(?,?,?,?,?,?,?)", ("match", "Match", None, None, "active", 0, main.now()))
                    connection.execute("INSERT INTO players(id,match_id,code,cover_path) VALUES(?,?,?,?)", ("p1", "match", "p1", "covers/match/p1.jpg"))
                    connection.execute("INSERT INTO players(id,match_id,code) VALUES(?,?,?)", ("p2", "match", "p2"))
                    rows = connection.execute("SELECT * FROM players WHERE match_id=? ORDER BY id", ("match",)).fetchall()
                    payloads = [main.player_payload(connection, row) for row in rows]
                self.assertEqual(payloads[0]["coverUrl"], "/media-covers/match/p1.jpg")
                self.assertIsNone(payloads[1]["coverUrl"])
            finally:
                main.DB_PATH = old_path


class ReviewSampleTest(unittest.TestCase):
    def test_make_confirmation_creates_one_sample_without_player(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            old_db, old_data = main.DB_PATH, main.DATA_DIR
            main.DB_PATH = Path(directory) / "test.sqlite3"
            main.DATA_DIR = Path(directory)
            main.CATEGORY_DATA_DIR = Path(directory) / "training" / "review"
            main.CATEGORY_DATA_DIR.mkdir(parents=True)
            main.init_db()
            try:
                with main.db() as connection:
                    connection.execute("INSERT INTO matches VALUES(?,?,?,?,?,?,?)", ("m", "Match", None, None, "draft", 0, main.now()))
                    connection.execute("INSERT INTO teams(id,match_id,side,name) VALUES(?,?,?,?)", ("m-home", "m", "home", "Home"))
                    connection.execute("INSERT INTO teams(id,match_id,side,name) VALUES(?,?,?,?)", ("m-away", "m", "away", "Away"))
                    connection.execute("INSERT INTO clips(id,match_id,filename,stored_path,sha256,size_bytes,duration,created_at) VALUES(?,?,?,?,?,?,?,?)", ("c", "m", "missing.mp4", str(Path(directory) / "missing.mp4"), "hash", 1, 10, main.now()))
                    connection.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,status,confidence,shot_type,points) VALUES(?,?,?,?,?,?,?,?)", ("e", "c", "make", 2, "pending", .9, "twoPoint", 2))
                client = TestClient(main.app)
                response = client.patch("/api/events/e", json={"status": "confirmed", "shotType": "twoPoint", "teamId": "m-home"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["reviewSample"]["created"], True)
                self.assertEqual(len(client.get("/api/matches/m/review-samples").json()), 1)
                client.close()
            finally:
                main.DB_PATH, main.DATA_DIR = old_db, old_data


class ReanalysisTest(unittest.TestCase):
    def test_ai_confirmation_can_downgrade_but_manual_confirmation_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            old_path, old_analyzer = main.DB_PATH, main.ANALYZER
            main.DB_PATH = Path(directory) / "analysis.sqlite3"
            main.init_db()
            match_id, clip_id, player_id = "match", "clip", "player"
            with main.db() as connection:
                connection.execute("INSERT INTO matches VALUES(?,?,?,?,?,?,?)", (match_id, "Match", None, None, "active", 0, main.now()))
                connection.execute("INSERT INTO teams(id,match_id,side,name) VALUES(?,?,?,?)", ("home", match_id, "home", "Home"))
                connection.execute("INSERT INTO clips(id,match_id,filename,stored_path,sha256,size_bytes,duration,status,confidence,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (clip_id, match_id, "x.mp4", "x.mp4", "hash", 1, 20, "processing", 0, main.now()))
                connection.execute("INSERT INTO players(id,match_id,team_id,code,number,number_source) VALUES(?,?,?,?,?,?)", (player_id, match_id, "home", "home-23", "23", "ai"))

            class FakeAnalyzer:
                confidence = .89

                def inspect(self, path, device):
                    track = TrackCandidate("local-001", .9, 8, number="23", number_confidence=.84, number_candidates=[{"number": "23", "votes": 8, "confidence": .84}])
                    event = AnalysisResult("make", 8, self.confidence, "crossing", "ball-hoop-crossing", "local-001", "threePoint", .63, "fiba-geometry")
                    return InspectionResult(events=[event], tracks=[track])

            fake = FakeAnalyzer()
            main.ANALYZER = fake
            try:
                for run_id in ("run-1", "run-2", "run-3"):
                    with main.db() as connection:
                        connection.execute("INSERT INTO analysis_runs(id,match_id,status,device,created_at) VALUES(?,?,?,?,?)", (run_id, match_id, "running", "cpu", main.now()))
                    asyncio.run(main.run_analysis(run_id, match_id, [clip_id], "cpu"))
                    with main.db() as connection:
                        event = connection.execute("SELECT * FROM analysis_events WHERE clip_id=?", (clip_id,)).fetchone()
                    if run_id == "run-1":
                        self.assertEqual((event["status"], event["confirmed_by"], event["points"]), ("pending", None, None))
                        with main.db() as connection:
                            payload = main.event_payload(event, connection)
                        self.assertEqual((payload["confirmedBy"], payload["confirmationRule"]), (None, None))
                        self.assertEqual((payload["numberConfidence"], payload["numberSource"]), (.84, "ai"))
                        player = connection.execute("SELECT number_candidates_json FROM players WHERE id=?", (player_id,)).fetchone()
                        self.assertEqual(json.loads(player["number_candidates_json"])[0]["number"], "23")
                        fake.confidence = .8
                    elif run_id == "run-2":
                        self.assertEqual((event["status"], event["confirmed_by"], event["points"]), ("pending", None, None))
                        with main.db() as connection:
                            self.assertEqual(connection.execute("SELECT COUNT(*) FROM event_revisions WHERE event_id=?", (event["id"],)).fetchone()[0], 1)
                            connection.execute("UPDATE analysis_events SET status='confirmed',confirmed_by='manual',confidence=.95 WHERE id=?", (event["id"],))
                    else:
                        self.assertEqual((event["status"], event["confirmed_by"], event["confidence"]), ("confirmed", "manual", .95))
            finally:
                main.ANALYZER = old_analyzer
                main.DB_PATH = old_path


if __name__ == "__main__":
    unittest.main()
