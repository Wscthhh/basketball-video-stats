from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .court_geometry import ShotClassification, classify_fiba_shot, projection_from_pose_result, transform_point
from .team_classifier import TeamMatch, classify as classify_team, parse_hex

SAMPLE_FPS = 10
MAX_FRAMES = 140


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
    number: str | None = None
    number_confidence: float = 0
    number_candidates: list[dict[str, Any]] = field(default_factory=list)
    cover_frame_index: int | None = None
    cover_image_path: Path | None = None
    cover_score: float = 0


@dataclass
class InspectionResult:
    events: list[AnalysisResult] = field(default_factory=list)
    tracks: list[TrackCandidate] = field(default_factory=list)
    metrics: dict[str, object] = field(default_factory=dict)
    error: str = ""


@dataclass(frozen=True)
class ClipTeamDecision:
    team_id: str | None
    confidence: float
    evidence: str


def classify_clip_team(tracks: list[TrackCandidate], teams: list[dict[str, str | None]], prototypes: dict[str, tuple[float, float, float]] | None = None) -> ClipTeamDecision:
    """Choose a clip team from stable jersey tracks, independently of shot events."""
    if len(teams) != 2 or any(not parse_hex(team.get("color")) for team in teams):
        return ClipTeamDecision(None, 0, "无法从片段可靠判断球队")
    votes: dict[str, list[TeamMatch]] = {}
    for track in tracks:
        if track.detections < 3 or track.jersey_rgb is None:
            continue
        result = classify_team(track.jersey_rgb, teams, prototypes)
        if result.team_id is not None and result.confidence >= 0.18:
            votes.setdefault(result.team_id, []).append(result)
    ranked = sorted(votes.items(), key=lambda item: (-len(item[1]), -sum(v.confidence for v in item[1])))
    if not ranked:
        return ClipTeamDecision(None, 0, "无法从片段可靠判断球队")
    winner_id, winner_votes = ranked[0]
    winner_score = sum(item.confidence for item in winner_votes)
    loser_votes = ranked[1][1] if len(ranked) > 1 else []
    loser_score = sum(item.confidence for item in loser_votes)
    if loser_votes and (len(winner_votes) == len(loser_votes) or winner_score <= loser_score):
        return ClipTeamDecision(None, 0, "无法从片段可靠判断球队")
    confidence = winner_score / len(winner_votes)
    return ClipTeamDecision(str(winner_id), round(confidence, 4), f"{len(winner_votes)} 条稳定轨迹的球衣颜色匹配")


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
        self._ocr: Any = None
        self._ocr_attempted = False
        self._ocr_error = ""
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
            "ocr": {"ready": self._ocr is not None, "attempted": self._ocr_attempted, "error": self._ocr_error},
        }

    def inspect(self, video_path: Path, device: str = "cpu", output_dir: Path | None = None) -> InspectionResult:
        if not self.ready:
            return InspectionResult(error="player and ball models are required")

        temporary_dir = tempfile.TemporaryDirectory(prefix="courttrace-") if output_dir is None else None
        frame_dir = Path(output_dir) if output_dir is not None else Path(temporary_dir.name)
        frame_dir.mkdir(parents=True, exist_ok=True)
        try:
          with self._lock:
            frames, error = self._extract_frames(video_path, frame_dir)
            if error:
                return InspectionResult(error=error)

            try:
                player_results = self._predict(self.models["player"], frames, device, confidence=0.35)
                ball_results = self._predict(self.models["ball"], frames, device, confidence=0.2)
            except Exception as error:
                return InspectionResult(error=f"inference failed: {error}")

            players, hoops = self._collect_detections(player_results, {"player"}, {"hoop"})
            balls, _ = self._collect_detections(ball_results, {"ball", "basketball", "sports ball"}, set(), best_per_frame=True)
            tracks, tracked_players = self._track_players(players, frames, frame_dir)
            self._recognize_track_numbers(tracks, tracked_players, frames)
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
        finally:
            if temporary_dir is not None:
                temporary_dir.cleanup()

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

    def _track_players(self, detections: list[dict[str, float]], frames: list[Path], output_dir: Path | None = None) -> tuple[list[TrackCandidate], list[dict[str, float]]]:
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
                    aggregate.setdefault("detections", []).append(item)
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
                self._build_track_candidate(key, value, colors.get(key), frames, output_dir)
                for key, value in aggregates.items() if value["count"] >= 3
            ]
            valid_keys = {track.local_track_key for track in tracks}
            return tracks, [item for item in tracked_players if item["local_track_key"] in valid_keys]
        except ImportError:
            return self._track_players_iou(detections, frames, output_dir)

    def _track_players_iou(self, detections: list[dict[str, float]], frames: list[Path] | None = None, output_dir: Path | None = None) -> tuple[list[TrackCandidate], list[dict[str, float]]]:
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
        stable = []
        for track in tracks:
            if track["count"] < 3:
                continue
            candidate = TrackCandidate(track["key"], track["confidence"] / track["count"], track["count"])
            if frames:
                self._set_best_cover(candidate, [item for item in detections if item.get("local_track_key") == track["key"]], frames, output_dir)
            stable.append(candidate)
        valid_keys = {track.local_track_key for track in stable}
        return stable, [item for item in detections if item.get("local_track_key") in valid_keys]

    def _build_track_candidate(self, key: str, aggregate: dict[str, Any], color: list[float] | None, frames: list[Path], output_dir: Path | None) -> TrackCandidate:
        candidate = TrackCandidate(key, aggregate["confidence"] / aggregate["count"], int(aggregate["count"]), self._average_color(color),
                                    sum(aggregate["aspects"]) / len(aggregate["aspects"]), self._median(aggregate["heights"]))
        trajectory = [item for item in aggregate.get("detections", [])]
        self._set_best_cover(candidate, trajectory, frames, output_dir)
        return candidate

    def _set_best_cover(self, candidate: TrackCandidate, detections: list[dict[str, float]], frames: list[Path], output_dir: Path | None) -> None:
        best: tuple[float, int, Any] | None = None
        for detection in detections:
            frame_index = int(detection["frame"])
            if frame_index >= len(frames):
                continue
            crop, score = self._cover_crop_and_score(frames[frame_index], detection)
            if crop is not None and (best is None or score > best[0]):
                best = (score, frame_index, crop)
        if best is None:
            return
        candidate.cover_score, candidate.cover_frame_index = best[0], best[1]
        if output_dir is not None:
            try:
                import cv2
                path = output_dir / "covers" / f"{candidate.local_track_key}.jpg"
                path.parent.mkdir(parents=True, exist_ok=True)
                if cv2.imwrite(str(path), best[2]):
                    candidate.cover_image_path = path
            except Exception:
                pass

    def _get_ocr(self) -> Any:
        if self._ocr_attempted:
            return self._ocr
        self._ocr_attempted = True
        try:
            from paddleocr import PaddleOCR  # type: ignore

            self._ocr = PaddleOCR(
                lang="en",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        except Exception as error:
            self._ocr_error = str(error)
            self._ocr = None
        return self._ocr

    def _recognize_track_numbers(self, tracks: list[TrackCandidate], players: list[dict[str, float]], frames: list[Path]) -> None:
        ocr = self._get_ocr()
        if ocr is None:
            return
        by_track: dict[str, list[dict[str, float]]] = {}
        for player in players:
            by_track.setdefault(str(player["local_track_key"]), []).append(player)
        for track in tracks:
            trajectory = sorted(by_track.get(track.local_track_key, []), key=lambda item: item["frame"])
            representatives = self._representative_detections(trajectory, 8)
            reads: list[tuple[str, float]] = []
            for detection in representatives:
                crop = self._upper_body_crop(frames[int(detection["frame"])], detection)
                if crop is None:
                    continue
                reads.extend(self._ocr_numbers(ocr, crop)[:1])
            votes: dict[str, list[float]] = {}
            for number, confidence in reads:
                votes.setdefault(number, []).append(confidence)
            track.number_candidates = sorted(
                ({"number": number, "votes": len(scores), "confidence": round(sum(scores) / len(scores), 4)} for number, scores in votes.items()),
                key=lambda item: (-item["votes"], -item["confidence"], int(item["number"])),
            )
            if not track.number_candidates or not reads:
                continue
            winner = track.number_candidates[0]
            if winner["votes"] >= 5 and winner["votes"] / len(reads) >= 0.6 and winner["confidence"] >= 0.75:
                track.number = winner["number"]
                track.number_confidence = winner["confidence"]

    @staticmethod
    def _representative_detections(detections: list[dict[str, float]], limit: int) -> list[dict[str, float]]:
        if len(detections) <= limit:
            return detections
        return [detections[round(index * (len(detections) - 1) / (limit - 1))] for index in range(limit)]

    @staticmethod
    def _upper_body_crop(frame_path: Path, detection: dict[str, float]) -> Any:
        try:
            import cv2

            image = cv2.imread(str(frame_path))
            if image is None:
                return None
            image_height, image_width = image.shape[:2]
            x1, y1, x2, y2 = (int(detection[key]) for key in ("x1", "y1", "x2", "y2"))
            width, height = x2 - x1, y2 - y1
            if width < 8 or height < 12:
                return None
            left = max(0, x1 + int(width * 0.08))
            right = min(image_width, x2 - int(width * 0.08))
            top = max(0, y1 + int(height * 0.08))
            bottom = min(image_height, y1 + int(height * 0.62))
            crop = image[top:bottom, left:right]
            return crop if crop.size else None
        except Exception:
            return None

    @staticmethod
    def _cover_crop_and_score(frame_path: Path, detection: dict[str, float]) -> tuple[Any, float]:
        """Return a bounded upper-body crop and a comparable sharpness/size score."""
        try:
            import cv2
            image = cv2.imread(str(frame_path))
            if image is None:
                return None, 0
            height, width = image.shape[:2]
            x1, y1, x2, y2 = (float(detection[key]) for key in ("x1", "y1", "x2", "y2"))
            box_width, box_height = x2 - x1, y2 - y1
            if box_width < 16 or box_height < 32:
                return None, 0
            left = max(0, int(x1 + box_width * 0.06))
            right = min(width, int(x2 - box_width * 0.06))
            top = max(0, int(y1 + box_height * 0.04))
            bottom = min(height, int(y1 + box_height * 0.78))
            if right <= left or bottom <= top:
                return None, 0
            crop = image[top:bottom, left:right]
            if crop.size == 0 or crop.shape[0] < 24 or crop.shape[1] < 12:
                return None, 0
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            sharpness = min(1.0, float(cv2.Laplacian(gray, cv2.CV_64F).var()) / 500.0)
            area_score = min(1.0, (box_width * box_height) / (width * height * 0.12))
            height_score = min(1.0, box_height / (height * 0.55))
            edge_touch = sum((x1 <= 1, y1 <= 1, x2 >= width - 1, y2 >= height - 1))
            edge_penalty = max(0.0, 1.0 - edge_touch * 0.25)
            score = (0.55 * sharpness + 0.25 * area_score + 0.20 * height_score) * edge_penalty
            return crop, float(score)
        except Exception:
            return None, 0

    @classmethod
    def cover_score(cls, frame_path: Path, detection: dict[str, float]) -> float:
        """Score helper kept independent so synthetic-frame tests need no model."""
        return cls._cover_crop_and_score(frame_path, detection)[1]

    @classmethod
    def _ocr_numbers(cls, ocr: Any, crop: Any) -> list[tuple[str, float]]:
        try:
            if hasattr(ocr, "predict"):
                result = ocr.predict(input=crop)
            else:
                result = ocr.ocr(crop, cls=False)
        except Exception:
            return []
        values: list[tuple[str, float]] = []
        cls._collect_ocr_values(result, values)
        return sorted(values, key=lambda item: item[1], reverse=True)

    @classmethod
    def _collect_ocr_values(cls, value: Any, output: list[tuple[str, float]]) -> None:
        if hasattr(value, "json"):
            value = value.json
            if callable(value):
                value = value()
        if isinstance(value, dict):
            texts, scores = value.get("rec_texts"), value.get("rec_scores")
            if isinstance(texts, (list, tuple)) and isinstance(scores, (list, tuple)):
                for text, score in zip(texts, scores):
                    cls._append_ocr_number(text, score, output)
                return
            for nested in value.values():
                cls._collect_ocr_values(nested, output)
        elif isinstance(value, (list, tuple)):
            if len(value) == 2 and isinstance(value[0], str) and isinstance(value[1], (int, float)):
                cls._append_ocr_number(value[0], value[1], output)
                return
            for nested in value:
                cls._collect_ocr_values(nested, output)

    @staticmethod
    def _append_ocr_number(text: Any, score: Any, output: list[tuple[str, float]]) -> None:
        cleaned = re.sub(r"\D", "", str(text))
        if 1 <= len(cleaned) <= 2 and int(cleaned) <= 99:
            output.append((str(int(cleaned)), max(0.0, min(1.0, float(score)))))

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
            # Median suppresses court lights, floor reflections and isolated background pixels.
            bgr = __import__("numpy").median(pixels, axis=0)
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
