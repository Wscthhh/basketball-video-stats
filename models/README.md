# Model Weights

The three pretrained weights are published by the `abdullahtarek/basketball_analysis` project:

https://github.com/abdullahtarek/basketball_analysis

| File | Task | Classes / output | SHA-256 |
| --- | --- | --- | --- |
| `player_detector.pt` | YOLO detect | Ball, Clock, Hoop, Overlay, Player, Ref, Scoreboard | `75C962CA04E92D756FA233289F19B421023EB826916D07FCAB8707291F767BAD` |
| `ball_detector_model.pt` | YOLO detect | Ball, Clock, Hoop, Overlay, Player, Ref, Scoreboard | `01E0D38CEE7735366F5BA5E5A0AE77ADC25006CFA3CD5D364789414CC76398EA` |
| `court_keypoint_detector.pt` | YOLO pose | Basketball court keypoints | `F6263105E5C2338FAFCFD5A6FEFD7D1D441E87364635E918DFDBB849F2DF1377` |

Run `scripts/download-models.ps1` after creating the Python environment to restore missing weights. Model files are tracked with Git LFS in this private repository.

These weights were trained on basketball broadcast footage. Validate and fine-tune them with phone gimbal footage before treating detections as final statistics.
