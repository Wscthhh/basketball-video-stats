import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import backend.main as main


class ApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.old_upload_dir = main.UPLOAD_DIR
        main.DB_PATH = Path(self.temp.name) / "test.sqlite3"
        main.UPLOAD_DIR = Path(self.temp.name) / "uploads"
        main.UPLOAD_DIR.mkdir(parents=True)
        main.init_db()
        with main.db() as connection:
            connection.execute("INSERT INTO matches VALUES(?,?,?,?,?,?,?)", ("integration-test", "integration-test", None, None, "active", 1, main.now()))
            connection.execute("INSERT INTO teams(id,match_id,side,name) VALUES(?,?,?,?)", ("integration-test-home", "integration-test", "home", ""))
            connection.execute("INSERT INTO teams(id,match_id,side,name) VALUES(?,?,?,?)", ("integration-test-away", "integration-test", "away", ""))
        self.client = TestClient(main.app)

    def tearDown(self) -> None:
        self.client.close()
        main.UPLOAD_DIR = self.old_upload_dir
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

    def test_stats_merge_and_explicit_clear(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Stats", "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"}}).json()["id"]
        with main.db() as c:
            c.execute("INSERT INTO clips VALUES(?,?,?,?,?,?,?,?,?,?)", ("clip-1", match_id, "x.mp4", "x.mp4", "hash-1", 1, 10, "review", 1, main.now()))
            c.execute("INSERT INTO players(id,match_id,code,name,status) VALUES(?,?,?,?,?)", ("p1", match_id, "tmp-1", "", "unconfirmed"))
            c.execute("INSERT INTO players(id,match_id,code,name,status) VALUES(?,?,?,?,?)", ("p2", match_id, "tmp-2", "", "unconfirmed"))
            c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,player_id,points,source,fingerprint,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("e1", "clip-1", "attempt", 2, .8, "pending", "p1", None, "test", "fp1", main.now()))
            c.execute("INSERT INTO analysis_events(id,clip_id,event_type,seconds,confidence,status,player_id,points,source,fingerprint,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("e2", "clip-1", "make", 3, .8, "confirmed", "p1", 2, "test", "fp2", main.now()))
        self.assertEqual(self.client.patch("/api/events/e1", json={"status": "confirmed", "playerId": None, "teamId": None, "type": "attempt"}).status_code, 200)
        classified = self.client.patch("/api/events/e2", json={"shotType": "threePoint"})
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

    def test_cleanup_preserves_fixture_and_revised_confirmation(self) -> None:
        match_id = self.client.post("/api/matches", json={"name": "Cleanup", "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"}}).json()["id"]
        with main.db() as c:
            c.execute("INSERT INTO clips VALUES(?,?,?,?,?,?,?,?,?,?)", ("cleanup-clip", match_id, "x.mp4", "x.mp4", "cleanup-hash", 1, 10, "review", 1, main.now()))
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


if __name__ == "__main__":
    unittest.main()
