"""ch71–75 语义配图：scene_id → 文件名（本章 ChNN 图 + 意象相近跨章）。"""

from __future__ import annotations

PREFIX = "assets/DaoDeJing/"

CHAPTER_SCENE_IMAGES: dict[int, dict[str, str]] = {
    71: {
        "intro-bridge": "被褐怀玉 - Ch70.jpg",
        "open-1": "不行的智慧 - Ch47.jpg",
        "s1": "塞其兑 - Ch52.jpg",
        "s2": "ch48_03_peeling_lacquer.jpg",
        "s3": "ch50_03_vine_shield.jpg",
        "s4": "Sage Hands Tea - Ch01.png",
        "s5": "大道甚夷 - Ch53.jpg",
        "open-ext1": "ch47_02_wooden_basin_stars.jpg",
        "open-ext2": "ch48_04_straw_rope_cut.jpg",
        "s-ext2": "ch50_04_stone_oil_lamp.jpg",
        "open-close": "上德不德 - Ch38.jpg",
    },
    72: {
        "intro-bridge": "极其寂静的古代军帐内 - Ch73.jpg",
        "open-1": "Palace Eaves - Ch02.jpg",
        "s1": "巨网 - Ch73.jpg",
        "s2": "ch49_02_communal_stone_mill.jpg",
        "s3": "知足 - Ch46.jpg",
        "s4": "被褐怀玉 - Ch70.jpg",
        "s5": "ch47_03_paper_window_moon.jpg",
        "open-ext1": "Flat Wood Board - Ch01.png",
        "open-ext2": "ch46_03_ancient_horse.jpg",
        "s-ext2": "Pure Mist - Ch01.png",
        "open-close": "无名之朴 - Ch37.jpg",
    },
    73: {
        "intro-bridge": "极其寂静的古代军帐内 - Ch73.jpg",
        "open-1": "勇于不敢则活 - Ch73.jpg",
        "s1": "哀兵必胜 - Ch69.jpg",
        "s2": "古寺屋顶上空的星轨 - Ch73.jpg",
        "s3": "静笃 - Ch16.jpg",
        "s4": "雨丝 - Ch73.jpg",
        "s5": "巨网 - Ch73.jpg",
        "open-ext1": "挫其锐 - Ch56.jpg",
        "open-ext2": "ch49_03_murky_pottery_water.jpg",
        "s-ext2": "油灯 - Ch58.jpg",
        "open-close": "尊道贵德 - Ch51.jpg",
    },
    74: {
        "intro-bridge": "代大匠斫者伤手 - Ch74.jpg",
        "open-1": "ch48_04_straw_rope_cut.jpg",
        "s1": "泥泞中 - Ch69.jpg",
        "s2": "箭头 - Ch56.jpg",
        "s3": "ch50_04_stone_oil_lamp.jpg",
        "s4": "代大匠斫者伤手 - Ch74.jpg",
        "s5": "ch48_03_peeling_lacquer.jpg",
        "open-ext1": "ch46_04_pottery_rice.jpg",
        "open-ext2": "极其寂静的古代军帐内 - Ch73.jpg",
        "s-ext2": "ch47_02_wooden_basin_stars.jpg",
        "open-close": "天下万物生于有 - Ch40.jpg",
    },
    75: {
        "intro-bridge": "民之饥 - Ch75.jpg",
        "open-1": "ch46_04_pottery_rice.jpg",
        "s1": "民之饥 - Ch75.jpg",
        "s2": "以正治国 - Ch57.jpg",
        "s3": "ch49_03_murky_pottery_water.jpg",
        "s4": "粗食 - Ch67.jpg",
        "s5": "树根 - Ch59.jpg",
        "open-ext1": "ch49_02_communal_stone_mill.jpg",
        "open-ext2": "ch50_03_vine_shield.jpg",
        "s-ext2": "炭火 - Ch60.jpg",
        "open-close": "江海所以能为百谷王者 - Ch66.jpg",
    },
}


def semantic_images_for_chapter(ch: int) -> list[str]:
    mapping = CHAPTER_SCENE_IMAGES[ch]
    from ch71_75_narrations import SCENE_ORDER

    return [PREFIX + mapping[sid] for sid in SCENE_ORDER]
