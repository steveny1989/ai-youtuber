#!/usr/bin/env python3
"""生成 ch71–75 hybrid 讲解分镜（Edge TTS，long_form ≥1200 字，含氛围层）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ch71_75_images import CHAPTER_SCENE_IMAGES  # noqa: E402
from ch71_75_narrations import NARRATIONS, SCENE_ORDER  # noqa: E402
from hybrid_storyboard_util import EXAMPLES, reset_batch_image_tracking, write_chapters  # noqa: E402

GROWTH_DYNAMIC_SUFFIX = "观念黑盒起号中，欢迎点个关注，八十一讲我们会讲完。"

CHAPTER_META = {
    71: {
        "title_short": "知不知",
        "yt_tag": "知不知上不知知病",
        "bili_dynamic": "知不知，上；不知知，病——夫唯病病，是以不病。",
        "desc_intro": "观念黑盒：《道德经》第七十一章精解——知不知、不知知与病病不病。",
        "sections": {
            "plain": "知不知上；不知知病；病病不病；圣人不病；收官知钥。",
            "east_west": "苏格拉底；孔子知不知；可证伪。",
            "modern": "装懂、不知清单、我目前的理解是。",
            "closing": "知不知、病病、诊断傲慢。",
        },
        "chapters": [
            ("承上：被褐怀玉", "过渡 · 承上启下"),
            ("五段破译", "知不知"),
            ("东西方互证", "东西方互证"),
            ("病病", "不知知"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    72: {
        "title_short": "民不畏威",
        "yt_tag": "大威至自知自爱",
        "bili_dynamic": "民不畏威，则大威至——圣人自知而不自见，自爱而不自贵。",
        "desc_intro": "观念黑盒：《道德经》第七十二章精解——大威、无狎无厌与自知自爱。",
        "sections": {
            "plain": "大威至；无狎无厌；不厌；自知自爱；去彼取此。",
            "east_west": "暴政恐怖；己所不欲；边界感。",
            "modern": "监控管理、不自见、威与规则。",
            "closing": "大威、不厌、自知、去彼取此。",
        },
        "chapters": [
            ("承上：知不知", "过渡 · 承上启下"),
            ("五段破译", "民不畏威"),
            ("东西方互证", "东西方互证"),
            ("自爱", "自知不自见"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    73: {
        "title_short": "天网恢恢",
        "yt_tag": "勇于不敢则活",
        "bili_dynamic": "勇于敢则杀，勇于不敢则活——天网恢恢，疏而不失。",
        "desc_intro": "观念黑盒：《道德经》第七十三章精解——敢与不敢、天之道与天网。",
        "sections": {
            "plain": "敢杀不敢活；天恶；不争善胜；繟然善谋；天网。",
            "east_west": "慎战；斯多葛；业力。",
            "modern": "杠杆敢、网络硬刚、繟然决策。",
            "closing": "不敢、犹难、天道、天网。",
        },
        "chapters": [
            ("承上：民不畏威", "过渡 · 承上启下"),
            ("五段破译", "天网恢恢"),
            ("东西方互证", "东西方互证"),
            ("繟然", "勇于不敢"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    74: {
        "title_short": "代大匠斫",
        "yt_tag": "民不畏死",
        "bili_dynamic": "民不畏死，奈何以死惧之——代大匠斫者，希有不伤其手。",
        "desc_intro": "观念黑盒：《道德经》第七十四章精解——民不畏死、司杀者与代斫伤手。",
        "sections": {
            "plain": "不畏死；常畏死孰敢；司杀者；代斫；伤手。",
            "east_west": "民为贵；程序正义；不教而杀。",
            "modern": "私刑、越权惩戒、让人值得活。",
            "closing": "畏活、程序、戒代斫。",
        },
        "chapters": [
            ("承上：天网恢恢", "过渡 · 承上启下"),
            ("五段破译", "代大匠斫"),
            ("东西方互证", "东西方互证"),
            ("司杀", "民不畏死"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    75: {
        "title_short": "民之饥",
        "yt_tag": "无以生为贤于贵生",
        "bili_dynamic": "民之饥以其上食税之多——夫唯无以生为者，是贤于贵生。",
        "desc_intro": "观念黑盒：《道德经》第七十五章精解——饥、难治、轻死与无以生为。",
        "sections": {
            "plain": "饥因食税；难治因有为；轻死因厚；无以生为；上改算术。",
            "east_west": "拉弗曲线；自发秩序；轻徭薄赋。",
            "modern": "抽成、折腾文化、攀比、生命减法。",
            "closing": "少税、少为、少厚、无以生为。",
        },
        "chapters": [
            ("承上：代大匠斫", "过渡 · 承上启下"),
            ("五段破译", "民之饥"),
            ("东西方互证", "东西方互证"),
            ("贵生", "无以生为"),
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
        first_chapter=71,
        max_chapter=75,
        tts_provider="edge",
        read_rate="-15%",
        long_form=True,
        min_commentary_chars=1200,
        scene_images_by_chapter=CHAPTER_SCENE_IMAGES,
        motion="auto",
    )

    for ch in range(71, 76):
        p = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"
        sb = json.loads(p.read_text(encoding="utf-8"))
        sb["tts"]["rate"] = "-10%"
        p.write_text(json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Set commentary TTS rate -10% for ch71–75")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
