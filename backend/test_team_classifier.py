import unittest

from backend.team_classifier import classify, jersey_distance


class TeamClassifierTest(unittest.TestCase):
    def test_colored_jerseys_are_separated(self) -> None:
        teams = [{"id": "home", "color": "#d73a3a"}, {"id": "away", "color": "#3267d6"}]
        self.assertEqual(classify((208, 48, 48), teams).team_id, "home")
        self.assertEqual(classify((48, 93, 202), teams).team_id, "away")

    def test_ambiguous_sample_stays_unassigned(self) -> None:
        teams = [{"id": "home", "color": "#eeeeee"}, {"id": "away", "color": "#ffffff"}]
        self.assertIsNone(classify((242, 242, 242), teams).team_id)

    def test_distance_is_finite_for_valid_colors(self) -> None:
        self.assertLess(jersey_distance((215, 58, 58), "#d73a3a"), 0.2)


if __name__ == "__main__":
    unittest.main()
