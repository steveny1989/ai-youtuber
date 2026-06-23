"""ch76–81 语义配图：scene_id → 文件名（本章 ChNN 图 + 意象相近跨章）。"""

from __future__ import annotations

PREFIX = "assets/DaoDeJing/"

CHAPTER_SCENE_IMAGES: dict[int, dict[str, str]] = {
    76: {
        "intro-bridge": "木强则折 - Ch76.jpg",
        "open-1": "ch50_03_vine_shield.jpg",
        "s1": "Pure Mist - Ch01.png",
        "s2": "ch48_04_straw_rope_cut.jpg",
        "s3": "ch49_03_murky_pottery_water.jpg",
        "s4": "箭头 - Ch56.jpg",
        "s5": "低处流淌的溪水绕过岩石 - Ch01.png",
        "open-ext1": "Sage Hands Tea - Ch01.png",
        "open-ext2": "ch46_03_ancient_horse.jpg",
        "s-ext2": "ch50_04_stone_oil_lamp.jpg",
        "open-close": "天下莫柔弱于水 - Ch78.jpg",
    },
    77: {
        "intro-bridge": "天之道 - Ch77.jpg",
        "open-1": "高山之巅 - Ch77.jpg",
        "s1": "天威不可测 - Ch77.jpg",
        "s2": "粮食 - Ch77.jpg",
        "s3": "ch49_02_communal_stone_mill.jpg",
        "s4": "知足 - Ch46.jpg",
        "s5": "ch47_03_paper_window_moon.jpg",
        "open-ext1": "Palace Eaves - Ch02.jpg",
        "open-ext2": "ch46_04_pottery_rice.jpg",
        "s-ext2": "油灯 - Ch58.jpg",
        "open-close": "尊道贵德 - Ch51.jpg",
    },
    78: {
        "intro-bridge": "天下莫柔弱于水 - Ch78.jpg",
        "open-1": "低处流淌的溪水绕过岩石 - Ch01.png",
        "s1": "海平线 - Ch05.jpg",
        "s2": "ch48_03_peeling_lacquer.jpg",
        "s3": "被褐怀玉 - Ch70.jpg",
        "s4": "大国者下流 - Ch61.jpg",
        "s5": "ch47_02_wooden_basin_stars.jpg",
        "open-ext1": "ch49_03_murky_pottery_water.jpg",
        "open-ext2": "ch50_03_vine_shield.jpg",
        "s-ext2": "ch50_04_stone_oil_lamp.jpg",
        "open-close": "上德不德 - Ch38.jpg",
    },
    79: {
        "intro-bridge": "和大怨 - Ch79.jpg",
        "open-1": "契约 - Ch79.jpg",
        "s1": "ch48_04_straw_rope_cut.jpg",
        "s2": "契约 - Ch79.jpg",
        "s3": "ch49_02_communal_stone_mill.jpg",
        "s4": "ch47_03_paper_window_moon.jpg",
        "s5": "民之饥 - Ch75.jpg",
        "open-ext1": "Sage Hands Tea - Ch01.png",
        "open-ext2": "ch46_03_ancient_horse.jpg",
        "s-ext2": "Pure Mist - Ch01.png",
        "open-close": "天下万物生于有 - Ch40.jpg",
    },
    80: {
        "intro-bridge": "浓白晨雾笼罩的孤绝小村 - Ch80.jpg",
        "open-1": "夜色绝壁上的茅草屋 - Ch80.jpg",
        "s1": "ch46_04_pottery_rice.jpg",
        "s2": "生之徒 - Ch50.jpg",
        "s3": "ch50_03_vine_shield.jpg",
        "s4": "粗食 - Ch67.jpg",
        "s5": "ch47_02_wooden_basin_stars.jpg",
        "open-ext1": "Flat Wood Board - Ch01.png",
        "open-ext2": "ch49_02_communal_stone_mill.jpg",
        "s-ext2": "炭火 - Ch60.jpg",
        "open-close": "ch47_03_paper_window_moon.jpg",
    },
    81: {
        "intro-bridge": "被褐怀玉 - Ch70.jpg",
        "open-1": "塞其兑 - Ch52.jpg",
        "s1": "ch48_03_peeling_lacquer.jpg",
        "s2": "不行的智慧 - Ch47.jpg",
        "s3": "ch49_02_communal_stone_mill.jpg",
        "s4": "江海所以能为百谷王者 - Ch66.jpg",
        "s5": "尊道贵德 - Ch51.jpg",
        "open-ext1": "ch47_02_wooden_basin_stars.jpg",
        "open-ext2": "ch50_04_stone_oil_lamp.jpg",
        "s-ext2": "ch50_03_vine_shield.jpg",
        "open-close": "天下万物生于有 - Ch40.jpg",
    },
}


def semantic_images_for_chapter(ch: int) -> list[str]:
    mapping = CHAPTER_SCENE_IMAGES[ch]
    from ch76_81_narrations import SCENE_ORDER

    return [PREFIX + mapping[sid] for sid in SCENE_ORDER]
