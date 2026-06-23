#!/usr/bin/env python3
"""给庄子系列分镜追加互动引导语，privacy_status 设为 private（定时由 publish_at 控制）。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CTA_YOUTUBE = "\n\n💬 看完这期，你最有共鸣的是哪一句？欢迎在评论区留言，和我说说你的感受。如果这期对你有帮助，别忘了点赞订阅，让更多人看见庄子。"

CTA_BILIBILI = "\n\n💬 看完这期，最触动你的是哪一句？欢迎在评论区留言，也欢迎发弹幕——我每条都会认真看的。觉得有收获的话，点赞投币收藏三连支持一下，让更多人有机会读到庄子。"

episodes = [
    ("examples/storyboard-zhuangzi-qiwulun.json",    "2026-07-01T08:00:00+08:00"),
    ("examples/storyboard-zhuangzi-yangshengzhu.json","2026-07-03T08:00:00+08:00"),
    ("examples/storyboard-zhuangzi-renjianshi.json",  "2026-07-05T08:00:00+08:00"),
    ("examples/storyboard-zhuangzi-dechongfu.json",   "2026-07-07T08:00:00+08:00"),
    ("examples/storyboard-zhuangzi-dazongshi.json",   "2026-07-09T08:00:00+08:00"),
    ("examples/storyboard-zhuangzi-yingdiwang.json",  "2026-07-11T08:00:00+08:00"),
]

for fn, publish_at in episodes:
    path = ROOT / fn
    sb = json.loads(path.read_text(encoding="utf-8"))

    if "youtube" in sb:
        sb["youtube"]["privacy_status"] = "private"
        intro = sb["youtube"].get("description_intro", "")
        if "💬" not in intro:
            sb["youtube"]["description_intro"] = intro + CTA_YOUTUBE

    if "bilibili" in sb:
        intro_b = sb["bilibili"].get("description_intro", "")
        if "💬" not in intro_b:
            sb["bilibili"]["description_intro"] = intro_b + CTA_BILIBILI
        dynamic = sb["bilibili"].get("dynamic", "")
        if "评论" not in dynamic:
            sb["bilibili"]["dynamic"] = dynamic + " 你最有共鸣的是哪句？评论区见。"

    path.write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ {fn.split('/')[-1]}  →  {publish_at}")

print("\n分镜全部更新完毕。")
