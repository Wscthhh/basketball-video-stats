from __future__ import annotations

import colorsys
import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TeamMatch:
    team_id: str | None
    confidence: float
    distance: float
    source: str


def parse_hex(value: str | None) -> tuple[float, float, float] | None:
    if not value or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return None
    return tuple(int(value[index:index + 2], 16) / 255 for index in (1, 3, 5))


def signature(rgb: tuple[float, float, float] | None) -> tuple[float, float, float] | None:
    if rgb is None:
        return None
    red, green, blue = (max(0.0, min(255.0, value)) / 255 for value in rgb)
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    return hue, saturation, value


def jersey_distance(sample: tuple[float, float, float] | None, target_hex: str | None) -> float:
    left, right = signature(sample), signature(tuple(value * 255 for value in parse_hex(target_hex))) if parse_hex(target_hex) else None
    if left is None or right is None:
        return math.inf
    hue_gap = min(abs(left[0] - right[0]), 1 - abs(left[0] - right[0]))
    saturation_gap = abs(left[1] - right[1])
    value_gap = abs(left[2] - right[2])
    # Hue is useful for colored jerseys; brightness is more informative for white/black kits.
    hue_weight = min(left[1], right[1])
    return hue_gap * (0.7 + 1.3 * hue_weight) + saturation_gap * 0.35 + value_gap * 0.8


def classify(sample: tuple[float, float, float] | None, teams: list[dict[str, str | None]], prototypes: dict[str, tuple[float, float, float]] | None = None) -> TeamMatch:
    candidates = sorted(
        (jersey_distance(sample, "#%02x%02x%02x" % tuple(round(max(0, min(255, value))) for value in prototypes[team["id"]])) if prototypes and team.get("id") in prototypes else jersey_distance(sample, team.get("color")), team.get("id"))
        for team in teams
        if team.get("id") and team.get("color")
    )
    if not candidates or math.isinf(candidates[0][0]):
        return TeamMatch(None, 0, math.inf, "unassigned")
    best_distance, best_id = candidates[0]
    second_distance = candidates[1][0] if len(candidates) > 1 else math.inf
    margin = second_distance - best_distance
    confidence = max(0.0, min(1.0, 1 - best_distance * 1.6)) * max(0.0, min(1.0, margin * 3.2))
    if confidence < 0.18:
        return TeamMatch(None, confidence, best_distance, "ambiguous-color")
    return TeamMatch(str(best_id), confidence, best_distance, "jersey-hsv")
