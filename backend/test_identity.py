import unittest
from types import SimpleNamespace

from backend.main import match_track_candidate
from backend.analyzer import BasketballAnalyzer


class IdentityTest(unittest.TestCase):
    def test_same_team_color_reuses_and_different_color_splits(self) -> None:
        player = {"id": "p1", "team_id": "home", "appearance_r": 220, "appearance_g": 20, "appearance_b": 20, "appearance_samples": 4}
        close = SimpleNamespace(jersey_rgb=(225, 25, 25), confidence=.8, detections=8)
        different = SimpleNamespace(jersey_rgb=(20, 20, 220), confidence=.8, detections=8)
        self.assertEqual(match_track_candidate(close, [player], "home")["id"], "p1")
        self.assertIsNone(match_track_candidate(different, [player], "home"))

    def test_missing_color_is_strict(self) -> None:
        player = {"id": "p1", "team_id": "home", "appearance_samples": 0, "appearance_r": None, "appearance_g": None, "appearance_b": None}
        track = SimpleNamespace(jersey_rgb=None, confidence=.9, detections=20)
        self.assertIsNone(match_track_candidate(track, [player], "home"))

    def test_tracks_seen_once_or_twice_are_not_stable(self) -> None:
        analyzer = BasketballAnalyzer.__new__(BasketballAnalyzer)
        detections = [
            {"frame": float(index), "x1": 10, "y1": 10, "x2": 40, "y2": 100, "x": 25, "y": 55, "confidence": .8}
            for index in (0, 1, 2)
        ]
        stable, linked = analyzer._track_players_iou(detections)
        self.assertEqual(len(stable), 1)
        self.assertEqual(len(linked), 3)


if __name__ == "__main__":
    unittest.main()
