#!/usr/bin/env python3
"""
道德经五讲 · 一键出片（Edge TTS 草稿）

  1. 扫描 epNN 图库，排除 EP01..EP(N-1) 已用图
  2. 自动配图 → 等你确认（或 --render 直接出片）
  3. 生成 22beats 分镜 + pipeline 渲染

用法:
  # 第一步：看图谱，确认/改 examples/ep03_image_matches.json
  python3 scripts/make_episode.py 3

  # 第二步：确认后出片
  python3 scripts/make_episode.py 3 --render

  # 跳过交互，匹配完直接渲染
  python3 scripts/make_episode.py 3 --render --yes

前置:
  - examples/storyboard-daodejing-ep03.json   （粗文案）
  - examples/ep03_beats.json
  - assets/DaoDeJing/image_catalog.json       （统一图库，自动合并 EP01/EP02 未用图）
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.episode_assets import (  # noqa: E402
    build_22beat_storyboard,
    collect_used_images,
    ensure_master_catalog,
    filter_unused_images,
    load_catalog_images,
    normalize_asset_path,
    print_match_review,
    scan_episode_catalog,
)
from scripts.match_storyboard_images import greedy_match  # noqa: E402


def _paths(episode: int) -> dict[str, Path]:
    tag = f"{episode:02d}"
    return {
        "coarse": ROOT / f"examples/storyboard-daodejing-ep{tag}.json",
        "beats": ROOT / f"examples/ep{tag}_beats.json",
        "matches": ROOT / f"examples/ep{tag}_image_matches.json",
        "storyboard": ROOT / f"examples/storyboard-daodejing-ep{tag}-22beats.json",
        "catalog": ROOT / "assets/DaoDeJing/image_catalog.json",
        "template": ROOT / "examples/storyboard-daodejing-ep02-22beats.json",
        "work_dir": ROOT / f"output/ep{tag}-draft/.work",
        "output_dir": ROOT / f"output/ep{tag}-draft",
    }


def run_match(episode: int, *, refresh_catalog: bool) -> list[dict]:
    p = _paths(episode)
    if not p["coarse"].is_file():
        raise SystemExit(f"缺少粗分镜: {p['coarse']}")
    if not p["beats"].is_file():
        raise SystemExit(f"缺少节拍表: {p['beats']}")

    if refresh_catalog:
        ep_catalog = ROOT / f"assets/DaoDeJing/ep{episode:02d}_image_catalog.json"
        if any(
            f.name.startswith(f"ep{episode:02d}_")
            for f in (ROOT / "assets/DaoDeJing").rglob("*")
            if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ):
            print(f"扫描 ep{episode:02d}_*.jpg → {ep_catalog.relative_to(ROOT)}")
            scan_episode_catalog(episode, ROOT)
        print(f"合并图库 → {p['catalog'].relative_to(ROOT)}")
        ensure_master_catalog(ROOT, refresh=True)
    else:
        ensure_master_catalog(ROOT, refresh=False)

    used = collect_used_images(ROOT, episode)
    all_images = load_catalog_images(p["catalog"], ROOT)
    pool = filter_unused_images(all_images, used, ROOT)

    beats_doc = json.loads(p["beats"].read_text(encoding="utf-8"))
    beats = beats_doc["beats"]

    if len(pool) < len(beats):
        raise SystemExit(
            f"可用新图不足：需要 {len(beats)} 张，"
            f"统一图库 {len(all_images)} 张，"
            f"排除往期已用 {len(used)} 张后剩 {len(pool)} 张。\n"
            f"请补充 assets/DaoDeJing/ 配图后执行 --refresh-catalog，"
            f"或编辑 examples/ep{episode:02d}_image_matches.json 手动指定。"
        )

    exclude_rel = {normalize_asset_path(x, ROOT) for x in used}
    matches = greedy_match(beats, pool, exclude_files=exclude_rel)

    out = {
        "meta": {
            "episode": episode,
            "catalog": str(p["catalog"].relative_to(ROOT)),
            "beats": str(p["beats"].relative_to(ROOT)),
            "beat_count": len(beats),
            "catalog_total": len(all_images),
            "pool_unused": len(pool),
            "excluded_prior_episodes": len(used),
            "assigned": sum(1 for m in matches if m.get("file")),
            "algorithm": "greedy_no_reuse_excluding_prior_eps",
        },
        "matches": matches,
    }
    p["matches"].write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 {p['matches'].relative_to(ROOT)}")
    print_match_review(matches, len(used), len(pool))
    return matches


def run_build_and_render(episode: int, *, skip_tts: bool = False) -> Path:
    p = _paths(episode)
    if not p["matches"].is_file():
        raise SystemExit("请先运行匹配（不加 --render）或确保 matches 文件存在")

    coarse = json.loads(p["coarse"].read_text(encoding="utf-8"))
    beats = json.loads(p["beats"].read_text(encoding="utf-8"))["beats"]
    matches_doc = json.loads(p["matches"].read_text(encoding="utf-8"))
    matches = matches_doc["matches"]

    missing = [m for m in matches if not m.get("file")]
    if missing:
        raise SystemExit(
            f"{len(missing)} 个节拍未配图: {[m['beat_id'] for m in missing]}。"
            f"请编辑 {p['matches'].relative_to(ROOT)} 后重试。"
        )

    template = json.loads(p["template"].read_text(encoding="utf-8"))
    # 模板只保留壳，去掉 EP02 场景
    template["scenes"] = []

    storyboard = build_22beat_storyboard(episode, coarse, beats, matches, template)
    p["storyboard"].write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已写入 {p['storyboard'].relative_to(ROOT)}")

    cmd = [
        sys.executable,
        "-m",
        "pipeline",
        str(p["storyboard"].relative_to(ROOT)),
        "--work-dir",
        str(p["work_dir"].relative_to(ROOT)),
        "--output-dir",
        str(p["output_dir"].relative_to(ROOT)),
    ]
    if skip_tts:
        cmd.append("--skip-tts")
    print("\n渲染中（Edge TTS）…")
    subprocess.run(cmd, cwd=ROOT, check=True)

    out_file = p["output_dir"] / storyboard["output"]["filename"]
    print(f"\n成片: {out_file}")
    print(f"封面: assets/covers/daodejing-ep{episode:02d}-cover.jpg")
    return out_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode", type=int, help="期数，如 3")
    parser.add_argument(
        "--render",
        action="store_true",
        help="配图确认后生成 22beats 并渲染",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="与 --render 合用：不交互，直接渲染",
    )
    parser.add_argument(
        "--refresh-catalog",
        action="store_true",
        help="重新扫描 epNN_*.jpg 并合并写入 image_catalog.json",
    )
    parser.add_argument(
        "--skip-tts",
        action="store_true",
        help="渲染时跳过 TTS（复用已有 audio）",
    )
    parser.add_argument(
        "--rematch",
        action="store_true",
        help="强制重新自动配图（默认 --render 时保留已有 matches）",
    )
    parser.add_argument(
        "--match-only",
        action="store_true",
        help="只配图，不提示渲染",
    )
    args = parser.parse_args()

    if args.episode < 1:
        raise SystemExit("episode 须 ≥ 1")

    p = _paths(args.episode)
    if args.rematch or args.refresh_catalog or not p["matches"].is_file():
        matches = run_match(args.episode, refresh_catalog=args.refresh_catalog)
    else:
        matches_doc = json.loads(p["matches"].read_text(encoding="utf-8"))
        matches = matches_doc["matches"]
        print(f"沿用已有 {p['matches'].relative_to(ROOT)}（{sum(1 for m in matches if m.get('file'))}/22 已配图）")

    if args.match_only:
        return 0

    if not args.render:
        print("\n下一步: 确认 examples/ep{:02d}_image_matches.json 后执行".format(args.episode))
        print(f"  python3 scripts/make_episode.py {args.episode} --render")
        return 0

    if not args.yes:
        missing = [m for m in matches if not m.get("file")]
        if missing:
            return 1
        try:
            ans = input("\n配图 OK？输入 y 开始渲染: ").strip().lower()
        except EOFError:
            ans = "y"
        if ans not in ("y", "yes", ""):
            print("已取消。改完 matches 后再 --render。")
            return 0

    run_build_and_render(args.episode, skip_tts=args.skip_tts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
