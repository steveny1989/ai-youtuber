#!/usr/bin/env python3
"""生成 ch51–ch55 hybrid 讲解分镜（Edge TTS，long_form ≥1200 字）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ch51_55_images import CHAPTER_SCENE_IMAGES  # noqa: E402
from ch51_55_narrations import NARRATIONS, SCENE_ORDER  # noqa: E402
from hybrid_storyboard_util import reset_batch_image_tracking, write_chapters  # noqa: E402

GROWTH_DYNAMIC_SUFFIX = "观念黑盒起号中，欢迎点个关注，八十一讲我们会讲完。"

CHAPTER_META = {
    51: {
        "title_short": "道生之德畜之",
        "yt_tag": "道生之德畜之",
        "bili_dynamic": "道生之，德畜之——生而不有，为而不恃，长而不宰，是谓玄德。",
        "desc_intro": "观念黑盒：《道德经》第五十一章精解——生成链与玄德四不。",
        "sections": {
            "plain": "道生德畜；物形势成；尊道贵德；长育亭毒养覆；玄德。",
            "east_west": "斯宾诺莎自然；生态生境；天地化育。",
            "modern": "平台生而不畜、创业形势、玄德领导。",
            "closing": "认链、尊道贵德、畜覆、玄德四不。",
        },
        "chapters": [
            ("承上：摄生", "过渡 · 承上启下"),
            ("五段破译", "生成链"),
            ("东西方互证", "东西方互证"),
            ("玄德", "生而不有"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    52: {
        "title_short": "天下有始",
        "yt_tag": "天下有始",
        "bili_dynamic": "天下有始，以为天下母——既知其子，复守其母，塞其兑闭其门。",
        "desc_intro": "观念黑盒：《道德经》第五十二章精解——守母、塞兑与习常。",
        "sections": {
            "plain": "天下母；知子守母；塞兑闭门；见小守柔；用光归明。",
            "east_west": "荣格原型；柏拉图理念；坤元。",
            "modern": "算法开兑、知子失母、深度工作边界。",
            "closing": "认母、守母、塞兑、见小守柔、习常。",
        },
        "chapters": [
            ("承上：玄德", "过渡 · 承上启下"),
            ("五段破译", "守母"),
            ("东西方互证", "东西方互证"),
            ("闭门", "塞其兑闭其门"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    53: {
        "title_short": "大道甚夷",
        "yt_tag": "大道甚夷",
        "bili_dynamic": "大道甚夷，而民好径——朝甚除田甚芜，是为盗夸，非道也哉。",
        "desc_intro": "观念黑盒：《道德经》第五十三章精解——好径与盗夸。",
        "sections": {
            "plain": "行大道畏施；甚夷好径；朝除田芜；盗夸。",
            "east_west": "罗马衰期；托尔斯泰简朴；政通人和反读。",
            "modern": "捷径文化、精致穷、表演式努力。",
            "closing": "畏施、识好径、看田仓、戒盗夸。",
        },
        "chapters": [
            ("承上：守母", "过渡 · 承上启下"),
            ("五段破译", "大道甚夷"),
            ("东西方互证", "东西方互证"),
            ("盗夸", "田芜仓虚"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    54: {
        "title_short": "善建者不拔",
        "yt_tag": "善建者不拔",
        "bili_dynamic": "善建者不拔，善抱者不脱——修之于身，其德乃真，以此观天下。",
        "desc_intro": "观念黑盒：《道德经》第五十四章精解——修德五层与由内而外。",
        "sections": {
            "plain": "善建善抱；祭祀不辍；身家乡村国天；以身观身。",
            "east_west": "曾子三省；原子习惯；家庭系统。",
            "modern": "跳层扩品牌、复利习惯、以身观身。",
            "closing": "善建抱、五层序、同构观、代际传。",
        },
        "chapters": [
            ("承上：好径", "过渡 · 承上启下"),
            ("五段破译", "善建善抱"),
            ("东西方互证", "东西方互证"),
            ("五层", "修德五层"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [],
    },
    55: {
        "title_short": "含德之厚",
        "yt_tag": "含德之厚",
        "bili_dynamic": "含德之厚，比于赤子——知和曰常，物壮则老，不道早已。",
        "desc_intro": "观念黑盒：《道德经》第五十五章精解——赤子、和与物壮则老。",
        "sections": {
            "plain": "赤子；不螫不据；握固精至；知和曰常；物壮则老。",
            "east_west": "依恋理论；婴儿呼吸；亚里士多德中道。",
            "modern": "硬核文化、过度养生、少战意。",
            "closing": "厚德赤子、减战意、知和、戒益生。",
        },
        "chapters": [
            ("承上：善建", "过渡 · 承上启下"),
            ("五段破译", "赤子之德"),
            ("东西方互证", "东西方互证"),
            ("和常", "知和曰常"),
            ("认知补丁", "认知补丁"),
        ],
        "scene_motions": {
            "s1": "pan_left",
            "s3": "pan_left",
            "open-ext2": "pan_right",
        },
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
        first_chapter=51,
        max_chapter=55,
        tts_provider="edge",
        read_rate="-15%",
        long_form=True,
        min_commentary_chars=1200,
        scene_images_by_chapter=CHAPTER_SCENE_IMAGES,
        motion="auto",
    )

    import json
    from hybrid_storyboard_util import EXAMPLES

    for ch in range(51, 56):
        p = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"
        sb = json.loads(p.read_text(encoding="utf-8"))
        sb["tts"]["rate"] = "-10%"
        p.write_text(json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Set commentary TTS rate -10% for ch51–55")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
