"""ch46–50 语义配图：scene_id → 文件名（优先本章 chNN_*，不足则意象相近跨章）。"""

from __future__ import annotations

PREFIX = "assets/DaoDeJing/"

CHAPTER_SCENE_IMAGES: dict[int, dict[str, str]] = {
    46: {
        "intro-bridge": "ch46_01_discarded_horse_armor.jpg",
        "open-1": "ch46_03_peaceful_horse.jpg",
        "s1": "ch46_05_iron_hoe.jpg",
        "s2": "ch46_03_ancient_horse.jpg",
        "s3": "ch46_02_knowing_enough.jpg",
        "s4": "ch46_04_single_grain.jpg",
        "s5": "ch46_06_firewood_bundle.jpg",
        "open-ext1": "ch46_07_calloused_hands.jpg",
        "open-ext2": "ch46_03_peaceful_horse.jpg",
        "s-ext2": "ch46_04_pottery_rice.jpg",
        "open-close": "ch46_02_knowing_enough.jpg",
    },
    47: {
        "intro-bridge": "ch47_01_window_universe.jpg",
        "open-1": "ch47_02_universe_in_bowl.jpg",
        "s1": "ch47_03_paper_window_moon.jpg",
        "s2": "ch47_06_solitary_sandal.jpg",
        "s3": "ch47_05_inkstone_ripple.jpg",
        "s4": "ch47_03_moon_through_blind.jpg",
        "s5": "ch47_02_wooden_basin_stars.jpg",
        "open-ext1": "ch47_01_window_universe.jpg",
        "open-ext2": "ch47_04_moongate_mountain.jpg",
        "s-ext2": "ch47_05_inkstone_ripple.jpg",
        "open-close": "ch47_03_paper_window_moon.jpg",
    },
    48: {
        "intro-bridge": "ch48_04_burning_rope.jpg",
        "open-1": "ch48_03_peeling_lacquer.jpg",
        "s1": "ch48_06_burning_scroll.jpg",
        "s2": "ch48_05_wiping_dust.jpg",
        "s3": "ch48_04_straw_rope_cut.jpg",
        "s4": "ch40_04_bead_in_void.jpg",
        "s5": "ch37_02_uncarved_block.jpg",
        "open-ext1": "ch48_03_beating_iron.jpg",
        "open-ext2": "ch48_07_cracked_lacquer.jpg",
        "s-ext2": "ch48_04_burning_rope.jpg",
        "open-close": "ch37_01_nature_overtaking.jpg",
    },
    49: {
        "intro-bridge": "ch49_03_murky_pottery_water.jpg",
        "open-1": "ch49_02_communal_stone_mill.jpg",
        "s1": "ch49_04_communal_trough.jpg",
        "s2": "ch49_05_wooden_ladle.jpg",
        "s3": "ch49_06_misty_stone_bridge.jpg",
        "s4": "ch49_03_murky_pottery_water.jpg",
        "s5": "ch51_01_sheltered_nest.jpg",
        "open-ext1": "ch38_01_coarse_linen_robe.jpg",
        "open-ext2": "ch49_02_communal_stone_mill.jpg",
        "s-ext2": "ch49_05_wooden_ladle.jpg",
        "open-close": "ch49_04_communal_trough.jpg",
    },
    50: {
        "intro-bridge": "ch50_01_missed_strike.jpg",
        "open-1": "ch50_02_safe_passage.jpg",
        "s1": "ch50_04_stone_oil_lamp.jpg",
        "s2": "ch50_03_vine_shield.jpg",
        "s3": "ch40_06_decaying_peony.jpg",
        "s4": "ch50_06_bamboo_staff_forest.jpg",
        "s5": "ch50_03_safe_shield.jpg",
        "open-ext1": "ch54_01_immovable_base.jpg",
        "open-ext2": "ch50_01_missed_strike.jpg",
        "s-ext2": "ch50_07_cave_fire.jpg",
        "open-close": "ch50_04_steady_flame.jpg",
    },
}


def semantic_images_for_chapter(ch: int) -> list[str]:
    mapping = CHAPTER_SCENE_IMAGES[ch]
    from ch46_50_narrations import SCENE_ORDER

    return [PREFIX + mapping[sid] for sid in SCENE_ORDER]
