#!/usr/bin/env python3
"""生成 ch76–81 hybrid 讲解分镜（Edge TTS，long_form ≥1200 字，含氛围层）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ch76_81_images import CHAPTER_SCENE_IMAGES  # noqa: E402
from ch76_81_narrations import NARRATIONS, SCENE_ORDER  # noqa: E402
from hybrid_storyboard_util import EXAMPLES, reset_batch_image_tracking, write_chapters  # noqa: E402

GROWTH_DYNAMIC_SUFFIX = "观念黑盒起号中，欢迎点个关注，八十一讲我们会讲完。"

CHAPTER_META = {
    76: {
        "title_short": "柔弱者生",
        "yt_tag": "强大处下柔弱处上",
        "bili_dynamic": "人之生也柔弱，其死也坚强——故坚强者死之徒，柔弱者生之徒。",
        "desc_intro": "观念黑盒：《道德经》第七十六章精解——生柔死坚、兵强木强与柔弱处上。",
        "sections": {
            "plain": "生柔死坚；枯槁；死徒生徒；兵强不胜；强大处下。",
            "east_west": "以柔克刚；庖丁解牛；幼态持续。",
            "modern": "文化硬化、brittle、弹性目标。",
            "closing": "生柔、不brittle、兵强、处下。",
        },
        "chapters": [
            ("承上：民之饥", "过渡 · 承上启下"),
            ("五段破译", "柔弱者生"),
            ("东西方互证", "东西方互证"),
            ("木强则折", "兵强不胜"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    77: {
        "title_short": "天之道张弓",
        "yt_tag": "损有余而补不足",
        "bili_dynamic": "天之道，其犹张弓与——损有余而补不足；人之道则不然。",
        "desc_intro": "观念黑盒：《道德经》第七十七章精解——张弓、损补与为而不恃。",
        "sections": {
            "plain": "张弓；抑高举起；损补；人道反；有余奉天下；不见贤。",
            "east_west": "差异原则；布施；负反馈。",
            "modern": "马太效应、让利、不见贤。",
            "closing": "张弓、损补、逆人道、不处功。",
        },
        "chapters": [
            ("承上：柔弱者生", "过渡 · 承上启下"),
            ("五段破译", "天之道"),
            ("东西方互证", "东西方互证"),
            ("损补", "人之道反"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    78: {
        "title_short": "柔弱于水",
        "yt_tag": "正言若反",
        "bili_dynamic": "天下莫柔弱于水，而攻坚强者莫之能胜——正言若反。",
        "desc_intro": "观念黑盒：《道德经》第七十八章精解——水胜强、受垢与正言若反。",
        "sections": {
            "plain": "水胜强；无以易；莫能行；受垢王；正言若反。",
            "east_west": "智者乐水；非暴力；为义受辱。",
            "modern": "水式竞争、受垢、反看常识。",
            "closing": "水、弱胜强、受垢、若反。",
        },
        "chapters": [
            ("承上：天之道", "过渡 · 承上启下"),
            ("五段破译", "柔弱于水"),
            ("东西方互证", "东西方互证"),
            ("受垢", "正言若反"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    79: {
        "title_short": "和大怨",
        "yt_tag": "执左契不责人",
        "bili_dynamic": "和大怨，必有余怨——圣人执左契而不责于人，天道无亲常与善人。",
        "desc_intro": "观念黑盒：《道德经》第七十九章精解——余怨、左契与司契司彻。",
        "sections": {
            "plain": "有余怨；执左不责；司契彻；无亲善人。",
            "east_west": "和解协议；恕；和而不同。",
            "modern": "假和好、司彻复盘、写契。",
            "closing": "真修复、不责、司契、无亲。",
        },
        "chapters": [
            ("承上：柔弱于水", "过渡 · 承上启下"),
            ("五段破译", "和大怨"),
            ("东西方互证", "东西方互证"),
            ("左契", "天道无亲"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    80: {
        "title_short": "小国寡民",
        "yt_tag": "甘食美服乐其俗",
        "bili_dynamic": "小国寡民——甘其食，美其服，安其居，乐其俗，相望不相往来。",
        "desc_intro": "观念黑盒：《道德经》第八十章精解——什伯不用、重死不远徙与简俗。",
        "sections": {
            "plain": "什伯不用；重死不远徙；舟舆甲兵不启；甘食乐俗；不相往来。",
            "east_west": "瓦尔登；侘寂；数字极简。",
            "modern": "工具焦虑、远方焦虑、消息边界。",
            "closing": "简、惜根、克制、脚下好。",
        },
        "chapters": [
            ("承上：和大怨", "过渡 · 承上启下"),
            ("五段破译", "小国寡民"),
            ("东西方互证", "东西方互证"),
            ("乐俗", "不相往来"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    81: {
        "title_short": "为而不争",
        "yt_tag": "信言不美美言不信",
        "bili_dynamic": "信言不美，美言不信——天之道利而不害，圣人之道为而不争。八十一讲完结。",
        "desc_intro": "观念黑盒：《道德经》第八十一章精解——全书终章：信美相反、不积愈有、为而不争。",
        "sections": {
            "plain": "信美相反；善不辩知不博；不积愈有；利而不害；为而不争。",
            "east_west": "反诡辩；讷于言敏于行；开源。",
            "modern": "标题党、交付不争功、收官行动。",
            "closing": "信言、不积、为不争、完结。",
        },
        "chapters": [
            ("承上：小国寡民", "过渡 · 承上启下"),
            ("五段破译", "为而不争"),
            ("东西方互证", "东西方互证"),
            ("不积", "利而不害"),
            ("认知补丁", "八十一讲完结"),
        ],
        "scenes": [],
    },
}


def main() -> int:
    for ch, meta in CHAPTER_META.items():
        narrs = NARRATIONS[ch]
        meta["scenes"] = [(sid, narrs[sid]) for sid in SCENE_ORDER]
        dynamic = meta.get("bili_dynamic", "")
        if ch == 81:
            if GROWTH_DYNAMIC_SUFFIX not in dynamic:
                meta["bili_dynamic"] = (
                    dynamic.rstrip("。") + "。"
                    + "八十一讲完结，感谢一路听到这里。"
                    + GROWTH_DYNAMIC_SUFFIX
                )
        elif GROWTH_DYNAMIC_SUFFIX not in dynamic:
            meta["bili_dynamic"] = (
                dynamic.rstrip("。") + "。" + GROWTH_DYNAMIC_SUFFIX
            )

    reset_batch_image_tracking()
    write_chapters(
        CHAPTER_META,
        first_chapter=76,
        max_chapter=81,
        tts_provider="edge",
        read_rate="-15%",
        long_form=True,
        min_commentary_chars=1200,
        scene_images_by_chapter=CHAPTER_SCENE_IMAGES,
        motion="auto",
    )

    for ch in range(76, 82):
        p = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"
        sb = json.loads(p.read_text(encoding="utf-8"))
        sb["tts"]["rate"] = "-10%"
        p.write_text(json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Set commentary TTS rate -10% for ch76–81")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
