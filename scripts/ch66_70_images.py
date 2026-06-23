"""ch66–70 语义配图：scene_id → 文件名（本章 ChNN 图 + 意象相近跨章）。"""

from __future__ import annotations

PREFIX = "assets/DaoDeJing/"

CHAPTER_SCENE_IMAGES: dict[int, dict[str, str]] = {
    66: {
        "intro-bridge": "江海所以能为百谷王者 - Ch66.jpg",
        "open-1": "低处流淌的溪水绕过岩石 - Ch01.png",
        "s1": "大国者下流 - Ch61.jpg",
        "s2": "善用人者为之下 - Ch68.jpg",
        "s3": "ch49_02_communal_stone_mill.jpg",
        "s4": "海平线 - Ch05.jpg",
        "s5": "知足 - Ch46.jpg",
        "open-ext1": "ch46_03_ancient_horse.jpg",
        "open-ext2": "ch47_03_paper_window_moon.jpg",
        "s-ext2": "ch50_04_stone_oil_lamp.jpg",
        "open-close": "尊道贵德 - Ch51.jpg",
    },
    67: {
        "intro-bridge": "慈 - Ch67.jpg",
        "open-1": "门槛 - Ch67.jpg",
        "s1": "无名之朴 - Ch37.jpg",
        "s2": "大道甚夷 - Ch53.jpg",
        "s3": "粗食 - Ch67.jpg",
        "s4": "ch50_03_vine_shield.jpg",
        "s5": "ch48_04_straw_rope_cut.jpg",
        "open-ext1": "Sage Hands Tea - Ch01.png",
        "open-ext2": "ch46_04_pottery_rice.jpg",
        "s-ext2": "油灯 - Ch58.jpg",
        "open-close": "上德不德 - Ch38.jpg",
    },
    68: {
        "intro-bridge": "善用人者为之下 - Ch68.jpg",
        "open-1": "剑柄 - Ch69.jpg",
        "s1": "挫其锐 - Ch56.jpg",
        "s2": "ch48_03_peeling_lacquer.jpg",
        "s3": "败退 - 通用.jpg",
        "s4": "大国者下流 - Ch01.png",
        "s5": "ch50_04_stone_oil_lamp.jpg",
        "open-ext1": "Palace Eaves - Ch02.jpg",
        "open-ext2": "ch49_03_murky_pottery_water.jpg",
        "s-ext2": "Pure Mist - Ch01.png",
        "open-close": "ch47_02_wooden_basin_stars.jpg",
    },
    69: {
        "intro-bridge": "哀兵必胜 - Ch69.jpg",
        "open-1": "泥泞中 - Ch69.jpg",
        "s1": "ch50_03_vine_shield.jpg",
        "s2": "败退 - 通用.jpg",
        "s3": "箭头 - Ch56.jpg",
        "s4": "ch48_04_straw_rope_cut.jpg",
        "s5": "炭火 - Ch60.jpg",
        "open-ext1": "ch49_02_communal_stone_mill.jpg",
        "open-ext2": "ch46_03_ancient_horse.jpg",
        "s-ext2": "ch47_03_paper_window_moon.jpg",
        "open-close": "生之庇所 - Ch50.jpg",
    },
    70: {
        "intro-bridge": "被褐怀玉 - Ch70.jpg",
        "open-1": "不欲琭琭如玉 - Ch39.jpg",
        "s1": "ch47_02_wooden_basin_stars.jpg",
        "s2": "ch49_03_murky_pottery_water.jpg",
        "s3": "塞其兑 - Ch52.jpg",
        "s4": "白玉 - Ch44.jpg",
        "s5": "金玉 - Ch44.jpg",
        "open-ext1": "Flat Wood Board - Ch01.png",
        "open-ext2": "ch48_03_peeling_lacquer.jpg",
        "s-ext2": "ch50_04_stone_oil_lamp.jpg",
        "open-close": "天下万物生于有 - Ch40.jpg",
    },
}


def semantic_images_for_chapter(ch: int) -> list[str]:
    mapping = CHAPTER_SCENE_IMAGES[ch]
    from ch66_70_narrations import SCENE_ORDER

    return [PREFIX + mapping[sid] for sid in SCENE_ORDER]
