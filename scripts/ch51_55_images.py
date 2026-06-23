"""ch51–55 语义配图：scene_id → 文件名（本章 ChNN 图 + 意象相近跨章）。"""

from __future__ import annotations

PREFIX = "assets/DaoDeJing/"

CHAPTER_SCENE_IMAGES: dict[int, dict[str, str]] = {
    51: {
        "intro-bridge": "尊道贵德 - Ch51.jpg",
        "open-1": "天下万物生于有 - Ch40.jpg",
        "s1": "有生于无 - Ch40.jpg",
        "s2": "ch49_02_communal_stone_mill.jpg",
        "s3": "大道的凝聚 - 通用.jpg",
        "s4": "生之庇所 - Ch50.jpg",
        "s5": "上德不德 - Ch38.jpg",
        "open-ext1": "ch49_03_murky_pottery_water.jpg",
        "open-ext2": "众生行 - Ch49.jpg",
        "s-ext2": "ch49_02_communal_stone_mill.jpg",
        "open-close": "尊道贵德 - Ch51.jpg",
    },
    52: {
        "intro-bridge": "塞其兑 - Ch52.jpg",
        "open-1": "归根 - Ch16.jpg",
        "s1": "树根 - Ch05.jpg",
        "s2": "同源 - Ch49.jpg",
        "s3": "塞其兑 - Ch52.jpg",
        "s4": "一根极细、看似柔弱的丝线 - Ch63.jpg",
        "s5": "Pure Mist - Ch01.png",
        "open-ext1": "圆形的月亮门 - Ch01.png",
        "open-ext2": "从幽暗狭窄的长廊望向门外 - Ch04.jpg",
        "s-ext2": "一扇完全敞开的柴门 - Ch05.jpg",
        "open-close": "塞其兑 - Ch52.jpg",
    },
    53: {
        "intro-bridge": "大道甚夷 - Ch53.jpg",
        "open-1": "Pure Forest Walk - Ch01.png",
        "s1": "大道甚夷 - Ch53.jpg",
        "s2": "栈道风雪 - 通用.jpg",
        "s3": "ch48_03_peeling_lacquer.jpg",
        "s4": "ch48_04_straw_rope_cut.jpg",
        "s5": "失道而后德 - Ch01.png",
        "open-ext1": "Palace Eaves - Ch02.jpg",
        "open-ext2": "大道甚夷 - Ch53.jpg",
        "s-ext2": "ch50_04_stone_oil_lamp.jpg",
        "open-close": "Pure Courtyard - Ch01.png",
    },
    54: {
        "intro-bridge": "善建者不拔 - Ch54.jpg",
        "open-1": "树根 - Ch05.jpg",
        "s1": "善建者不拔 - Ch54.jpg",
        "s2": "一块古老的石碑 - Ch04.jpg",
        "s3": "ch49_02_communal_stone_mill.jpg",
        "s4": "Pure Mirror - Ch01.png",
        "s5": "Sage Insight - Ch01.png",
        "open-ext1": "百姓心 - Ch49.jpg",
        "open-ext2": "善建者不拔 - Ch54.jpg",
        "s-ext2": "Flat Wood Board - Ch01.png",
        "open-close": "善建者不拔 - Ch54.jpg",
    },
    55: {
        "intro-bridge": "刚柔转换 - 通用.jpg",
        "open-1": "天下之至柔 - Ch01.png",
        "s1": "Pure Pebble - Ch01.png",
        "s2": "ch50_03_vine_shield.jpg",
        "s3": "一根极其纤细的白色丝线 - Ch01.png",
        "s4": "Pure Ripples - Ch01.png",
        "s5": "弱者道之用 - Ch40.jpg",
        "open-ext1": "Sage Hands Tea - Ch01.png",
        "open-ext2": "摄生 - Ch50.jpg",
        "s-ext2": "ch50_04_stone_oil_lamp.jpg",
        "open-close": "一根极细、看似柔弱的丝线 - Ch63.jpg",
    },
}


def semantic_images_for_chapter(ch: int) -> list[str]:
    mapping = CHAPTER_SCENE_IMAGES[ch]
    from ch51_55_narrations import SCENE_ORDER

    return [PREFIX + mapping[sid] for sid in SCENE_ORDER]
