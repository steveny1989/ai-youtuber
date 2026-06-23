#!/usr/bin/env python3
"""试跑 TTS：从分镜取一段旁白生成 mp3（edge / volcengine / gemini）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.env_util import load_dotenv  # noqa: E402
from pipeline.models import Storyboard, TtsConfig  # noqa: E402
from pipeline.subtitle_timing import build_cues_for_audio  # noqa: E402
from pipeline.tts import generate_scene_audio  # noqa: E402


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "storyboard",
        nargs="?",
        type=Path,
        default=ROOT / "examples/storyboard-daodejing-ep01-22beats.json",
    )
    parser.add_argument("--scene-id", default="intro-1")
    parser.add_argument(
        "--provider",
        default="volcengine",
        choices=("edge", "volcengine", "gemini", "google_cloud"),
    )
    parser.add_argument("--voice", default="zh_male_ruyaqingnian_uranus_bigtts")
    parser.add_argument("--resource-id", default="seed-tts-2.0")
    parser.add_argument("--emotion", default="narrator")
    parser.add_argument("--model", default="gemini-2.5-flash-preview-tts")
    parser.add_argument("--rate", default="-5%")
    args = parser.parse_args()

    sb = Storyboard.load(args.storyboard.resolve())
    scene = next((s for s in sb.all_scenes() if s.id == args.scene_id), None)
    if not scene or not scene.narration.strip():
        print(f"Scene not found or empty: {args.scene_id}", file=sys.stderr)
        return 1

    tts = TtsConfig(
        provider=args.provider,
        voice=args.voice,
        model=args.model,
        rate=args.rate,
        language_code=sb.language or "zh-CN",
        resource_id=args.resource_id,
        emotion=args.emotion,
    )
    out = ROOT / "output" / "audio" / f"{args.scene_id}.mp3"
    print(f"TTS provider={tts.provider} model={tts.model} voice={tts.voice}")
    print(f"Scene {args.scene_id} ({len(scene.narration)} chars) -> {out}")
    generate_scene_audio(scene.narration, out, tts)
    build_cues_for_audio(scene.narration, out)
    print(f"OK: {out} ({out.stat().st_size} bytes)")
    print(f"Cues: {out.with_suffix('.cues.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
