#!/usr/bin/env python3
"""生成 ch46–ch50 hybrid 讲解分镜（Edge TTS，long_form ≥1200 字）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ch46_50_narrations import NARRATIONS, SCENE_ORDER  # noqa: E402
from ch46_50_images import CHAPTER_SCENE_IMAGES  # noqa: E402
from hybrid_storyboard_util import reset_batch_image_tracking, write_chapters  # noqa: E402

GROWTH_DYNAMIC_SUFFIX = "观念黑盒起号中，欢迎点个关注，八十一讲我们会讲完。"

CHAPTER_META = {
    46: {
        "title_short": "天下有道",
        "yt_tag": "天下有道",
        "bili_dynamic": "有道走马以粪，无道戎马生郊——祸莫大于不知足，知足之足常足矣。",
        "desc_intro": "观念黑盒：《道德经》第四十六章精解——有道无道与知足之足。",
        "sections": {
            "plain": "走马以粪；戎马生郊；不知足欲得；知足之足。",
            "east_west": "Pax Romana；亚当·斯密分工。",
            "modern": "商战备战、burnout、马力在耕还是在战。",
            "closing": "观马力、识不知足、戒欲得、知足之足。",
        },
        "chapters": [
            ("承上：清静", "过渡 · 承上启下"),
            ("四段破译", "有道无道"),
            ("东西方互证", "东西方互证"),
            ("马力", "马力在耕还是在战"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    47: {
        "title_short": "不出户知天下",
        "yt_tag": "不出户知天下",
        "bili_dynamic": "不出户知天下，不窥牖见天道——其出弥远，其知弥少。",
        "desc_intro": "观念黑盒：《道德经》第四十七章精解——不行而知与弥远弥少。",
        "sections": {
            "plain": "户牖；弥远弥少；不行而知；不见而明不为而成。",
            "east_west": "康德现象界；笛卡尔我思。",
            "modern": "信息焦虑、游学打卡、订阅过载。",
            "closing": "户牖足矣、戒弥远、不行而知、不见而明。",
        },
        "chapters": [
            ("承上：天下", "过渡 · 承上启下"),
            ("五段破译", "户牖之知"),
            ("东西方互证", "东西方互证"),
            ("弥远", "其出弥远其知弥少"),
            ("认知补丁", "认知补丁"),
        ],
        "scene_motions": {
            "s1": "pan_up",
            "s4": "pan_up",
            "open-ext1": "pan_up",
        },
        "scenes": [],
    },
    48: {
        "title_short": "为道日损",
        "yt_tag": "为道日损",
        "bili_dynamic": "为学日益，为道日损——损之又损以至于无为，取天下常以无事。",
        "desc_intro": "观念黑盒：《道德经》第四十八章精解——日益日损与无为无不为。",
        "sections": {
            "plain": "日益日损；损之又损；无为无不为；取天下以无事。",
            "east_west": "奥卡姆剃刀；乔布斯 focus；佛教戒定慧。",
            "modern": "知识订阅、数字极简、无效会议。",
            "closing": "双轨、损之又损、无为无不为、取天下以无事。",
        },
        "chapters": [
            ("承上：知", "过渡 · 承上启下"),
            ("四段破译", "日益与日损"),
            ("东西方互证", "东西方互证"),
            ("无事", "取天下以无事"),
            ("认知补丁", "认知补丁"),
        ],
        "scene_motions": {
            "s2": "pan_right",
            "s3": "pan_right",
            "open-ext2": "pan_left",
        },
        "scenes": [],
    },
    49: {
        "title_short": "圣人常无心",
        "yt_tag": "圣人常无心",
        "bili_dynamic": "圣人常无心，以百姓心为心——亦善亦信，歙歙孩之。",
        "desc_intro": "观念黑盒：《道德经》第四十九章精解——无心、德善德信与空芯领导。",
        "sections": {
            "plain": "无心；亦善德善；亦信德信；歙歙浑心；孩之。",
            "east_west": "孔子勿施；罗杰斯无条件关注；servant leadership。",
            "modern": "取消文化、算法乖用户、条件式善信。",
            "closing": "常无心、德善、德信、歙歙孩之。",
        },
        "chapters": [
            ("承上：日损", "过渡 · 承上启下"),
            ("五段破译", "无心善信"),
            ("东西方互证", "东西方互证"),
            ("空芯", "空芯领导力"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    50: {
        "title_short": "出生入死",
        "yt_tag": "出生入死",
        "bili_dynamic": "生之死地十有三——以其生生之厚，善摄生者无死地。",
        "desc_intro": "观念黑盒：《道德经》第五十章精解——十有三与善摄生无死地。",
        "sections": {
            "plain": "出生入死；十有三；生生之厚；善摄生；无死地。",
            "east_west": "斯多葛二分；塔勒布反脆弱；不立于危墙。",
            "modern": "加班文化、All in、burnout。",
            "closing": "识三类、戒厚厚、善摄生、无死地。",
        },
        "chapters": [
            ("承上：无心", "过渡 · 承上启下"),
            ("五段破译", "十有三"),
            ("东西方互证", "东西方互证"),
            ("死地", "善摄生无死地"),
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
        first_chapter=46,
        max_chapter=50,
        tts_provider="edge",
        read_rate="-15%",
        long_form=True,
        min_commentary_chars=1200,
        scene_images_by_chapter=CHAPTER_SCENE_IMAGES,
        motion="auto",
    )

    import json
    from hybrid_storyboard_util import EXAMPLES

    for ch in range(46, 51):
        p = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"
        sb = json.loads(p.read_text(encoding="utf-8"))
        sb["tts"]["rate"] = "-10%"
        p.write_text(json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Set commentary TTS rate -10% for ch46–50")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
