from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SAMPLE_FPS = 5
MAX_FRAMES = 50


@dataclass
class AnalysisResult:
    event_type: str
    seconds: float
    confidence: float
    description: str
    source: str


@dataclass
class InspectionResult:
    events: list[AnalysisResult] = field(default_factory=list)
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
                court_results = self._predict(self.models["court"], [frames[len(frames) // 2]], device, confidence=0.25) if self.models["court"].ready else []
            except Exception as error:
                return InspectionResult(error=f"inference failed: {error}")

            players, hoops = self._collect_detections(player_results, {"player"}, {"hoop"})
            balls, _ = self._collect_detections(ball_results, {"ball", "basketball", "sports ball"}, set(), best_per_frame=True)
            court_keypoints = self._count_keypoints(court_results)
            events = self._detect_shot_events(balls, hoops)
            return InspectionResult(
                events=events,
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

    def _detect_shot_events(self, balls: list[dict[str, float]], hoops: list[dict[str, float]]) -> list[AnalysisResult]:
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
        events = [
            AnalysisResult(
                "投篮",
                apex["frame"] / SAMPLE_FPS,
                min(0.92, average_confidence),
                "篮球轨迹呈现上升后下降，生成疑似投篮候选",
                "ball-trajectory",
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
                        )
                    )
                    return events
        return events

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
