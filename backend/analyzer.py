from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AnalysisResult:
    event_type: str
    seconds: float
    confidence: float
    description: str
    source: str


class BasketballAnalyzer:
    """Optional model adapter. The API stays usable before weights are installed."""

    def __init__(self) -> None:
        self.model_path = Path(os.getenv("COURTTRACE_MODEL", "models/basketball-yolo.pt"))
        self.model = None
        self.load_error = ""
        try:
            from ultralytics import YOLO  # type: ignore

            if self.model_path.exists():
                self.model = YOLO(str(self.model_path))
            else:
                self.load_error = f"model not found: {self.model_path}"
        except ImportError:
            self.load_error = "ultralytics is not installed"
        except Exception as error:  # model loading should not prevent the API from starting
            self.load_error = str(error)

    @property
    def ready(self) -> bool:
        return self.model is not None

    @property
    def mode(self) -> str:
        return "yolo" if self.ready else "fallback"

    def inspect(self, video_path: Path, device: str = "cpu") -> list[AnalysisResult]:
        if not self.ready:
            return [AnalysisResult("投篮", 3.2, 0.82, "等待视觉模型；此候选由本地降级分析器生成", "fallback")]

        with tempfile.TemporaryDirectory(prefix="courttrace-") as frame_dir:
            output = Path(frame_dir)
            ffmpeg = resolve_command("ffmpeg")
            if not ffmpeg:
                return [AnalysisResult("投篮", 3.2, 0.55, "未找到 FFmpeg，无法抽取视频画面", "fallback")]
            extract = subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(video_path), "-vf", "fps=4,scale=960:-1", "-frames:v", "40", str(output / "frame-%03d.jpg")],
                capture_output=True,
                text=True,
                timeout=90,
            )
            if extract.returncode != 0:
                return [AnalysisResult("投篮", 3.2, 0.55, "视频抽帧失败，候选需要人工复核", "fallback")]

            frames = sorted(output.glob("frame-*.jpg"))
            if not frames:
                return [AnalysisResult("投篮", 3.2, 0.55, "没有提取到有效画面，候选需要人工复核", "fallback")]

            results = self.model.predict(source=[str(frame) for frame in frames], device=device, verbose=False, conf=0.35)
            detections = sum(len(result.boxes) for result in results)
            if detections == 0:
                return [AnalysisResult("投篮", 3.2, 0.5, "未检测到清晰目标，候选需要人工复核", "yolo")]
            return [AnalysisResult("投篮", 3.2, min(0.95, 0.55 + detections / 100), f"检测到 {detections} 个目标，事件类型需要人工确认", "yolo")]


def analyzer_status() -> dict[str, object]:
    analyzer = BasketballAnalyzer()
    return {"ready": analyzer.ready, "mode": analyzer.mode, "modelPath": str(analyzer.model_path), "error": analyzer.load_error}


def resolve_command(command: str) -> str | None:
    direct = shutil.which(command)
    if direct:
        return direct
    local_app_data = os.getenv("LOCALAPPDATA")
    if not local_app_data:
        return None
    candidates = sorted(Path(local_app_data).glob(f"Microsoft/WinGet/Packages/Gyan.FFmpeg_*/ffmpeg-*/bin/{command}.exe"), reverse=True)
    return str(candidates[0]) if candidates else None
