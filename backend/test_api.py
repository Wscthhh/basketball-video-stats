import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.main as main
from backend.analyzer import InspectionResult, TrackCandidate


class ApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.old_upload_dir = main.UPLOAD_DIR
        self.old_data_dir = main.DATA_DIR
        self.old_covers_dir = main.COVERS_DIR
        self.old_category_data_dir = main.CATEGORY_DATA_DIR
        self.old_clip_team_data_dir = main.CLIP_TEAM_DATA_DIR
        self.old_training_archive_dir = main.TRAINING_ARCHIVE_DIR
        self.old_mobile_token = main.MOBILE_TOKEN
        main.DB_PATH = Path(self.temp.name) / "test.sqlite3"
        main.DATA_DIR = Path(self.temp.name) / "data"
        main.UPLOAD_DIR = main.DATA_DIR / "uploads"
        main.COVERS_DIR = main.DATA_DIR / "covers"
        main.CATEGORY_DATA_DIR = main.DATA_DIR / "training" / "review"
        main.CLIP_TEAM_DATA_DIR = main.DATA_DIR / "training" / "clip-team"
        main.EXPORT_DIR = main.DATA_DIR / "exports"
        main.TRAINING_ARCHIVE_DIR = main.DATA_DIR / "training" / "archive"
        main.UPLOAD_DIR.mkdir(parents=True)
        main.COVERS_DIR.mkdir(parents=True)
        main.CATEGORY_DATA_DIR.mkdir(parents=True)
        main.CLIP_TEAM_DATA_DIR.mkdir(parents=True)
        main.EXPORT_DIR.mkdir(parents=True)
        main.TRAINING_ARCHIVE_DIR.mkdir(parents=True)
        main.init_db()
        with main.db() as connection:
            connection.execute("INSERT INTO matches VALUES(?,?,?,?,?,?,?)", ("integration-test", "integration-test", None, None, "active", 1, main.now()))
            connection.execute("INSERT INTO teams(id,match_id,side,name) VALUES(?,?,?,?)", ("integration-test-home", "integration-test", "home", ""))
            connection.execute("INSERT INTO teams(id,match_id,side,name) VALUES(?,?,?,?)", ("integration-test-away", "integration-test", "away", ""))
        self.client = TestClient(main.app)

    def tearDown(self) -> None:
        self.client.close()
        main.UPLOAD_DIR = self.old_upload_dir
        main.DATA_DIR = self.old_data_dir
        main.COVERS_DIR = self.old_covers_dir
        main.CATEGORY_DATA_DIR = self.old_category_data_dir
        main.CLIP_TEAM_DATA_DIR = self.old_clip_team_data_dir
        main.TRAINING_ARCHIVE_DIR = self.old_training_archive_dir
        main.MOBILE_TOKEN = self.old_mobile_token
        self.temp.cleanup()

    def test_match_teams_workspace_and_test_filter(self) -> None:
        response = self.client.post("/api/matches", json={"name": "Test match", "homeTeam": {"name": "Red", "color": "#f00"}, "awayTeam": {"name": "Blue", "color": "#00f"}})
        self.assertEqual(response.status_code, 201)
        match = response.json(); match_id = match["id"]
        self.assertEqual(match["homeTeam"]["name"], "Red")
        self.assertEqual(match["awayTeam"]["color"], "#00f")
        self.assertIn("integration-test", {item["id"] for item in self.client.get("/api/matches").json()})
        self.assertNotIn("integration-test", {item["id"] for item in self.client.get("/api/matches?include_test=false").json()})
        workspace = self.client.get(f"/api/matches/{match_id}/workspace").json()
        self.assertEqual(workspace["match"]["homeTeam"]["name"], "Red")
        self.assertIsInstance(workspace["stats"], list)

    def test_match_name_is_generated_from_team_names(self) -> None:
        response = self.client.post("/api/matches", json={"name": "旧标题", "homeTeam": {"name": "Home"}, "awayTeam": {"name": "Away"}})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "Home VS Away")

    def test_matches_are_ordered_by_creation_time(self) -> None:
        older = self.client.post("/api/matches", json={"name": "Older", "homeTeam": {"name": "Home"}, "awayTeam": {"name": "Away"}}).json()["id"]
        newer = self.client.post("/api/matches", json={"name": "Newer", "playedAt": "2020-01-01", "homeTeam": {"name": "Home"}, "awayTeam": {"name": "Away"}}).json()["id"]
        with main.db() as c:
            c.execute("UPDATE matches SET created_at=? WHERE id=?", ("2026-01-01T00:00:00+00:00", older))
            c.execute("UPDATE matches SET created_at=? WHERE id=?", ("2026-01-02T00:00:00+00:00", newer))
        ordered = self.client.get("/api/matches?include_test=false").json()
        self.assertEqual([item["id"] for item in ordered], [newer, older])

    def test_team_training_status_requires_balanced_samples(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Training", "homeTeam": {"name": "Home"}, "awayTeam": {"name": "Away"}}).json()["id"]
        status = self.client.get(f"/api/matches/{match_id}/team-classifier/training-status")
        self.assertEqual((status.status_code, status.json()["ready"], status.json()["suggestion"]), (200, False, False))

    def test_interrupted_processing_clips_are_requeued(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Recovery", "homeTeam": {"name": "Home"}, "awayTeam": {"name": "Away"}}).json()["id"]
        with main.db() as c:
            c.execute("INSERT INTO clips(id,match_id,filename,stored_path,sha256,size_bytes,created_at,status) VALUES(?,?,?,?,?,?,?,?)", ("stale-clip", match_id, "x.mp4", "x.mp4", "stale-hash", 1, main.now(), "processing"))
        main.init_db()
        with main.db() as c:
            self.assertEqual(c.execute("SELECT status FROM clips WHERE id='stale-clip'").fetchone()["status"], "queued")

    def test_mobile_upload_page_requires_token(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Mobile", "homeTeam": {"name": "Home"}, "awayTeam": {"name": "Away"}}).json()["id"]
        main.MOBILE_TOKEN = "test-token"
        self.assertEqual(self.client.get("/mobile").status_code, 403)
        response = self.client.get("/mobile?token=test-token")
        self.assertEqual(response.status_code, 200)
        self.assertIn("COURTTRACE 手机上传", response.text)
        self.assertEqual(self.client.get(f"/api/matches/{match_id}/clips/collections?token=bad").status_code, 403)

    def test_delete_match_preserves_training_archives(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Delete me", "homeTeam": {"name": "Home"}, "awayTeam": {"name": "Away"}}).json()["id"]
        frame = main.CLIP_TEAM_DATA_DIR / match_id / "clip" / "frame-00.jpg"
        frame.parent.mkdir(parents=True)
        frame.write_bytes(b"training")
        with main.db() as c:
            c.execute("INSERT INTO clips(id,match_id,filename,stored_path,sha256,size_bytes,created_at) VALUES(?,?,?,?,?,?,?)", ("clip", match_id, "x.mp4", "x.mp4", "delete-match-hash", 1, main.now()))
            c.execute("INSERT INTO clip_review_samples(id,match_id,clip_id,team_id,label,frames_json,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", ("sample", match_id, "clip", f"{match_id}-home", "team_home", json.dumps([str(frame.relative_to(main.DATA_DIR))]), "{}", main.now(), main.now()))
        response = self.client.delete(f"/api/matches/{match_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["trainingSamplesPreserved"], 1)
        self.assertTrue(list((main.TRAINING_ARCHIVE_DIR / "team" / match_id).rglob("*.jpg")))
        with main.db() as c:
            self.assertIsNotNone(c.execute("SELECT id FROM archived_team_training_samples WHERE source_match_id=?", (match_id,)).fetchone())

    def test_stats_merge_and_explicit_clear(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Stats", "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"}}).json()["id"]
        with main.db() as c:
            c.execute("INSERT INTO clips(id,match_id,filename,stored_path,sha256,size_bytes,duration,status,confidence,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", ("clip-1", match_id, "x.mp4", "x.mp4", "hash-1", 1, 10, "review", 1, main.now()))
            c.execute("INSERT INTO players(id,match_id,code,name,status) VALUES(?,?,?,?,?)", ("p1", match_id, "tmp-1", "", "unconfirmed"))
            c.execute("INSERT INTO players(id,match_id,code,name,status) VALUES(?,?,?,?,?)", ("p2", match_id, "tmp-2", "", "unconfirmed"))
            c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,player_id,points,source,fingerprint,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("e1", "clip-1", "attempt", 2, .8, "pending", "p1", None, "test", "fp1", main.now()))
            c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,player_id,points,source,fingerprint,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("e2", "clip-1", "make", 3, .8, "confirmed", "p1", 2, "test", "fp2", main.now()))
        self.assertEqual(self.client.patch("/api/events/e1", json={"status": "confirmed", "playerId": None, "teamId": None, "type": "attempt"}).status_code, 200)
        classified = self.client.patch("/api/events/e2", json={"shotType": "threePoint", "teamId": f"{match_id}-home"})
        self.assertEqual(classified.status_code, 200)
        self.assertEqual(classified.json()["points"], 3)
        stats = self.client.get(f"/api/matches/{match_id}/stats").json()
        self.assertEqual(stats[0]["playerId"], "p1")
        self.assertEqual(stats[0]["attempts"], 0)
        self.assertEqual(stats[0]["makes"], 1)
        self.assertEqual(stats[0]["points"], 3)
        self.assertEqual(stats[0]["threePointMakes"], 1)
        self.assertEqual(stats[1]["code"], "unassigned")
        merged = self.client.post("/api/players/merge", json={"sourcePlayerId": "p2", "targetPlayerId": "p1"})
        self.assertEqual(merged.status_code, 200)

    def test_team_only_make_confirmation_scoring_and_sample(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Scoring", "homeTeam": {"name": "Home"}, "awayTeam": {"name": "Away"}}).json()["id"]
        with main.db() as c:
            c.execute("INSERT INTO clips(id,match_id,filename,stored_path,sha256,size_bytes,duration,status,confidence,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", ("scoring-clip", match_id, "x.mp4", "x.mp4", "scoring-hash", 1, 10, "review", 1, main.now()))
            c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,points,source,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", ("scoring-event", "scoring-clip", "make", 2, .91, "pending", None, "ai", main.now()))
            c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,points,source,updated_at,team_id) VALUES(?,?,?,?,?,?,?,?,?,?)", ("away-event", "scoring-clip", "make", 3, .8, "pending", None, "ai", main.now(), f"{match_id}-away"))
            c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,points,source,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", ("unassigned-event", "scoring-clip", "make", 4, .7, "pending", None, "ai", main.now()))

        response = self.client.patch(
            "/api/events/scoring-event",
            json={"status": "confirmed", "teamId": f"{match_id}-home"},
        )
        self.assertEqual(response.status_code, 200)
        event = response.json()
        self.assertEqual((event["status"], event["teamId"], event["teamSource"]), ("confirmed", f"{match_id}-home", "manual"))
        self.assertIsNone(event["playerId"])
        self.assertEqual(event["reviewSample"]["created"], True)

        grouped = self.client.get(f"/api/matches/{match_id}/scoring").json()
        self.assertEqual([item["id"] for item in grouped["home"]["events"]], ["scoring-event"])
        self.assertEqual([item["id"] for item in grouped["away"]["events"]], ["away-event"])
        self.assertEqual([item["id"] for item in grouped["unassigned"]], ["unassigned-event"])
        samples = self.client.get(f"/api/matches/{match_id}/review-samples").json()
        self.assertEqual(samples[0]["teamId"], f"{match_id}-home")
        self.assertEqual(samples[0]["label"], "make")

    def test_upload_path_and_analysis_claim_validation(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Upload", "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"}}).json()["id"]
        upload = self.client.post(
            f"/api/matches/{match_id}/clips",
            files={"files": ("clip.mp4", b"not-a-real-video", "video/mp4")},
        )
        self.assertEqual(upload.status_code, 200)
        clip = upload.json()["accepted"][0]
        with main.db() as connection:
            row = connection.execute("SELECT stored_path FROM clips WHERE id=?", (clip["id"],)).fetchone()
            self.assertEqual(Path(row["stored_path"]).parent.name, clip["id"])
            connection.execute(
                "INSERT INTO analysis_runs(id,match_id,status,device,created_at,total_clips,completed_clips,details_json) VALUES(?,?,?,?,?,?,?,?)",
                ("active-run", match_id, "running", "cpu", main.now(), 1, 0, "{}"),
            )
        conflict = self.client.post(f"/api/matches/{match_id}/analyze", json={"clipIds": [clip["id"]], "device": "cpu"})
        self.assertEqual(conflict.status_code, 409)
        with main.db() as connection:
            connection.execute("UPDATE analysis_runs SET status='completed' WHERE id='active-run'")
        invalid = self.client.post(f"/api/matches/{match_id}/analyze", json={"clipIds": ["missing"], "device": "cpu"})
        self.assertEqual(invalid.status_code, 422)

    def test_delete_clip_removes_relations_and_files_without_affecting_other_clip(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Delete", "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"}}).json()["id"]
        deleted_dir = main.UPLOAD_DIR / match_id / "delete-clip"
        kept_dir = main.UPLOAD_DIR / match_id / "keep-clip"
        deleted_dir.mkdir(parents=True)
        kept_dir.mkdir(parents=True)
        deleted_video = deleted_dir / "delete.mp4"
        kept_video = kept_dir / "keep.mp4"
        deleted_video.write_bytes(b"delete")
        kept_video.write_bytes(b"keep")
        deleted_cover = main.COVERS_DIR / match_id / "deleted-player.jpg"
        kept_cover = main.COVERS_DIR / match_id / "shared-player.jpg"
        deleted_cover.parent.mkdir(parents=True)
        deleted_cover.write_bytes(b"delete cover")
        kept_cover.write_bytes(b"keep cover")
        analysis_dir = main.DATA_DIR / "analysis" / "run-1" / "delete-clip"
        analysis_dir.mkdir(parents=True)
        (analysis_dir / "result.json").write_text("{}", encoding="utf-8")
        sample_dir = main.CATEGORY_DATA_DIR / match_id / "delete-sample"
        sample_dir.mkdir(parents=True)
        (sample_dir / "frame.jpg").write_bytes(b"frame")

        with main.db() as c:
            for clip_id, path, digest in (("delete-clip", deleted_video, "delete-hash"), ("keep-clip", kept_video, "keep-hash")):
                c.execute("INSERT INTO clips(id,match_id,filename,stored_path,sha256,size_bytes,duration,status,confidence,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (clip_id, match_id, path.name, str(path), digest, path.stat().st_size, 10, "review", 1, main.now()))
            c.execute("INSERT INTO players(id,match_id,code,identity_type,status,cover_path,cover_source_clip_id) VALUES(?,?,?,?,?,?,?)", ("deleted-player", match_id, "tmp-delete", "temporary", "unconfirmed", str(deleted_cover), "delete-clip"))
            c.execute("INSERT INTO players(id,match_id,code,identity_type,status,cover_path,cover_source_clip_id) VALUES(?,?,?,?,?,?,?)", ("shared-player", match_id, "tmp-shared", "temporary", "unconfirmed", str(kept_cover), "keep-clip"))
            c.execute("INSERT INTO player_tracks(id,clip_id,player_id,local_track_key) VALUES(?,?,?,?)", ("delete-track", "delete-clip", "deleted-player", "delete-local"))
            c.execute("INSERT INTO player_tracks(id,clip_id,player_id,local_track_key) VALUES(?,?,?,?)", ("shared-delete-track", "delete-clip", "shared-player", "shared-delete-local"))
            c.execute("INSERT INTO player_tracks(id,clip_id,player_id,local_track_key) VALUES(?,?,?,?)", ("keep-track", "keep-clip", "shared-player", "keep-local"))
            c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,player_id,source) VALUES(?,?,?,?,?,?,?,?)", ("delete-event", "delete-clip", "make", 1, .9, "confirmed", "deleted-player", "test"))
            c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,player_id,source) VALUES(?,?,?,?,?,?,?,?)", ("keep-event", "keep-clip", "attempt", 2, .8, "pending", "shared-player", "test"))
            c.execute("INSERT INTO event_revisions VALUES(?,?,?,?,?)", ("delete-revision", "delete-event", "confirmed", "{}", main.now()))
            c.execute("INSERT INTO review_samples(id,match_id,clip_id,event_id,label,seconds,created_at) VALUES(?,?,?,?,?,?,?)", ("delete-sample", match_id, "delete-clip", "delete-event", "make", 1, main.now()))
            c.execute("INSERT INTO analysis_runs(id,match_id,status,device,created_at,details_json) VALUES(?,?,?,?,?,?)", ("run-1", match_id, "completed", "cpu", main.now(), '{"clipIds":["delete-clip"]}'))

        response = self.client.delete("/api/clips/delete-clip")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": "delete-clip", "deleted": True})
        self.assertEqual(self.client.patch("/api/clips/delete-clip", json={}).status_code, 404)
        self.assertEqual(self.client.delete("/api/clips/delete-clip").status_code, 404)
        with main.db() as c:
            for table, row_id in (("clips", "delete-clip"), ("analysis_events", "delete-event"), ("event_revisions", "delete-revision"), ("player_tracks", "delete-track"), ("review_samples", "delete-sample"), ("players", "deleted-player")):
                self.assertIsNone(c.execute(f"SELECT 1 FROM {table} WHERE id=?", (row_id,)).fetchone())
            self.assertIsNotNone(c.execute("SELECT 1 FROM clips WHERE id='keep-clip'").fetchone())
            self.assertIsNotNone(c.execute("SELECT 1 FROM analysis_events WHERE id='keep-event'").fetchone())
            self.assertIsNotNone(c.execute("SELECT 1 FROM player_tracks WHERE id='keep-track'").fetchone())
            self.assertIsNotNone(c.execute("SELECT 1 FROM players WHERE id='shared-player'").fetchone())
            self.assertIsNotNone(c.execute("SELECT 1 FROM analysis_runs WHERE id='run-1'").fetchone())
        self.assertFalse(deleted_dir.exists())
        self.assertFalse(analysis_dir.exists())
        self.assertFalse(sample_dir.exists())
        self.assertFalse(deleted_cover.exists())
        self.assertTrue(kept_dir.exists())
        self.assertTrue(kept_cover.exists())

    def test_cleanup_preserves_fixture_and_revised_confirmation(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Cleanup", "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"}}).json()["id"]
        with main.db() as c:
            c.execute("INSERT INTO clips(id,match_id,filename,stored_path,sha256,size_bytes,duration,status,confidence,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", ("cleanup-clip", match_id, "x.mp4", "x.mp4", "cleanup-hash", 1, 10, "review", 1, main.now()))
            c.execute("INSERT INTO players(id,match_id,code,identity_type,status) VALUES(?,?,?,?,?)", ("temporary-player", match_id, "tmp", "temporary", "unconfirmed"))
            c.execute("INSERT INTO players(id,match_id,code,identity_type,status) VALUES(?,?,?,?,?)", ("manual-player", match_id, "manual", "manual", "confirmed"))
            for event_id, player_id, source, status in (("auto-event", "temporary-player", "ai", "pending"), ("fixture-event", "manual-player", "test-fixture", "confirmed")):
                c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,player_id,source) VALUES(?,?,?,?,?,?,?,?)", (event_id, "cleanup-clip", "attempt", 1, .5, status, player_id, source))
            c.execute("INSERT INTO event_revisions VALUES(?,?,?,?,?)", ("revision", "auto-event", "pending", "{}", main.now()))
            c.execute("INSERT INTO player_tracks(id,clip_id,player_id,local_track_key) VALUES(?,?,?,?)", ("track", "cleanup-clip", "temporary-player", "local-1"))
            c.execute("INSERT INTO analysis_runs(id,match_id,status,device,created_at) VALUES(?,?,?,?,?)", ("cleanup-run", match_id, "completed", "cpu", main.now()))
        result = self.client.post(f"/api/matches/{match_id}/cleanup-analysis")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["events"], 1)
        with main.db() as c:
            self.assertIsNotNone(c.execute("SELECT id FROM analysis_events WHERE id='fixture-event'").fetchone())
            self.assertIsNone(c.execute("SELECT id FROM players WHERE id='temporary-player'").fetchone())
            self.assertIsNotNone(c.execute("SELECT id FROM players WHERE id='manual-player'").fetchone())

    def test_clip_patch_and_collections_include_every_clip(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Collections", "homeTeam": {"name": "Home"}, "awayTeam": {"name": "Away"}}).json()["id"]
        with main.db() as c:
            for clip_id in ("home-clip", "away-clip", "unresolved-clip"):
                c.execute("INSERT INTO clips(id,match_id,filename,stored_path,sha256,size_bytes,duration,status,confidence,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (clip_id, match_id, "x.mp4", "x.mp4", clip_id, 1, 10, "review", 1, main.now()))
        home_id, away_id = f"{match_id}-home", f"{match_id}-away"
        self.assertEqual(self.client.patch("/api/clips/home-clip", json={"teamId": home_id}).status_code, 200)
        self.assertEqual(self.client.patch("/api/clips/away-clip", json={"teamId": away_id}).status_code, 200)
        invalid = self.client.patch("/api/clips/unresolved-clip", json={"teamId": "other-team"})
        self.assertEqual(invalid.status_code, 422)
        result = self.client.get(f"/api/matches/{match_id}/clips/collections").json()
        ids = [clip["id"] for side in ("home", "away") for clip in result[side]["clips"]] + [clip["id"] for clip in result["unresolved"]]
        self.assertEqual(set(ids), {"home-clip", "away-clip", "unresolved-clip"})
        self.assertEqual(result["home"]["clips"][0]["teamSource"], "manual")

        with main.db() as c:
            c.execute("UPDATE clips SET team_id=?,team_source='ai' WHERE id=?", (home_id, "unresolved-clip"))
        result = self.client.get(f"/api/matches/{match_id}/clips/collections").json()
        self.assertEqual({clip["id"] for clip in result["home"]["clips"]}, {"home-clip", "unresolved-clip"})
        self.assertEqual(result["unresolved"], [])

    def test_clip_team_review_sample_confirm_update_clear_and_list(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Clip review", "homeTeam": {"name": "Home"}, "awayTeam": {"name": "Away"}}).json()["id"]
        video = main.DATA_DIR / "source.mp4"
        video.write_bytes(b"not-a-video")
        with main.db() as c:
            c.execute(
                "INSERT INTO clips(id,match_id,filename,stored_path,sha256,size_bytes,duration,status,confidence,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                ("review-clip", match_id, "source.mp4", str(video), "review-hash", video.stat().st_size, 12.5, "review", 1, main.now()),
            )

        class FakeCapture:
            def __init__(self, *_args):
                self.positions = []

            def get(self, property_id):
                return 10 if property_id == 7 else 0

            def set(self, property_id, position):
                self.positions.append(position)

            def read(self):
                return True, b"fake-frame"

            def release(self):
                pass

        class FakeCV2:
            CAP_PROP_FRAME_COUNT = 7
            CAP_PROP_POS_FRAMES = 1
            IMWRITE_JPEG_QUALITY = 1

            @staticmethod
            def VideoCapture(path):
                return FakeCapture(path)

            @staticmethod
            def imwrite(path, frame, _params):
                Path(path).write_bytes(frame)
                return True

        home_id, away_id = f"{match_id}-home", f"{match_id}-away"
        with patch.dict(sys.modules, {"cv2": FakeCV2}):
            first = self.client.patch("/api/clips/review-clip", json={"teamId": home_id})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["teamSource"], "manual")
        with main.db() as c:
            sample = c.execute("SELECT * FROM clip_review_samples WHERE clip_id='review-clip'").fetchone()
            frames = json.loads(sample["frames_json"])
            self.assertEqual((sample["label"], len(frames), json.loads(sample["metadata_json"])["source"]), ("team_home", 3, "manual"))
            self.assertTrue(all((main.DATA_DIR / path).exists() for path in frames))
            sample_id = sample["id"]
        self.assertEqual(self.client.patch("/api/clips/review-clip", json={"teamId": away_id}).status_code, 200)
        with main.db() as c:
            samples = c.execute("SELECT id,team_id,label FROM clip_review_samples WHERE clip_id='review-clip'").fetchall()
            self.assertEqual(len(samples), 1)
            self.assertEqual(samples[0]["id"], sample_id)
            self.assertEqual((samples[0]["team_id"], samples[0]["label"]), (away_id, "team_away"))
        listed = self.client.get(f"/api/matches/{match_id}/clip-review-samples")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()[0]["metadata"]["clipFilename"], "source.mp4")
        self.assertEqual(self.client.patch("/api/clips/review-clip", json={"teamId": None}).status_code, 200)
        with main.db() as c:
            self.assertIsNone(c.execute("SELECT 1 FROM clip_review_samples WHERE clip_id='review-clip'").fetchone())
        self.assertFalse((main.CLIP_TEAM_DATA_DIR / match_id / "review-clip").exists())

    def test_delete_clip_removes_clip_team_review_sample(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Delete clip sample", "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"}}).json()["id"]
        sample_dir = main.CLIP_TEAM_DATA_DIR / match_id / "sample-clip"
        sample_dir.mkdir(parents=True)
        (sample_dir / "frame-00.jpg").write_bytes(b"frame")
        with main.db() as c:
            c.execute(
                "INSERT INTO clips(id,match_id,filename,stored_path,sha256,size_bytes,duration,status,confidence,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                ("sample-clip", match_id, "x.mp4", "x.mp4", "sample-hash", 1, 1, "review", 1, main.now()),
            )
            c.execute(
                "INSERT INTO clip_review_samples(id,match_id,clip_id,team_id,label,frames_json,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                ("sample-row", match_id, "sample-clip", f"{match_id}-home", "team_home", "[]", "{}", main.now(), main.now()),
            )
        self.assertEqual(self.client.delete("/api/clips/sample-clip").status_code, 200)
        with main.db() as c:
            self.assertIsNone(c.execute("SELECT 1 FROM clip_review_samples WHERE id='sample-row'").fetchone())
        self.assertFalse(sample_dir.exists())

    def test_manual_clip_team_survives_analysis(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Manual team", "homeTeam": {"name": "Home", "color": "#ff0000"}, "awayTeam": {"name": "Away", "color": "#0000ff"}}).json()["id"]
        with main.db() as c:
            c.execute("INSERT INTO clips(id,match_id,filename,stored_path,sha256,size_bytes,duration,status,confidence,created_at,team_id,team_source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", ("manual-clip", match_id, "x.mp4", "x.mp4", "manual-hash", 1, 10, "processing", 0, main.now(), f"{match_id}-home", "manual"))
            c.execute("INSERT INTO analysis_runs(id,match_id,status,device,total_clips,created_at) VALUES(?,?,?,?,?,?)", ("manual-run", match_id, "running", "cpu", 1, main.now()))

        class FakeAnalyzer:
            def inspect(self, *_args, **_kwargs):
                return InspectionResult(tracks=[TrackCandidate("local-001", .9, 8, (0, 0, 255))])

        with patch.object(main, "ANALYZER", FakeAnalyzer()):
            asyncio.run(main.run_analysis("manual-run", match_id, ["manual-clip"], "cpu"))
        with main.db() as c:
            clip = c.execute("SELECT team_id,team_source FROM clips WHERE id='manual-clip'").fetchone()
            self.assertEqual((clip["team_id"], clip["team_source"]), (f"{match_id}-home", "manual"))


if __name__ == "__main__":
    unittest.main()
