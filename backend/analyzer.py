from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .court_geometry import ShotClassification, classify_fiba_shot, projection_from_pose_result, transform_point

SAMPLE_FPS = 5
MAX_FRAMES = 50


@dataclass
class AnalysisResult:
    event_type: str
    seconds: float
    confidence: float
    description: str
    source: str
    local_track_key: str | None = None
    shot_type: str | None = None
    shot_type_confidence: float = 0
    shot_type_source: str | None = None
    court_x: float | None = None
    court_y: float | None = None
    homography_confidence: float = 0
    release_frame: int | None = None


@dataclass
class TrackCandidate:
    local_track_key: str
    confidence: float
    detections: int
    jersey_rgb: tuple[float, float, float] | None = None
    bbox_aspect: float | None = None
    median_height: float | None = None


@dataclass
class InspectionResult:
    events: list[AnalysisResult] = field(default_factory=list)
    tracks: list[TrackCandidate] = field(default_factory=list)
    metrics: dict[str, object] = field(default_factory=dict)
    error: str = ""


@dataclass
class ModelHandle:
    name: str
    path: Path
    task: str
    model: Any = None
    error: str = ""

    @property
    def ready(self) -> bool:
        return self.model is not None

    def status(self) -> dict[str, object]:
        names = getattr(self.model, "names", {}) if self.model else {}
        return {
            "ready": self.ready,
            "path": str(self.path),
            "task": getattr(self.model, "task", self.task) if self.model else self.task,
            "classes": list(names.values()) if isinstance(names, dict) else list(names),
            "error": self.error,
        }


class BasketballAnalyzer:
    """Runs independent player, ball and court models over sampled video frames."""

    def __init__(self) -> None:
        self.models = {
            "player": ModelHandle("player", Path(os.getenv("COURTTRACE_PLAYER_MODEL", "models/player_detector.pt")), "detect"),
            "ball": ModelHandle("ball", Path(os.getenv("COURTTRACE_BALL_MODEL", "models/ball_detector_model.pt")), "detect"),
            "court": ModelHandle("court", Path(os.getenv("COURTTRACE_COURT_MODEL", "models/court_keypoint_detector.pt")), "pose"),
        }
        self._lock = threading.Lock()
        self._load_models()

    def _load_models(self) -> None:
        try:
            from ultralytics import YOLO  # type: ignore
        except ImportError:
            for handle in self.models.values():
                handle.error = "ultralytics is not installed"
            return

        for handle in self.models.values():
            if not handle.path.exists():
                handle.error = f"model not found: {handle.path}"
                continue
            try:
                handle.model = YOLO(str(handle.path))
                handle.error = ""
            except Exception as error:  # a broken optional weight must not stop the API
                handle.error = str(error)

    @property
    def ready(self) -> bool:
        return self.models["player"].ready and self.models["ball"].ready

    @property
    def mode(self) -> str:
        if all(handle.ready for handle in self.models.values()):
            return "multi-model"
        if any(handle.ready for handle in self.models.values()):
            return "partial"
        return "fallback"

    def status(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "mode": self.mode,
            "models": {name: handle.status() for name, handle in self.models.items()},
        }

    def inspect(self, video_path: Path, device: str = "cpu") -> InspectionResult:
        if not self.ready:
            return InspectionResult(error="player and ball models are required")

        with self._lock, tempfile.TemporaryDirectory(prefix="courttrace-") as frame_dir:
            frames, error = self._extract_frames(video_path, Path(frame_dir))
            if error:
                return InspectionResult(error=error)

            try:
                player_results = self._predict(self.models["player"], frames, device, confidence=0.35)
                ball_results = self._predict(self.models["ball"], frames, device, confidence=0.2)
            except Exception as error:
                return InspectionResult(error=f"inference failed: {error}")

            players, hoops = self._collect_detections(player_results, {"player"}, {"hoop"})
            balls, _ = self._collect_detections(ball_results, {"ball", "basketball", "sports ball"}, set(), best_per_frame=True)
            tracks, tracked_players = self._track_players(players, frames)
            events = self._detect_shot_events(balls, hoops, tracked_players)
            court_keypoints = 0
            if events and self.models["court"].ready:
                release_frames = sorted({event.release_frame for event in events if event.release_frame is not None})
                court_frames = [frames[min(max(frame, 0), len(frames) - 1)] for frame in release_frames]
                try:
                    court_results = self._predict(self.models["court"], court_frames, device, confidence=0.25)
                    court_keypoints = self._count_keypoints(court_results)
                    self._classify_shot_types(events, release_frames, court_results, tracked_players)
                except Exception:
                    # Shot detection remains valid when court calibration is unavailable.
                    pass
            return InspectionResult(
                events=events,
                tracks=tracks,
                metrics={
                    "sampledFrames": len(frames),
                    "playerDetections": len(players),
                    "ballDetections": len(balls),
                    "hoopDetections": len(hoops),
                    "courtKeypoints": court_keypoints,
                    "eventCandidates": len(events),
                    "modelMode": self.mode,
                },
            )

    def _extract_frames(self, video_path: Path, output: Path) -> tuple[list[Path], str]:
        ffmpeg = resolve_command("ffmpeg")
        if not ffmpeg:
            return [], "FFmpeg is not available"
        process = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(video_path), "-vf", f"fps={SAMPLE_FPS},scale=960:-1", "-frames:v", str(MAX_FRAMES), str(output / "frame-%03d.jpg")],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if process.returncode != 0:
            return [], process.stderr.strip() or "video frame extraction failed"
        frames = sorted(output.glob("frame-*.jpg"))
        return (frames, "") if frames else ([], "no valid video frames were extracted")

    def _predict(self, handle: ModelHandle, frames: list[Path], device: str, confidence: float) -> list[Any]:
        if not handle.ready:
            return []
        inference_device: object = 0 if device == "cuda" else "cpu"
        try:
            return handle.model.predict(source=[str(frame) for frame in frames], device=inference_device, verbose=False, conf=confidence, imgsz=640, batch=1)
        finally:
            if device == "cuda":
                handle.model.to("cpu")
                try:
                    import torch  # type: ignore

                    torch.cuda.empty_cache()
                except ImportError:
                    pass

    def _collect_detections(
        self,
        results: list[Any],
        primary_names: set[str],
        secondary_names: set[str],
        best_per_frame: bool = False,
    ) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
        primary: list[dict[str, float]] = []
        secondary: list[dict[str, float]] = []
        for frame_index, result in enumerate(results):
            names = result.names
            frame_primary: list[dict[str, float]] = []
            for box in result.boxes:
                class_id = int(box.cls.item())
                class_name = str(names[class_id]).strip().lower()
                x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
                detection = {
                    "frame": float(frame_index),
                    "x": (x1 + x2) / 2,
                    "y": (y1 + y2) / 2,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "confidence": float(box.conf.item()),
                }
                if class_name in primary_names:
                    frame_primary.append(detection)
                elif class_name in secondary_names:
                    secondary.append(detection)
            if best_per_frame and frame_primary:
                primary.append(max(frame_primary, key=lambda item: item["confidence"]))
            else:
                primary.extend(frame_primary)
        return primary, secondary

    def _detect_shot_events(self, balls: list[dict[str, float]], hoops: list[dict[str, float]], players: list[dict[str, float]]) -> list[AnalysisResult]:
        if len(balls) < 4:
            return []
        apex_index = min(range(len(balls)), key=lambda index: balls[index]["y"])
        if apex_index == 0 or apex_index == len(balls) - 1:
            return []
        apex = balls[apex_index]
        rise = max(ball["y"] for ball in balls[:apex_index]) - apex["y"]
        fall = max(ball["y"] for ball in balls[apex_index + 1 :]) - apex["y"]
        if rise < 24 or fall < 24:
            return []

        average_confidence = sum(ball["confidence"] for ball in balls) / len(balls)
        release_ball = balls[max(0, apex_index - 2)]
        release_frame = int(release_ball["frame"])
        shooter = self._nearest_player(release_ball, players)
        if not shooter:
            return []
        events = [
            AnalysisResult(
                "投篮",
                release_frame / SAMPLE_FPS,
                min(0.92, average_confidence),
                "篮球轨迹呈现上升后下降，生成疑似投篮候选",
                "ball-trajectory",
                shooter,
                release_frame=release_frame,
            )
        ]

        above_hoop = False
        for ball in balls[apex_index:]:
            nearby = [hoop for hoop in hoops if abs(hoop["frame"] - ball["frame"]) <= 1]
            for hoop in nearby:
                hoop_width = hoop["x2"] - hoop["x1"]
                inside_x = hoop["x1"] - hoop_width * 0.35 <= ball["x"] <= hoop["x2"] + hoop_width * 0.35
                if not inside_x:
                    continue
                if ball["y"] < hoop["y1"]:
                    above_hoop = True
                elif above_hoop and ball["y"] > hoop["y2"]:
                    events.append(
                        AnalysisResult(
                            "命中",
                            ball["frame"] / SAMPLE_FPS,
                            min(0.9, (ball["confidence"] + hoop["confidence"]) / 2),
                            "篮球由篮筐上方穿过篮筐区域，生成疑似命中候选",
                            "ball-hoop-crossing",
                            shooter,
                            release_frame=release_frame,
                        )
                    )
                    return events
        return events

    def _classify_shot_types(self, events: list[AnalysisResult], release_frames: list[int], court_results: list[Any], players: list[dict[str, float]]) -> None:
        projections = {frame: projection_from_pose_result(result) for frame, result in zip(release_frames, court_results)}
        for event in events:
            if event.release_frame is None or not event.local_track_key:
                continue
            projection = projections.get(event.release_frame)
            if projection is None:
                continue
            candidates = [player for player in players if player.get("local_track_key") == event.local_track_key]
            if not candidates:
                continue
            player = min(candidates, key=lambda item: abs(item["frame"] - event.release_frame))
            foot = ((player["x1"] + player["x2"]) / 2, player["y2"])
            court_point = transform_point(foot, projection)
            if court_point is None:
                continue
            classification = classify_fiba_shot(court_point, projection.confidence)
            if classification.shot_type == "freeThrow" and not self._is_stationary_release(event.local_track_key, event.release_frame, players):
                classification = ShotClassification("twoPoint", classification.confidence * 0.75, court_point[0], court_point[1], "release point is near the free-throw line but the shooter is moving")
            event.shot_type = classification.shot_type
            event.shot_type_confidence = classification.confidence
            event.shot_type_source = "fiba-geometry" if classification.shot_type else None
            event.court_x = classification.court_x
            event.court_y = classification.court_y
            event.homography_confidence = projection.confidence
            if classification.shot_type:
                label = {"freeThrow": "罚球", "twoPoint": "两分", "threePoint": "三分"}[classification.shot_type]
                event.description = f"{event.description}；FIBA 球场定位判断为{label}"

    @staticmethod
    def _is_stationary_release(track_key: str, release_frame: int, players: list[dict[str, float]]) -> bool:
        window_start = max(0, release_frame - 3)
        shooter = sorted(
            [item for item in players if item.get("local_track_key") == track_key and window_start <= item["frame"] <= release_frame],
            key=lambda item: item["frame"],
        )
        if len(shooter) < 2:
            return False
        first, last = shooter[0], shooter[-1]
        first_frame_players = [item for item in players if item["frame"] == first["frame"]]
        last_frame_players = [item for item in players if item["frame"] == last["frame"]]
        if not first_frame_players or not last_frame_players:
            return False
        first_camera = (sum(item["x"] for item in first_frame_players) / len(first_frame_players), sum(item["y"] for item in first_frame_players) / len(first_frame_players))
        last_camera = (sum(item["x"] for item in last_frame_players) / len(last_frame_players), sum(item["y"] for item in last_frame_players) / len(last_frame_players))
        residual_x = (last["x"] - first["x"]) - (last_camera[0] - first_camera[0])
        residual_y = (last["y"] - first["y"]) - (last_camera[1] - first_camera[1])
        player_height = max(1.0, last["y2"] - last["y1"])
        return (residual_x**2 + residual_y**2) ** 0.5 / player_height < 0.12

    @staticmethod
    def _iou(left: dict[str, float], right: dict[str, float]) -> float:
        x1, y1 = max(left["x1"], right["x1"]), max(left["y1"], right["y1"])
        x2, y2 = min(left["x2"], right["x2"]), min(left["y2"], right["y2"])
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area_left = (left["x2"] - left["x1"]) * (left["y2"] - left["y1"])
        area_right = (right["x2"] - right["x1"]) * (right["y2"] - right["y1"])
        return intersection / max(area_left + area_right - intersection, 1e-6)

    def _track_players(self, detections: list[dict[str, float]], frames: list[Path]) -> tuple[list[TrackCandidate], list[dict[str, float]]]:
        try:
            import numpy as np
            import supervision as sv  # type: ignore

            tracker = sv.ByteTrack(
                track_activation_threshold=0.35,
                lost_track_buffer=12,
                minimum_matching_threshold=0.72,
                frame_rate=SAMPLE_FPS,
                minimum_consecutive_frames=3,
            )
            by_frame: dict[int, list[dict[str, float]]] = {}
            for detection in detections:
                by_frame.setdefault(int(detection["frame"]), []).append(detection)

            tracked_players: list[dict[str, float]] = []
            aggregates: dict[str, dict[str, Any]] = {}
            colors: dict[str, list[float]] = {}
            for frame_index in range(max(by_frame, default=-1) + 1):
                frame_detections = by_frame.get(frame_index, [])
                if frame_detections:
                    boxes = np.asarray([[item["x1"], item["y1"], item["x2"], item["y2"]] for item in frame_detections], dtype=np.float32)
                    confidence = np.asarray([item["confidence"] for item in frame_detections], dtype=np.float32)
                    current = sv.Detections(xyxy=boxes, confidence=confidence, class_id=np.zeros(len(frame_detections), dtype=int))
                else:
                    current = sv.Detections.empty()
                tracked = tracker.update_with_detections(current)
                if tracked.tracker_id is None:
                    continue
                for box, confidence, tracker_id in zip(tracked.xyxy, tracked.confidence, tracked.tracker_id):
                    key = f"local-{int(tracker_id):03d}"
                    x1, y1, x2, y2 = (float(value) for value in box)
                    item = {
                        "frame": float(frame_index), "x": (x1 + x2) / 2, "y": (y1 + y2) / 2,
                        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                        "confidence": float(confidence), "local_track_key": key,
                    }
                    tracked_players.append(item)
                    aggregate = aggregates.setdefault(key, {"count": 0, "confidence": 0})
                    aggregate["count"] += 1
                    aggregate["confidence"] += float(confidence)
                    aggregate.setdefault("heights", []).append(max(1.0, y2 - y1))
                    aggregate.setdefault("aspects", []).append(max(0.01, (x2 - x1) / max(1.0, y2 - y1)))
                    color = self._sample_jersey_color(frames[frame_index], item)
                    if color:
                        current_color = colors.setdefault(key, [0.0, 0.0, 0.0, 0.0])
                        current_color[0] += color[0]
                        current_color[1] += color[1]
                        current_color[2] += color[2]
                        current_color[3] += 1
            tracks = [
                TrackCandidate(key, value["confidence"] / value["count"], int(value["count"]), self._average_color(colors.get(key)),
                               sum(value["aspects"]) / len(value["aspects"]), self._median(value["heights"]))
                for key, value in aggregates.items() if value["count"] >= 3
            ]
            valid_keys = {track.local_track_key for track in tracks}
            return tracks, [item for item in tracked_players if item["local_track_key"] in valid_keys]
        except ImportError:
            return self._track_players_iou(detections)

    def _track_players_iou(self, detections: list[dict[str, float]]) -> tuple[list[TrackCandidate], list[dict[str, float]]]:
        tracks: list[dict[str, Any]] = []
        for detection in sorted(detections, key=lambda item: (item["frame"], -item["confidence"])):
            candidates = [track for track in tracks if detection["frame"] - track["frame"] <= 1 and self._iou(detection, track["last"]) >= 0.25]
            track = max(candidates, key=lambda item: self._iou(detection, item["last"]), default=None)
            if track is None:
                track = {"key": f"local-{len(tracks)+1:03d}", "last": detection, "frame": detection["frame"], "count": 0, "confidence": 0.0}
                tracks.append(track)
            track["last"], track["frame"] = detection, detection["frame"]
            track["count"] += 1; track["confidence"] += detection["confidence"]
            detection["local_track_key"] = track["key"]
        stable = [TrackCandidate(t["key"], t["confidence"] / max(t["count"], 1), t["count"]) for t in tracks if t["count"] >= 3]
        valid_keys = {track.local_track_key for track in stable}
        return stable, [item for item in detections if item.get("local_track_key") in valid_keys]

    @staticmethod
    def _sample_jersey_color(frame_path: Path, detection: dict[str, float]) -> tuple[float, float, float] | None:
        try:
            import cv2
            image = cv2.imread(str(frame_path))
            if image is None:
                return None
            x1, y1, x2, y2 = (int(detection[key]) for key in ("x1", "y1", "x2", "y2"))
            width, height = x2 - x1, y2 - y1
            if width < 8 or height < 12:
                return None
            top = image[y1 + int(height * 0.2): y1 + int(height * 0.68), x1 + int(width * 0.2): x2 - int(width * 0.2)]
            if top.size == 0:
                return None
            hsv = cv2.cvtColor(top, cv2.COLOR_BGR2HSV)
            mask = (hsv[:, :, 1] > 25) & (hsv[:, :, 2] > 35)
            pixels = top[mask]
            if len(pixels) < 10:
                pixels = top.reshape(-1, 3)
            bgr = pixels.mean(axis=0)
            return float(bgr[2]), float(bgr[1]), float(bgr[0])
        except Exception:
            return None

    @staticmethod
    def _average_color(value: list[float] | None) -> tuple[float, float, float] | None:
        if not value or value[3] == 0:
            return None
        return tuple(channel / value[3] for channel in value[:3])

    @staticmethod
    def _median(values: list[float]) -> float | None:
        return sorted(values)[len(values) // 2] if values else None

    @staticmethod
    def _nearest_player(ball: dict[str, float], players: list[dict[str, float]]) -> str | None:
        nearby = [p for p in players if abs(p["frame"] - ball["frame"]) <= 1]
        if not nearby: return None
        player = min(nearby, key=lambda p: ((p["x"] - ball["x"]) ** 2 + (p["y"] - ball["y"]) ** 2) ** 0.5)
        return player.get("local_track_key")

    @staticmethod
    def _count_keypoints(results: list[Any]) -> int:
        count = 0
        for result in results:
            if result.keypoints is not None and result.keypoints.xy is not None:
                count += int(result.keypoints.xy.numel() / 2)
        return count


def resolve_command(command: str) -> str | None:
    direct = shutil.which(command)
    if direct:
        return direct
    local_app_data = os.getenv("LOCALAPPDATA")
    if not local_app_data:
        return None
    candidates = sorted(Path(local_app_data).glob(f"Microsoft/WinGet/Packages/Gyan.FFmpeg_*/ffmpeg-*/bin/{command}.exe"), reverse=True)
    return str(candidates[0]) if candidates else None
