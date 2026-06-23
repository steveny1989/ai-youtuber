"""ch56–60 语义配图：scene_id → 文件名（本章 ChNN 图 + 意象相近跨章）。"""

from __future__ import annotations

PREFIX = "assets/DaoDeJing/"

CHAPTER_SCENE_IMAGES: dict[int, dict[str, str]] = {
    56: {
        "intro-bridge": "挫其锐 - Ch56.jpg",
        "open-1": "一束光切过暗室 - Ch56.jpg",
        "s1": "悬崖边盘腿打坐的修道者 - Ch56.jpg",
        "s2": "透过磨砂质感的厚重旧纸窗 - Ch56.jpg",
        "s3": "箭头 - Ch56.jpg",
        "s4": "ch49_03_murky_pottery_water.jpg",
        "s5": "死结 - Ch56.jpg",
        "open-ext1": "塞其兑 - Ch52.jpg",
        "open-ext2": "ch48_03_peeling_lacquer.jpg",
        "s-ext2": "Pure Mist - Ch01.png",
        "open-close": "ch47_03_paper_window_moon.jpg",
    },
    57: {
        "intro-bridge": "以正治国 - Ch57.jpg",
        "open-1": "竹简 - Ch57.jpg",
        "s1": "却走马以粪 - Ch46.jpg",
        "s2": "ch46_03_ancient_horse.jpg",
        "s3": "ch48_04_straw_rope_cut.jpg",
        "s4": "大道甚夷 - Ch53.jpg",
        "s5": "ch49_02_communal_stone_mill.jpg",
        "open-ext1": "Palace Eaves - Ch02.jpg",
        "open-ext2": "知足 - Ch46.jpg",
        "s-ext2": "ch50_04_stone_oil_lamp.jpg",
        "open-close": "无名之朴 - Ch37.jpg",
    },
    58: {
        "intro-bridge": "方而不割 - Ch58.jpg",
        "open-1": "大殿深处 - Ch58.jpg",
        "s1": "麻纸 - Ch58.jpg",
        "s2": "油灯 - Ch58.jpg",
        "s3": "ch48_04_straw_rope_cut.jpg",
        "s4": "ch49_03_murky_pottery_water.jpg",
        "s5": "善建者不拔 - Ch54.jpg",
        "open-ext1": "Sage Hands Tea - Ch01.png",
        "open-ext2": "ch48_03_peeling_lacquer.jpg",
        "s-ext2": "Flat Wood Board - Ch01.png",
        "open-close": "ch47_02_wooden_basin_stars.jpg",
    },
    59: {
        "intro-bridge": "治人事天莫若啬 - Ch59.jpg",
        "open-1": "树根 - Ch59.jpg",
        "s1": "ch46_04_pottery_rice.jpg",
        "s2": "ch50_04_stone_oil_lamp.jpg",
        "s3": "善建者不拔 - Ch54.jpg",
        "s4": "ch48_04_straw_rope_cut.jpg",
        "s5": "ch50_03_vine_shield.jpg",
        "open-ext1": "知足 - Ch46.jpg",
        "open-ext2": "ch49_02_communal_stone_mill.jpg",
        "s-ext2": "炭火 - Ch60.jpg",
        "open-close": "天下万物生于有 - Ch40.jpg",
    },
    60: {
        "intro-bridge": "炭火 - Ch60.jpg",
        "open-1": "鱼不可脱于渊 - Ch36.jpg",
        "s1": "避险之路 - Ch50.jpg",
        "s2": "ch49_03_murky_pottery_water.jpg",
        "s3": "ch50_04_stone_oil_lamp.jpg",
        "s4": "ch49_02_communal_stone_mill.jpg",
        "s5": "尊道贵德 - Ch51.jpg",
        "open-ext1": "ch50_03_vine_shield.jpg",
        "open-ext2": "ch46_03_ancient_horse.jpg",
        "s-ext2": "ch47_02_wooden_basin_stars.jpg",
        "open-close": "生之庇所 - Ch50.jpg",
    },
}


def semantic_images_for_chapter(ch: int) -> list[str]:
    mapping = CHAPTER_SCENE_IMAGES[ch]
    from ch56_60_narrations import SCENE_ORDER

    return [PREFIX + mapping[sid] for sid in SCENE_ORDER]
