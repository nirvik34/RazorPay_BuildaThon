from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from simulator import (
    compromised,
    intent_mismatch,
    new_merchant,
    normal,
    over_limit,
    splitting,
)  # noqa: E402

MODES = [
    "normal",
    "over_limit",
    "splitting",
    "intent_mismatch",
    "new_merchant",
    "compromised",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AgentPay Guard — deterministic shopping-agent simulator"
    )
    parser.add_argument(
        "--api", default="http://localhost:8000", help="Guard backend base URL"
    )
    parser.add_argument(
        "--mode", default="all", choices=MODES + ["all"], help="demo scenario to run"
    )
    args = parser.parse_args()

    started = time.perf_counter()
    scenes = MODES if args.mode == "all" else [args.mode]
    for scene in scenes:
        module = {
            "normal": normal,
            "over_limit": over_limit,
            "splitting": splitting,
            "intent_mismatch": intent_mismatch,
            "new_merchant": new_merchant,
            "compromised": compromised,
        }[scene]
        try:
            module.run(args.api)
        except (AssertionError, RuntimeError) as exc:
            print(f"\n[!] {scene} failed: {exc}")
            if scene == normal_scene_first(scene, scenes):
                raise SystemExit(1) from exc
            continue
        time.sleep(0.4)

    print(
        f"\nDemo complete in {time.perf_counter() - started:.1f}s — every decision recorded in local audit."
    )


def normal_scene_first(scene: str, scenes: list[str]) -> bool:
    return scene == scenes[0]


if __name__ == "__main__":
    main()
