"""讲解分镜配图：语义打分 + 章节冷却（三章内不重复同图）。"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "assets/DaoDeJing/image_catalog.json"

DEPRIORITIZE_PREFIX = ("Flat ", "Template ", "Pure ")

# 同一图在 chN 出现后，chN+1…chN+3 禁用；chN+4 起可用（例：ch01 → ch05）
DEFAULT_CHAPTER_COOLDOWN = 3

SCENE_SECTION = {
    "intro-bridge": "intro",
    "open-1": "open",
    "s1": "core",
    "s2": "core",
    "s3": "core",
    "s4": "core",
    "s5": "core",
    "open-ext1": "east_west",
    "open-ext2": "modern",
    "s-ext2": "modern",
    "open-close": "closing",
}

SCENE_HINTS: dict[str, list[str]] = {
    "intro-bridge": ["道", "玄", "总纲", "承上", "雾", "山", "卷轴", "门", "始", "章"],
    "open-1": ["破译", "逐段", "解读", "黑盒", "直译"],
    "open-ext1": ["柏拉图", "西方", "东方", "互证", "儒", "释", "亚里士", "康德", "希腊"],
    "open-ext2": ["公司", "今天", "现代", "教育", "个人", "职场", "城市", "手机"],
    "s-ext2": ["练习", "本周", "个人", "习惯", "一件"],
    "open-close": ["补丁", "收束", "下一章", "四条", "预告"],
}

# 英文文件名 → 中文语义（plc_/wat_/ep 系列）
EN_GLOSS: dict[str, str] = {
    "cooking": "烹", "fish": "鲜", "tripod": "鼎", "fire": "火", "charcoal": "炭",
    "water": "水", "ocean": "海", "river": "江", "valley": "谷", "wave": "波",
    "snow": "雪", "ice": "冰", "rain": "雨", "mist": "雾", "cloud": "云",
    "jade": "玉", "stone": "石", "wood": "木", "iron": "铁", "gold": "金",
    "mother": "母", "horse": "马", "deer": "鹿", "war": "战", "weapon": "兵",
    "banner": "旗", "mud": "泥", "blood": "血", "sage": "圣人", "throne": "王",
    "governance": "治国", "courtyard": "庭", "wall": "墙", "gate": "门",
    "mirror": "镜", "well": "井", "rope": "绳", "silk": "丝", "thread": "丝",
    "step": "足", "path": "行", "journey": "千里", "protective": "慈", "support": "下",
    "hands": "手", "torn": "哀", "banner": "旗", "hidden": "藏", "hemp": "褐",
    "convergence": "归", "basin": "渊", "drop": "滴", "leaf": "叶", "reef": "石",
    "bowing": "拜", "official": "官", "shadow": "鬼", "midnight": "夜",
    "meticulous": "细", "seal": "印", "empty": "虚", "moongate": "门",
}

# 文件名 → 中文语义补义（plc/wat 系列 + 各章标签图）
FILENAME_HINTS: dict[str, str] = {
    # plc 宫廷/治国系列
    "plc_01_towering_walls": "高墙 壁垒 组织 大公司 制度 围墙 大国",
    "plc_02_pillar_corridor": "廊柱 宫廷 秩序 器物 尊行",
    "plc_03_weapon_rack": "兵器 止戈 武器 兵 不武 慈 用兵",
    "plc_04_midnight_courtyard": "夜 庭 静 道莅 余温 关系 小火",
    "plc_05_cooking_fish_tripod": "烹小鲜 烹 鱼 治国 鼎 少翻动 火候",
    "plc_06_stone_base_silk": "被褐 麻布 粗布 丝 玉 怀玉 卑微 褐",
    "plc_07_mirror_basin": "镜 水 渊 虚 谷 谦下  basin",
    "plc_08_meticulous_governance": "治国 治理 精细 大国 政策",
    "plc_09_imperial_seal": "拱璧 印 礼仪 宝 权力 坐进 驷马",
    "plc_10_empty_dragon_robe": "奥 深藏 空 龙袍 万物之奥 隐秘 不善",
    "plc_11_broken_beads": "改错 保 珠子 浪子 接纳 何弃",
    "plc_12_discarded_tablets": "弃 碑 失误 人才 坐进 复盘",
    "plc_13_rain_drainage_beast": "雨 排水 易 难 图难 无为",
    "plc_14_moongate_garden": "月门 园 道莅 鬼 神 不肖 大",
    "plc_15_empty_throne_dust": "空 王座 尘 德交 守 侯王",
    "plc_16_snowy_dougong": "雪 斗拱 建筑 难 慎终 始",
    "plc_17_snowy_sacrificial_altar": "祭坛 雪 慎终 始 难 易",
    "plc_18_astronomical_instrument": "仪器 观天 稽式 玄德 智",
    "plc_19_forbidden_city_dawn": "黎明 宫城 大顺 治国 道",
    "plc_20_feather_on_balustrade": "羽 轻 愚 朴 减巧 栏杆",
    # wat 水系列
    "wat_01_deep_low_pool": "愚 深 低 池 质朴 返朴 明民",
    "wat_02_thawing_river": "智多 解冻 河 变化 难治",
    "wat_03_seeping_drop_rock": "滴 渗 石 难 易 毫末 九层",
    "wat_04_river_convergence": "江海 百谷 归 下 汇流 德交 百川",
    "wat_05_melting_lake_ice": "冰 化 僵硬 智 融 损",
    "wat_06_leaf_in_vortex": "叶 涡 不争 柔弱 谷 虚",
    "wat_07_underwater_light_beam": "水下 深渊 谷 低 百谷 光",
    "wat_08_waterfall_abyss": "瀑 深渊 虚 谷 下 不争",
    "wat_09_still_mirror_bowl": "静 镜 水 止水 渊 慎终",
    "wat_10_rain_hitting_reef": "雨 石 柔 刚 撞击 两不相伤",
    "wat_11_catching_drops": "滴水 柔弱 水 善下 江海",
    "wat_12_stirring_murky_water": "浊 搅 烹 翻锅 少动 智多",
    "wat_13_river_finding_path": "千里 行 路 足下 径流 始于",
    "wat_14_tidal_sand_ripples": "海 潮 下 沙 不争 百谷",
    "wat_15_ocean_rain_pillar": "海 雨 大 下 江海 百川 大国",
    # ch60–70 标签图
    "炭火 - ch60": "烹小鲜 火 治国 火候 少翻动 小火",
    "大国者下流 - ch61": "大国 下流 海 百川 处下 牝 王",
    "母马 - ch61": "牝 天下之牝 雌 柔顺 马 大国 下",
    "母鹿 - ch61": "牝 柔顺 鹿 处下 动物 牝",
    "道者万物之奥 - ch62": "奥 万物 宝 不善 拱璧 坐进 道 深",
    "报怨以德 - ch63": "报怨 德 清洗 化解 矛 无为 味无味",
    "一根极细、看似柔弱的丝线 - ch63": "细丝 易 难 柔弱 图难 无为",
    "井水 - ch63": "井水 深 静 无为 无味 事无事",
    "黑暗中 - ch63": "黑暗 奥 隐 深 保存 不善",
    "千里之行 - ch64": "千里 行 足下 始于 难 易 慎终",
    "挑夫 - ch64": "挑夫 负重 行 足下 起步 千里",
    "松子 - ch64": "松子 毫末 九层 台 难 易 图难",
    "薄冰上刚落下一片枯叶 - ch64": "薄冰 叶 轻 难 易 慎终 始",
    "油灯微光下 - ch65": "油灯 微光 愚 智者 暗 明民 玄德 大顺",
    "江海所以能为百谷王者 - ch66": "江海 百谷 王 谷 下 不争 虚",
    "慈 - ch67": "慈 三宝 勇 卫 保护 天将救",
    "粗食 - ch67": "俭 粗食 三宝 少欲 广 舍俭",
    "门槛 - ch67": "门槛 后 不敢先 不肖 细 舍后",
    "善用人者为之下 - ch68": "用人 之下 托举 承载 不争 为客",
    "剑柄 - ch69": "剑 兵 武器 执无兵 用兵 客",
    "哀兵必胜 - ch69": "哀 兵 胜 战旗 悲 抗兵",
    "泥泞中 - ch69": "泥泞 战场 哀 旗 退 轻敌",
    "被褐怀玉 - ch70": "被褐 怀玉 粗布 玉 知不知 希 大巧若拙",
    # 其它常用
    "ch61_01_ocean_convergence": "大国 下流 海 归 百川",
    "ch66_01_the_great_valley": "江海 百谷 谷 下 王",
    "ch46_03_ancient_horse": "驷马 拱璧 马 礼仪 献礼",
    "ep02_49_bowing_official_shadow": "官 拜 影子 鬼 神 伤人 KPI",
    "hemp screen - ch02": "褐 麻 粗布 被褐 布 丝",
    "empty throne - ch02": "空 王座 贵 道 坐进 拱璧",
    "court officials - ch02": "官 善 不善 保 人 何弃",
    "大巧若拙 - ch45": "大巧 若拙 被褐 怀玉 知 行",
    "天下莫柔弱于水 - ch78": "水 柔弱 江海 善下 不争",
    "鱼不可脱于渊 - ch36": "鱼 渊 海 处下 牝 王",
    "油灯 - ch58": "油灯 微光 愚 暗 明 玄德",
    # ch71–81 标签图
    "巨网 - ch73": "网 天网 恢恢 疏而不失 勇 敢 杀",
    "极其寂静的古代军帐内 - ch73": "军帐 静 勇 敢 活 杀 天网",
    "勇于不敢则活 - ch73": "勇 敢 活 杀 天网 不争",
    "雨丝 - ch73": "雨 天 网 柔 细 不争",
    "代大匠斫者伤手 - ch74": "大匠 斫 伤手 代 越 权 民",
    "民之饥 - ch75": "饥 民 上食 税 多 难治",
    "木强则折 - ch76": "木强 折 强 死 徒 弱 生",
    "天之道 - ch77": "天之道 损有余 补不足 天 道",
    "天威不可测 - ch77": "天威 不可测 天 道 损 补",
    "粮食 - ch77": "粮食 天 损 补 民 足",
    "高山之巅 - ch77": "高山 天 威 损 补 处高",
    "和大怨 - ch79": "大怨 和 契 约 德 怨",
    "契约 - ch79": "契约 和 怨 信 约 德",
    "浓白晨雾笼罩的孤绝小村 - ch80": "晨雾 小村 邻 国 小 寡 民",
    "夜色绝壁上的茅草屋 - ch80": "茅草屋 夜 邻 小国 寡 民 朴",
    "栈道风雪 - 通用": "栈道 风雪 信 言 美 辩 善",
    # ch40–50 标签图
    "反者道之动 - ch40": "反 道 动 周期 返回 相反",
    "弱者道之用 - ch40": "弱 道 用 柔 水 穿石",
    "天下万物生于有 - ch40": "有 无 生 万物 反者 弱者",
    "有生于无 - ch40": "无 有 生 万物 空",
    "大雪 - ch41": "上士 闻道 勤行 雪 雾",
    "大雾弥漫的湖面 - ch41": "雾 湖 希声 大音 建言",
    "一座如刀锋般的巨大山峰 - ch42": "道生 一 万物 负 阳 冲气",
    "清晨幽谷中 - ch42": "谷 生 万物 冲气 和",
    "刺绣 - ch44": "名 身 货 得 知足 知止",
    "大巧若拙 - ch45": "大巧 若拙 大辩 若讷 清静",
    "大直若屈 - ch45": "大直 若屈 大成 若缺 大盈 若冲",
    "却走马以粪 - ch46": "走马 以粪 戎马 郊 知足 有道",
    "知足之足 - ch46": "知足 之足 不知足 欲得",
    "不出户 - ch47": "不出户 知天下 不窥牖 见天道",
    "窥牖见天道 - ch47": "窥牖 天道 弥远 弥少 不行而知",
    "为道日损 - ch48": "为道 日损 为学 日益 损之又损 无为",
    "损之又损 - ch48": "损 无为 无不为 取天下 无事",
    "百姓心 - ch49": "百姓 心 圣人 无心 德善 德信",
    "众生行 - ch49": "众生 百姓 心 亦善 亦信",
    "出生入死 - ch50": "出生 入死 十有三 摄生 死地",
    "生之徒 - ch50": "生 之徒 死 之徒 十有三",
    "摄生 - ch50": "摄生 生生 之厚 无死地 善",
    "老虎 - ch50": "虎 爪 角 兕 无 投 死地",
    "避险之路 - ch50": "避险 路 善摄生 无死地 生",
}


def _tokens(text: str) -> set[str]:
    text = text.strip().lower()
    if not text:
        return set()
    out: set[str] = set()
    for p in re.split(r"[\s,，、；;：:]+", text):
        p = p.strip()
        if len(p) >= 2:
            out.add(p)
    for m in re.finditer(r"[\u4e00-\u9fff]{2,6}", text):
        out.add(m.group())
    return out


def chapter_tags_in_name(name: str) -> set[int]:
    tags: set[int] = set()
    m = re.match(r"ch(\d+)_", name, re.I)
    if m:
        tags.add(int(m.group(1)))
    for m in re.finditer(r" - [Cc]h(\d+)(?:\s|\(|\.|$|-)", name):
        tags.add(int(m.group(1)))
    return tags


def is_deprioritized(rel: str) -> bool:
    return Path(rel).name.startswith(DEPRIORITIZE_PREFIX)


def load_image_records(library: list[str]) -> list[dict]:
    by_file: dict[str, dict] = {}
    if CATALOG.is_file():
        raw = json.loads(CATALOG.read_text(encoding="utf-8"))
        images = raw if isinstance(raw, list) else raw.get("images", [])
        for img in images:
            f = img.get("file", "")
            if f:
                by_file[f] = dict(img)

    records: list[dict] = []
    for rel in library:
        rec = dict(by_file.get(rel, {}))
        rec.setdefault("file", rel)
        rec.setdefault("filename", Path(rel).name)
        rec.setdefault("id", Path(rel).stem)
        rec["_tokens"] = _image_tokens(rec)
        rec["_chapter_tags"] = chapter_tags_in_name(Path(rel).name)
        records.append(rec)
    return records


def filename_zh_label(rel: str) -> str:
    stem = Path(rel).stem
    m = re.match(r"^(.+?)\s*-\s*Ch", stem)
    if m:
        return m.group(1).strip()
    if re.search(r"[\u4e00-\u9fff]", stem):
        return stem
    return ""


def _filename_derived_tokens(rel: str) -> set[str]:
    stem = Path(rel).stem
    tokens: set[str] = set()

    zh = filename_zh_label(rel)
    if zh:
        tokens |= _tokens(zh)

    hint = FILENAME_HINTS.get(stem.lower(), "")
    if not hint:
        for key, val in FILENAME_HINTS.items():
            if key in stem.lower():
                hint = val
                break
    if hint:
        tokens |= _tokens(hint)

    for part in re.split(r"[_\-\s]+", stem):
        pl = part.lower()
        if not pl.isascii() or len(pl) < 3:
            continue
        tokens.add(pl)
        if pl in EN_GLOSS:
            tokens |= _tokens(EN_GLOSS[pl])

    return tokens


def _image_tokens(img: dict) -> set[str]:
    rel = img.get("file", "")
    filename = Path(img.get("filename") or rel).stem
    chunks = [
        img.get("description_zh", ""),
        img.get("description", ""),
        " ".join(img.get("tags", [])),
        " ".join(img.get("themes", [])),
        " ".join(img.get("match_keywords", [])),
        str(img.get("id", "")),
        filename.replace("_", " "),
        filename.replace(" - ", " "),
    ]
    tokens: set[str] = set()
    for c in chunks:
        tokens |= _tokens(str(c))
    tokens |= _filename_derived_tokens(rel)
    return tokens


def _semantic_overlap(narration: str, img: dict, scene_id: str) -> tuple[float, list[str]]:
    narr = narration
    narr_tokens = _tokens(narration) | _tokens(" ".join(SCENE_HINTS.get(scene_id, [])))
    img_tokens = img["_tokens"]
    matched: list[str] = []

    for t in narr_tokens:
        if len(t) < 2:
            continue
        if t in img_tokens or any(t in it for it in img_tokens):
            matched.append(t)

    # 旁白整句含图义（如「与被褐怀玉」切词后丢失子串）
    for it in img_tokens:
        if len(it) < 2 or not re.search(r"[\u4e00-\u9fff]", it):
            continue
        if it in narr and it not in matched:
            matched.append(it)

    bonus = 0.0
    zh = filename_zh_label(img["file"])
    if zh and len(zh) >= 2:
        if zh in narr:
            matched.append(f"「{zh[:12]}」")
            bonus += 16.0
        else:
            for n in (4, 3):
                for i in range(max(0, len(zh) - n + 1)):
                    sub = zh[i : i + n]
                    if sub in narr:
                        matched.append(sub)
                        bonus += 6.0
                        break
                if bonus >= 6.0:
                    break

    stem_l = Path(img["file"]).stem.lower()
    for en, zh_word in EN_GLOSS.items():
        if en in stem_l and zh_word in narr:
            matched.append(zh_word)
            bonus += 5.0

    score = len(set(matched)) * 2.0 + bonus
    return score, sorted(set(matched), key=len, reverse=True)[:8]


def cooldown_ok(
    rel: str,
    ch: int,
    used_chapters: dict[str, list[int]],
    *,
    cooldown: int = DEFAULT_CHAPTER_COOLDOWN,
) -> bool:
    for prev in used_chapters.get(rel, []):
        if abs(ch - prev) <= cooldown:
            return False
    return True


def score_scene_image(
    *,
    scene_id: str,
    narration: str,
    img: dict,
    chapter: int,
    usage: Counter[str],
    used_chapters: dict[str, list[int]],
    chapter_seen: set[str],
    max_reuse: int,
    chapter_cooldown: int,
) -> float:
    rel = img["file"]
    tags = img.get("_chapter_tags", set())
    # 预告镜禁止占用下一章标签主图（如 ch62 片尾抢 ch63 报怨以德）
    if scene_id == "open-close" and (chapter + 1) in tags:
        return -1e9

    if rel in chapter_seen:
        return -1e9
    # ch01 标签图仅用于第一章（磁盘上大量 ch01 通用图会污染后续章节）
    if 1 in tags and chapter != 1:
        return -1e9
    if usage[rel] >= max_reuse:
        return -1e9
    if not cooldown_ok(rel, chapter, used_chapters, cooldown=chapter_cooldown):
        zh = filename_zh_label(rel)
        tags = img.get("_chapter_tags", set())
        # 下章预告占用的「本章主图」：回到所属章 intro/s1 时允许复用
        if not (chapter in tags and zh and zh in narration):
            return -1e9

    overlap, _ = _semantic_overlap(narration, img, scene_id)

    section = SCENE_SECTION.get(scene_id, "")
    section_bonus = 4.0 if section and section in set(img.get("themes", [])) else 0.0
    chapter_bonus = 0.0
    if chapter in tags:
        chapter_bonus = 8.0
        zh = filename_zh_label(rel)
        if zh and zh in narration:
            chapter_bonus += 12.0

    future_penalty = 0.0
    for t in tags:
        if t > chapter:
            future_penalty += 18.0

    deprioritize_penalty = 6.0 if is_deprioritized(rel) else 0.0
    usage_penalty = usage[rel] * 2.0

    return (
        overlap
        + section_bonus
        + chapter_bonus
        - future_penalty
        - deprioritize_penalty
        - usage_penalty
    )


def semantic_only_score(scene_id: str, narration: str, img: dict, chapter: int) -> float:
    """仅语义相关度（审查用，不含冷却/用量惩罚）。"""
    overlap, _ = _semantic_overlap(narration, img, scene_id)
    section = SCENE_SECTION.get(scene_id, "")
    section_bonus = 4.0 if section and section in set(img.get("themes", [])) else 0.0
    chapter_bonus = 3.0 if chapter in img.get("_chapter_tags", set()) else 0.0
    deprioritize_penalty = 6.0 if is_deprioritized(img["file"]) else 0.0
    return overlap + section_bonus + chapter_bonus - deprioritize_penalty


def pick_chapter_images_semantic(
    ch: int,
    scenes: list[tuple[str, str]],
    records: list[dict],
    *,
    usage: Counter[str],
    used_chapters: dict[str, list[int]],
    max_reuse: int = 3,
    chapter_cooldown: int = DEFAULT_CHAPTER_COOLDOWN,
) -> list[tuple[str, float, list[str]]]:
    """按镜语义贪心选配；返回 [(file, score, matched_tokens), ...]。"""
    chapter_seen: set[str] = set()
    out: list[tuple[str, float, list[str]]] = []

    for scene_id, narration in scenes:
        best_rel = ""
        best_score = -1e18
        best_matched: list[str] = []

        for img in records:
            sc = score_scene_image(
                scene_id=scene_id,
                narration=narration,
                img=img,
                chapter=ch,
                usage=usage,
                used_chapters=used_chapters,
                chapter_seen=chapter_seen,
                max_reuse=max_reuse,
                chapter_cooldown=chapter_cooldown,
            )
            if sc > best_score:
                rel = img["file"]
                _, matched = _semantic_overlap(narration, img, scene_id)
                best_score = sc
                best_rel = rel
                best_matched = matched[:6]

        if not best_rel:
            raise RuntimeError(f"ch{ch:02d} {scene_id}: 无可用配图")

        chapter_seen.add(best_rel)
        usage[best_rel] += 1
        used_chapters.setdefault(best_rel, []).append(ch)
        out.append((best_rel, best_score, best_matched))

    return out


def load_usage_state(*, exclude_chapters: set[int]) -> tuple[Counter[str], dict[str, list[int]]]:
    """从分镜读取已分配状态（用于只重配部分章节时保留冷却/用量）。"""
    usage: Counter[str] = Counter()
    used_chapters: dict[str, list[int]] = {}
    for ch in range(1, 82):
        if ch in exclude_chapters:
            continue
        path = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for s in data.get("scenes", []):
            img = s.get("image", "")
            if not img or "avatar" in img:
                continue
            usage[img] += 1
            used_chapters.setdefault(img, []).append(ch)
    return usage, used_chapters


def analyze_assignments(
    chapters: list[int],
    *,
    chapter_cooldown: int = DEFAULT_CHAPTER_COOLDOWN,
) -> dict:
    usage = Counter()
    used_at: dict[str, list[int]] = {}
    adjacent = 0
    cooldown_violations = 0
    prev: set[str] = set()

    for ch in chapters:
        path = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        imgs = [s.get("image", "") for s in data.get("scenes", []) if s.get("image")]
        usage.update(imgs)
        adjacent += len(set(imgs) & prev)
        for img in imgs:
            for prev_ch in used_at.get(img, []):
                if abs(ch - prev_ch) <= chapter_cooldown:
                    cooldown_violations += 1
            used_at.setdefault(img, []).append(ch)
        prev = set(imgs)

    return {
        "unique": len(usage),
        "max_reuse": max(usage.values()) if usage else 0,
        "adjacent_overlap": adjacent,
        "cooldown_violations": cooldown_violations,
        "top": usage.most_common(8),
    }
