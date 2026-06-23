"""ch61–65 语义配图：scene_id → 文件名（本章 ChNN 图 + 意象相近跨章）。"""

from __future__ import annotations

PREFIX = "assets/DaoDeJing/"

CHAPTER_SCENE_IMAGES: dict[int, dict[str, str]] = {
    61: {
        "intro-bridge": "大国者下流 - Ch61.jpg",
        "open-1": "母马 - Ch61.jpg",
        "s1": "江海所以能为百谷王者 - Ch66.jpg",
        "s2": "静笃 - Ch16.jpg",
        "s3": "善用人者为之下 - Ch68.jpg",
        "s4": "ch49_02_communal_stone_mill.jpg",
        "s5": "低处流淌的溪水绕过岩石 - Ch01.png",
        "open-ext1": "海平线 - Ch05.jpg",
        "open-ext2": "ch46_03_ancient_horse.jpg",
        "s-ext2": "ch47_03_paper_window_moon.jpg",
        "open-close": "尊道贵德 - Ch51.jpg",
    },
    62: {
        "intro-bridge": "道者万物之奥 - Ch62.jpg",
        "open-1": "ch47_02_wooden_basin_stars.jpg",
        "s1": "天下万物生于有 - Ch40.jpg",
        "s2": "ch50_03_vine_shield.jpg",
        "s3": "ch48_03_peeling_lacquer.jpg",
        "s4": "Palace Eaves - Ch02.jpg",
        "s5": "无名之朴 - Ch37.jpg",
        "open-ext1": "Sage Hands Tea - Ch01.png",
        "open-ext2": "知足 - Ch46.jpg",
        "s-ext2": "ch50_04_stone_oil_lamp.jpg",
        "open-close": "上德不德 - Ch38.jpg",
    },
    63: {
        "intro-bridge": "报怨以德 - Ch63.jpg",
        "open-1": "一根极细、看似柔弱的丝线 - Ch63.jpg",
        "s1": "为道日损 - Ch48.jpg",
        "s2": "和大怨 - Ch79.jpg",
        "s3": "ch48_04_straw_rope_cut.jpg",
        "s4": "ch49_03_murky_pottery_water.jpg",
        "s5": "黑暗中 - Ch63.jpg",
        "open-ext1": "ch46_04_pottery_rice.jpg",
        "open-ext2": "井水 - Ch63.jpg",
        "s-ext2": "炭火 - Ch60.jpg",
        "open-close": "ch47_03_paper_window_moon.jpg",
    },
    64: {
        "intro-bridge": "千里之行 - Ch64.jpg",
        "open-1": "薄冰上刚落下一片枯叶 - Ch64.jpg",
        "s1": "松子 - Ch64.jpg",
        "s2": "善建者不拔 - Ch54.jpg",
        "s3": "岩壁裂缝中渗出的细流 - Ch01.png",
        "s4": "ch50_04_stone_oil_lamp.jpg",
        "s5": "树根 - Ch59.jpg",
        "open-ext1": "ch49_02_communal_stone_mill.jpg",
        "open-ext2": "消失的足迹 - 通用.jpg",
        "s-ext2": "知足 - Ch46.jpg",
        "open-close": "天下万物生于有 - Ch40.jpg",
    },
    65: {
        "intro-bridge": "油灯微光下 - Ch65.jpg",
        "open-1": "绝圣弃智 - Ch19.jpg",
        "s2": "不行的智慧 - Ch47.jpg",
        "s1": "古灯在暗室中点亮 - Ch01.png",
        "s3": "大道甚夷 - Ch53.jpg",
        "s4": "塞其兑 - Ch52.jpg",
        "s5": "无名之朴 - Ch37.jpg",
        "open-ext1": "油灯 - Ch58.jpg",
        "open-ext2": "ch48_03_peeling_lacquer.jpg",
        "s-ext2": "ch50_03_vine_shield.jpg",
        "open-close": "江海所以能为百谷王者 - Ch66.jpg",
    },
}


def semantic_images_for_chapter(ch: int) -> list[str]:
    mapping = CHAPTER_SCENE_IMAGES[ch]
    from ch61_65_narrations import SCENE_ORDER

    return [PREFIX + mapping[sid] for sid in SCENE_ORDER]
