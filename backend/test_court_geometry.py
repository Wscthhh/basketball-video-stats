import unittest

import numpy as np

from backend.court_geometry import FIBA_KEYPOINTS, classify_fiba_shot, projection_from_pose_result, transform_point


class FakeTensor:
    def __init__(self, value):
        self.value = np.asarray(value)

    def __len__(self):
        return len(self.value)

    def __getitem__(self, index):
        return FakeTensor(self.value[index])

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.value


class CourtGeometryTest(unittest.TestCase):
    def test_fiba_shot_types_and_boundary(self) -> None:
        self.assertEqual(classify_fiba_shot((5.8, 7.5), .9).shot_type, "freeThrow")
        self.assertEqual(classify_fiba_shot((4.0, 7.5), .9).shot_type, "twoPoint")
        self.assertEqual(classify_fiba_shot((9.0, 7.5), .9).shot_type, "threePoint")
        self.assertEqual(classify_fiba_shot((2.0, .5), .9).shot_type, "threePoint")
        self.assertIsNone(classify_fiba_shot((1.575 + 6.75, 7.5), .9).shot_type)

    def test_pose_projection_maps_back_to_court_metres(self) -> None:
        image_points = FIBA_KEYPOINTS * 30 + np.asarray((100, 50), dtype=np.float32)
        keypoints = type("Keypoints", (), {"xy": FakeTensor([image_points]), "conf": FakeTensor([np.ones(18)])})()
        result = type("Result", (), {"keypoints": keypoints})()
        projection = projection_from_pose_result(result)
        self.assertIsNotNone(projection)
        point = transform_point(tuple(image_points[8]), projection)
        self.assertIsNotNone(point)
        self.assertAlmostEqual(point[0], FIBA_KEYPOINTS[8][0], places=2)
        self.assertAlmostEqual(point[1], FIBA_KEYPOINTS[8][1], places=2)


if __name__ == "__main__":
    unittest.main()
