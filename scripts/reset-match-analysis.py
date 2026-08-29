"""Remove generated analysis for one match, keeping match setup and fixtures."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import main  # noqa: E402


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-id", required=True)
    args = parser.parse_args()
    print(main.cleanup_match_analysis(args.match_id))


if __name__ == "__main__":
    run()
