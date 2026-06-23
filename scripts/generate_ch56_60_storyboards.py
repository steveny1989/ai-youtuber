#!/usr/bin/env python3
"""生成 ch56–60 hybrid 讲解分镜（Edge TTS，long_form ≥1200 字，含氛围层）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ch56_60_images import CHAPTER_SCENE_IMAGES  # noqa: E402
from ch56_60_narrations import NARRATIONS, SCENE_ORDER  # noqa: E402
from hybrid_storyboard_util import EXAMPLES, reset_batch_image_tracking, write_chapters  # noqa: E402

GROWTH_DYNAMIC_SUFFIX = "观念黑盒起号中，欢迎点个关注，八十一讲我们会讲完。"

CHAPTER_META = {
    56: {
        "title_short": "知者不言",
        "yt_tag": "知者不言",
        "bili_dynamic": "知者不言，言者不知——挫其锐，和其光，同其尘，是谓玄同。",
        "desc_intro": "观念黑盒：《道德经》第五十六章精解——不言、和光同尘与玄同。",
        "sections": {
            "plain": "知者不言；塞兑闭门；挫锐解纷；和光同尘；玄同为贵。",
            "east_west": "维特根斯坦沉默；禅宗不立文字；天何言哉。",
            "modern": "解释型人格、和光同尘、玄同练习。",
            "closing": "不言、闭门、和光、玄同。",
        },
        "chapters": [
            ("承上：含德之厚", "过渡 · 承上启下"),
            ("五段破译", "知者不言"),
            ("东西方互证", "东西方互证"),
            ("玄同", "和光同尘"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    57: {
        "title_short": "以正治国",
        "yt_tag": "以正治国",
        "bili_dynamic": "以正治国，以奇用兵，以无事取天下——我无为而民自化。",
        "desc_intro": "观念黑盒：《道德经》第五十七章精解——以正治国与民自化。",
        "sections": {
            "plain": "以正奇无事；忌讳民贫；利器国昏；法令盗贼；四我自化。",
            "east_west": "看不见的手；无为而治；孙子以奇用兵。",
            "modern": "KPI 忌讳、算法利器、少开会。",
            "closing": "以正、戒折腾、简法、我静。",
        },
        "chapters": [
            ("承上：玄同", "过渡 · 承上启下"),
            ("五段破译", "以正治国"),
            ("东西方互证", "东西方互证"),
            ("民自化", "我无为"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    58: {
        "title_short": "其政闷闷",
        "yt_tag": "其政闷闷",
        "bili_dynamic": "其政闷闷，其民淳淳——祸兮福之所倚，方而不割，光而不耀。",
        "desc_intro": "观念黑盒：《道德经》第五十八章精解——闷闷察察与祸福相依。",
        "sections": {
            "plain": "闷闷淳淳；察察缺缺；祸福相依；正奇互变；四不。",
            "east_west": "斯多葛；亢则害；花未全开月未圆。",
            "modern": "察察管理、祸福练习、光而不耀。",
            "closing": "政闷、祸福、戒极、四不。",
        },
        "chapters": [
            ("承上：无事", "过渡 · 承上启下"),
            ("五段破译", "闷闷察察"),
            ("东西方互证", "东西方互证"),
            ("四不", "方而不割"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    59: {
        "title_short": "莫若啬",
        "yt_tag": "治人事天莫若啬",
        "bili_dynamic": "治人事天，莫若啬——重积德，深根固柢，长生久视。",
        "desc_intro": "观念黑盒：《道德经》第五十九章精解——啬、重积德与深根。",
        "sections": {
            "plain": "莫若啬；早服；重积德；有国之母；深根固柢。",
            "east_west": "富兰克林节俭；守破离；积肥于田。",
            "modern": "少开会、重兑现、慢公司。",
            "closing": "啬、早服、德厚、深根。",
        },
        "chapters": [
            ("承上：闷闷", "过渡 · 承上启下"),
            ("五段破译", "莫若啬"),
            ("东西方互证", "东西方互证"),
            ("深根", "长生久视"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    60: {
        "title_short": "烹小鲜",
        "yt_tag": "治大国若烹小鲜",
        "bili_dynamic": "治大国，若烹小鲜——两不相伤，故德交归焉。",
        "desc_intro": "观念黑盒：《道德经》第六十章精解——烹小鲜与两不相伤。",
        "sections": {
            "plain": "烹小鲜；以道莅；神不伤人；两不相伤；德交归。",
            "east_west": "治未病；最小有效剂量；改善哲学。",
            "modern": "少改组织架构、戒恐惧 KPI。",
            "closing": "少翻、道莅、不伤人、德交。",
        },
        "chapters": [
            ("承上：啬", "过渡 · 承上启下"),
            ("五段破译", "烹小鲜"),
            ("东西方互证", "东西方互证"),
            ("不相伤", "德交归"),
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
        first_chapter=56,
        max_chapter=60,
        tts_provider="edge",
        read_rate="-15%",
        long_form=True,
        min_commentary_chars=1200,
        scene_images_by_chapter=CHAPTER_SCENE_IMAGES,
        motion="auto",
    )

    for ch in range(56, 61):
        p = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"
        sb = json.loads(p.read_text(encoding="utf-8"))
        sb["tts"]["rate"] = "-10%"
        p.write_text(json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Set commentary TTS rate -10% for ch56–60")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
