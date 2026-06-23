#!/usr/bin/env python3
"""生成 ch61–65 hybrid 讲解分镜（Edge TTS，long_form ≥1200 字，含氛围层）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ch61_65_images import CHAPTER_SCENE_IMAGES  # noqa: E402
from ch61_65_narrations import NARRATIONS, SCENE_ORDER  # noqa: E402
from hybrid_storyboard_util import EXAMPLES, reset_batch_image_tracking, write_chapters  # noqa: E402

GROWTH_DYNAMIC_SUFFIX = "观念黑盒起号中，欢迎点个关注，八十一讲我们会讲完。"

CHAPTER_META = {
    61: {
        "title_short": "大国者下流",
        "yt_tag": "大国者下流",
        "bili_dynamic": "大国者下流，天下之交——牝常以静胜牡，大者宜为下。",
        "desc_intro": "观念黑盒：《道德经》第六十一章精解——下流、牝静与大国宜下。",
        "sections": {
            "plain": "下流之交；牝静胜牡；以下取；各得所欲；大者宜下。",
            "east_west": "修昔底德陷阱；海纳百川；低头见天。",
            "modern": "平台接口、以静胜牡、大者先下。",
            "closing": "下流、牝静、以下取、大者下。",
        },
        "chapters": [
            ("承上：烹小鲜", "过渡 · 承上启下"),
            ("五段破译", "大国下流"),
            ("东西方互证", "东西方互证"),
            ("以下取", "大者宜下"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    62: {
        "title_short": "道者万物之奥",
        "yt_tag": "道者万物之奥",
        "bili_dynamic": "道者万物之奥——善人之宝，不善人之所保；坐进此道，为天下贵。",
        "desc_intro": "观念黑盒：《道德经》第六十二章精解——万物之奥与坐进此道。",
        "sections": {
            "plain": "万物之奥；善宝不善保；美言尊行；坐进此道；求得以免。",
            "east_west": "浪子回头；有教无类；斯宾诺莎。",
            "modern": "坐进日常、不弃人、美言市。",
            "closing": "奥、保、坐进、兜底。",
        },
        "chapters": [
            ("承上：大国下流", "过渡 · 承上启下"),
            ("五段破译", "万物之奥"),
            ("东西方互证", "东西方互证"),
            ("坐进此道", "不善亦保"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    63: {
        "title_short": "为无为",
        "yt_tag": "为无为报怨以德",
        "bili_dynamic": "为无为，事无事——报怨以德，图难于其易，圣人犹难之。",
        "desc_intro": "观念黑盒：《道德经》第六十三章精解——为无为与图难于易。",
        "sections": {
            "plain": "为无事事无味；报怨以德；易细；不为大；轻诺犹难。",
            "east_west": "原子习惯；改善；善战无赫赫。",
            "modern": "最小闭环、轻诺、排优先级。",
            "closing": "无为、易细、不为大、犹难。",
        },
        "chapters": [
            ("承上：万物之奥", "过渡 · 承上启下"),
            ("五段破译", "为无为"),
            ("东西方互证", "东西方互证"),
            ("图难于易", "报怨以德"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    64: {
        "title_short": "千里之行",
        "yt_tag": "千里之行始于足下",
        "bili_dynamic": "其安易持，其未兆易谋——千里之行始于足下，慎终如始。",
        "desc_intro": "观念黑盒：《道德经》第六十四章精解——未兆易谋与慎终如始。",
        "sections": {
            "plain": "易持易谋；未有未乱；木台足下；无为无执；慎终。",
            "east_west": "破窗理论；持续改善；防微杜渐。",
            "modern": "技术债、九成败、验收清单。",
            "closing": "早谋、足下、无执、慎终。",
        },
        "chapters": [
            ("承上：为无为", "过渡 · 承上启下"),
            ("五段破译", "千里之行"),
            ("东西方互证", "东西方互证"),
            ("慎终如始", "始于足下"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    65: {
        "title_short": "玄德大顺",
        "yt_tag": "不以智治国",
        "bili_dynamic": "古之善为道者，将以愚之——不以智治国国之福，玄德乃至大顺。",
        "desc_intro": "观念黑盒：《道德经》第六十五章精解——将以愚之与玄德大顺。",
        "sections": {
            "plain": "将以愚之；智多难治；智治国贼福；稽式玄德；大顺。",
            "east_west": "大智若愚；奥卡姆剃刀；减博弈。",
            "modern": "反刷数、简法、减小聪明。",
            "closing": "愚之、戒智、稽式、大顺。",
        },
        "chapters": [
            ("承上：千里之行", "过渡 · 承上启下"),
            ("五段破译", "将以愚之"),
            ("东西方互证", "东西方互证"),
            ("玄德", "不以智治国"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
}


def main() -> int:
    for ch, meta in CHAPTER_META.items():
        narrs = NARRATIONS[ch]
        meta["scenes"] = [(sid, narrs[sid]) for sid in SCENE_ORDER]
        if GROWTH_DYNAMIC_SUFFIX not in meta.get("bili_dynamic", ""):
            meta["bili_dynamic"] = (
                meta["bili_dynamic"].rstrip("。") + "。" + GROWTH_DYNAMIC_SUFFIX
            )

    reset_batch_image_tracking()
    write_chapters(
        CHAPTER_META,
        first_chapter=61,
        max_chapter=65,
        tts_provider="edge",
        read_rate="-15%",
        long_form=True,
        min_commentary_chars=1200,
        scene_images_by_chapter=CHAPTER_SCENE_IMAGES,
        motion="auto",
    )

    for ch in range(61, 66):
        p = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"
        sb = json.loads(p.read_text(encoding="utf-8"))
        sb["tts"]["rate"] = "-10%"
        p.write_text(json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Set commentary TTS rate -10% for ch61–65")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
