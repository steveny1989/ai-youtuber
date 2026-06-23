#!/usr/bin/env python3
"""生成 ch66–70 hybrid 讲解分镜（Edge TTS，long_form ≥1200 字，含氛围层）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ch66_70_images import CHAPTER_SCENE_IMAGES  # noqa: E402
from ch66_70_narrations import NARRATIONS, SCENE_ORDER  # noqa: E402
from hybrid_storyboard_util import EXAMPLES, reset_batch_image_tracking, write_chapters  # noqa: E402

GROWTH_DYNAMIC_SUFFIX = "观念黑盒起号中，欢迎点个关注，八十一讲我们会讲完。"

CHAPTER_META = {
    66: {
        "title_short": "江海善下",
        "yt_tag": "江海善下百谷王",
        "bili_dynamic": "江海所以能为百谷王者，以其善下之——不争，故天下莫能与之争。",
        "desc_intro": "观念黑盒：《道德经》第六十六章精解——善下、言下身后与不争之胜。",
        "sections": {
            "plain": "善下百谷王；言下身后；不重不害；乐推不厌；不争。",
            "east_west": "仆人式领导；海纳百川；善战致人。",
            "modern": "抢功、平台接口、父母处上。",
            "closing": "善下、身后、不重、不争。",
        },
        "chapters": [
            ("承上：玄德大顺", "过渡 · 承上启下"),
            ("五段破译", "江海善下"),
            ("东西方互证", "东西方互证"),
            ("不争", "乐推不厌"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    67: {
        "title_short": "我有三宝",
        "yt_tag": "慈俭不敢为天下先",
        "bili_dynamic": "我有三宝：慈、俭、不敢为天下先——舍之则死，天将救之以慈卫之。",
        "desc_intro": "观念黑盒：《道德经》第六十七章精解——道大不肖与三宝。",
        "sections": {
            "plain": "道大不肖；三宝慈俭后；勇广器长；舍三宝死；慈卫。",
            "east_west": "慈悲；斯多葛节制；君子不争。",
            "modern": "烧钱扩张、创始人抢镜、三宝日用。",
            "closing": "不肖、三宝、戒舍、慈卫。",
        },
        "chapters": [
            ("承上：江海善下", "过渡 · 承上启下"),
            ("五段破译", "我有三宝"),
            ("东西方互证", "东西方互证"),
            ("慈卫", "不敢为天下先"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    68: {
        "title_short": "不争之德",
        "yt_tag": "善用人者为之下",
        "bili_dynamic": "善为士者不武，善战者不怒，善胜敌者不与——是谓不争之德。",
        "desc_intro": "观念黑盒：《道德经》第六十八章精解——不武不怒不与与用人之力。",
        "sections": {
            "plain": "不武；不怒；不与；为下；配天。",
            "east_west": "不战而屈人；情绪智力；敬天爱人。",
            "modern": "谈判不怒、价格战不与、为下带团队。",
            "closing": "不武、不怒、不与、为下。",
        },
        "chapters": [
            ("承上：我有三宝", "过渡 · 承上启下"),
            ("五段破译", "不争之德"),
            ("东西方互证", "东西方互证"),
            ("用人", "善用人下"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    69: {
        "title_short": "哀者胜",
        "yt_tag": "不敢为主哀者胜",
        "bili_dynamic": "用兵有言：不敢为主而为客，不敢进寸而退尺——抗兵相加，哀者胜矣。",
        "desc_intro": "观念黑盒：《道德经》第六十九章精解——为客退尺、轻敌丧宝与哀兵。",
        "sections": {
            "plain": "为客；退尺；行无行；轻敌丧宝；哀胜。",
            "east_west": "先不可胜；谦卦；克制武力。",
            "modern": "轻敌竞争、进寸争吵、哀而知代价。",
            "closing": "为客、退尺、戒轻、哀胜。",
        },
        "chapters": [
            ("承上：不争之德", "过渡 · 承上启下"),
            ("五段破译", "哀者胜"),
            ("东西方互证", "东西方互证"),
            ("轻敌", "退尺不进寸"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    70: {
        "title_short": "被褐怀玉",
        "yt_tag": "吾言甚易知莫能行",
        "bili_dynamic": "吾言甚易知，甚易行，天下莫能知莫能行——圣人被褐怀玉。",
        "desc_intro": "观念黑盒：《道德经》第七十章精解——言易知行难与被褐怀玉。",
        "sections": {
            "plain": "易知易行莫能；言有宗事有君；无知不我知；希则贵；被褐怀玉。",
            "east_west": "知行合一；窄门；大巧若拙。",
            "modern": "收藏不等于行、人设与内核、一条道理一动作。",
            "closing": "莫能行、宗君、希贵、褐玉。",
        },
        "chapters": [
            ("承上：哀者胜", "过渡 · 承上启下"),
            ("五段破译", "被褐怀玉"),
            ("东西方互证", "东西方互证"),
            ("知行合一", "言有宗"),
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
        first_chapter=66,
        max_chapter=70,
        tts_provider="edge",
        read_rate="-15%",
        long_form=True,
        min_commentary_chars=1200,
        scene_images_by_chapter=CHAPTER_SCENE_IMAGES,
        motion="auto",
    )

    for ch in range(66, 71):
        p = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"
        sb = json.loads(p.read_text(encoding="utf-8"))
        sb["tts"]["rate"] = "-10%"
        p.write_text(json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Set commentary TTS rate -10% for ch66–70")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
