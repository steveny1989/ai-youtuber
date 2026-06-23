#!/usr/bin/env python3
"""生成 ch41–ch45 hybrid 讲解分镜（Edge TTS，long_form ≥1200 字）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ch41_45_narrations import NARRATIONS, SCENE_ORDER  # noqa: E402
from hybrid_storyboard_util import reset_batch_image_tracking, write_chapters  # noqa: E402

GROWTH_DYNAMIC_SUFFIX = "观念黑盒起号中，欢迎点个关注，八十一讲我们会讲完。"

CHAPTER_META = {
    41: {
        "title_short": "上士闻道",
        "yt_tag": "上士闻道",
        "bili_dynamic": "上士勤行，中士若亡，下士大笑——不笑不足以为道。",
        "desc_intro": "观念黑盒：《道德经》第四十一章精解——闻道三士与大音希声。",
        "sections": {
            "plain": "三士；不笑；建言悖论；大音希声；善贷且成。",
            "east_west": "苏格拉底；禅宗以指见月；康德物自体。",
            "modern": "收藏即闻道、执行即上士、悖论进阶。",
            "closing": "识三士、认悖论、敬无名、勤而行。",
        },
        "chapters": [
            ("承上：三士", "过渡 · 承上启下"),
            ("分层破译", "闻道三士"),
            ("东西方互证", "东西方互证"),
            ("知与行", "闻与行"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    42: {
        "title_short": "道生一",
        "yt_tag": "道生一",
        "bili_dynamic": "道生一，一生万物——冲气以为和，强梁者不得其死。",
        "desc_intro": "观念黑盒：《道德经》第四十二章精解——生成链与阴阳冲和。",
        "sections": {
            "plain": "道生一；阴阳冲和；孤寡称；强梁；教父。",
            "east_west": "毕达哥拉斯；系统论涌现。",
            "modern": "增长与合规、强梁商业、配比。",
            "closing": "守一、配阴阳、戒强梁、认损益。",
        },
        "chapters": [
            ("承上：生成", "过渡 · 承上启下"),
            ("五段破译", "道生万物"),
            ("东西方互证", "东西方互证"),
            ("强梁", "冲气与强梁"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    43: {
        "title_short": "天下之至柔",
        "yt_tag": "天下之至柔",
        "bili_dynamic": "至柔驰骋至坚，无有入无间——不言之教，天下希及。",
        "desc_intro": "观念黑盒：《道德经》第四十三章精解——至柔、无有与不言。",
        "sections": {
            "plain": "至柔至坚；无有入无间；无为有益；不言之教。",
            "east_west": "斯多葛二分；示范伦理。",
            "modern": "信任入缝、微管理、环境改习惯。",
            "closing": "用柔、敬无有、信无为、行不言。",
        },
        "chapters": [
            ("承上：至柔", "过渡 · 承上启下"),
            ("四句破译", "四句破译"),
            ("东西方互证", "东西方互证"),
            ("不言", "不言之教"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    44: {
        "title_short": "名与身孰亲",
        "yt_tag": "名与身孰亲",
        "bili_dynamic": "名身货得四问——知足不辱，知止不殆，可以长久。",
        "desc_intro": "观念黑盒：《道德经》第四十四章精解——取舍与知足知止。",
        "sections": {
            "plain": "名身货得；甚爱多藏；知足知止。",
            "east_west": "斯多葛可控；佛教少欲。",
            "modern": "FOMO、囤货款、标签内耗。",
            "closing": "身先名、货为身用、戒 hoarding、知足止。",
        },
        "chapters": [
            ("承上：取舍", "过渡 · 承上启下"),
            ("四问破译", "四问破译"),
            ("东西方互证", "东西方互证"),
            ("知足", "知足知止"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    45: {
        "title_short": "大成若缺",
        "yt_tag": "大成若缺",
        "bili_dynamic": "大成若缺，大盈若冲——大巧若拙，清静为天下正。",
        "desc_intro": "观念黑盒：《道德经》第四十五章精解——大若悖论与清静为正。",
        "sections": {
            "plain": "成缺盈冲；直屈巧拙辩讷；躁静；清静为正。",
            "east_west": "侘寂；维特根斯坦后期。",
            "modern": "完美主义、藏锋、少噪。",
            "closing": "成若缺、盈若冲、藏锋、清静为正。",
        },
        "chapters": [
            ("承上：大若", "过渡 · 承上启下"),
            ("五组破译", "大若悖论"),
            ("东西方互证", "东西方互证"),
            ("清静", "清静为正"),
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
        first_chapter=41,
        max_chapter=45,
        tts_provider="edge",
        read_rate="-15%",
        long_form=True,
        min_commentary_chars=1200,
    )

    import json
    from hybrid_storyboard_util import EXAMPLES

    for ch in range(41, 46):
        p = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"
        sb = json.loads(p.read_text(encoding="utf-8"))
        sb["tts"]["rate"] = "-10%"
        p.write_text(json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Set commentary TTS rate -10% for ch41–45")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
