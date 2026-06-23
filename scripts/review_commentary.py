#!/usr/bin/env python3
"""观念黑盒 hybrid 讲解稿自动评审（规则 + 评分 + 修改建议）。

用法:
  python3 scripts/review_commentary.py examples/storyboard-daodejing-ch36-commentary.json
  python3 scripts/review_commentary.py --chapters 31-40
  python3 scripts/review_commentary.py --chapters 1-10 --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAOTECHING = ROOT / "assets/DaoDeJing/taoteching_full.json"

REQUIRED_SCENES = [
    "intro-bridge",
    "open-1",
    "s1",
    "s2",
    "s3",
    "s4",
    "s5",
    "open-ext1",
    "open-ext2",
    "s-ext2",
    "open-close",
]

# 机械垫字 / 元指令（出现即扣分，全章重复则严重扣分）
BOILERPLATE_PATTERNS: list[tuple[str, str, int]] = [
    (r"请对照本周一个真实决策写下来", "homework_tail", 8),
    (r"观念黑盒系列到此处", "series_meta", 5),
    (r"建议分两次听完", "listen_meta", 4),
    (r"可暂停三十秒", "pause_meta", 4),
    (r"写下来，比「听懂了」重要十倍", "slogan_repeat", 5),
    (r"硬扛短期有效，长期几乎总是失本或失君", "wrong_ch26_quote", 6),
    (r"东西方互证不是堆名字", "ext1_boilerplate", 3),
    (r"若三脉同向，你几乎可以把它当「底层常量」", "ext1_boilerplate", 3),
    (r"现代例子尽量具体，是为了让「道」变成可执行的下一步", "ext2_boilerplate", 3),
    (r"执行不了，说明例子还不够贴你的皮肤", "ext2_boilerplate", 3),
    (r"若你带团队，可把本条变成复盘会", "sext2_boilerplate", 3),
    (r"个人则写成日记题", "sext2_boilerplate", 3),
    (r"四条补丁不必一次全做", "close_boilerplate", 3),
    (r"七分钟内容，值得你用七天消化", "close_boilerplate", 3),
    (r"对照生活，别停在概念层", "generic_pad", 4),
    (r"全章落点，建议你用一句话写给未来的自己", "s5_wrong_close", 5),
]

# 仅应在特定镜出现的套话
SCENE_SPECIFIC: dict[str, list[str]] = {
    "open-ext1": ["回到今天", "互证", "西方", "东方"],
    "open-ext2": ["回到今天"],
    "open-close": ["四条认知补丁", "下一章"],
}

PASS_SCORE = 72


def _cn_num(n: int) -> str:
    ones = "零一二三四五六七八九"
    if n <= 0:
        return str(n)
    if n < 10:
        return ones[n]
    if n < 20:
        return "十" + (ones[n % 10] if n % 10 else "")
    if n < 100:
        tens, o = divmod(n, 10)
        return ones[tens] + "十" + (ones[o] if o else "")
    return str(n)


def _prev_chapter_mentioned(intro: str, prev_ch: int) -> bool:
    label = f"第{_cn_num(prev_ch)}章"
    return label in intro


@dataclass
class Issue:
    severity: str  # error | warn | info
    code: str
    scene: str
    message: str
    deduction: int = 0


@dataclass
class ReviewResult:
    path: str
    chapter: int | None
    title: str
    score: int
    passed: bool
    total_chars: int
    issues: list[Issue] = field(default_factory=list)

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)


def _cn_bigrams(text: str) -> set[str]:
    s = re.sub(r"[^\u4e00-\u9fff]", "", text)
    return {s[i : i + 2] for i in range(len(s) - 1)}


def _has_echo_tail(text: str) -> bool:
    """镜内「正文 + 空格 + 同义收束」——ch31+ 机械加长常见听感问题。"""
    m = re.match(r"^(.+[。！？])\s+(.+)$", text.strip())
    if not m:
        return False
    body, tail = m.group(1), m.group(2).strip()
    if len(tail) < 8 or len(tail) > 55:
        return False
    tail_bi = _cn_bigrams(tail)
    if len(tail_bi) < 3:
        return False
    body_bi = _cn_bigrams(body)
    overlap = len(body_bi & tail_bi) / len(tail_bi)
    return overlap >= 0.38


def _chapter_num_from_path(path: Path) -> int | None:
    m = re.search(r"ch(\d+)-commentary", path.name)
    return int(m.group(1)) if m else None


def load_chapter_text(ch: int) -> str:
    data = json.loads(TAOTECHING.read_text(encoding="utf-8"))
    raw = data.get(str(ch), "")
    return raw.replace("\n", "")


def review_storyboard(path: Path) -> ReviewResult:
    sb = json.loads(path.read_text(encoding="utf-8"))
    ch = _chapter_num_from_path(path)
    return _review_storyboard(sb, path_label=str(path.relative_to(ROOT)), chapter=ch)


def review_storyboard_data(
    sb: dict,
    *,
    chapter: int | None = None,
    path_label: str = "storyboard.json",
) -> ReviewResult:
    return _review_storyboard(sb, path_label=path_label, chapter=chapter)


def _review_storyboard(
    sb: dict,
    *,
    path_label: str,
    chapter: int | None,
) -> ReviewResult:
    result = ReviewResult(
        path=path_label,
        chapter=chapter,
        title=sb.get("title", ""),
        score=100,
        passed=False,
        total_chars=0,
    )

    scenes = {s["id"]: s for s in sb.get("scenes", [])}
    narrations = {sid: (scenes[sid].get("narration") or "").strip() for sid in scenes}

    # 结构
    for sid in REQUIRED_SCENES:
        if sid not in scenes:
            result.add(
                Issue("error", "missing_scene", sid, f"缺少标准镜位 {sid}", 15)
            )

    result.total_chars = sum(len(t) for t in narrations.values())

    if result.total_chars < 900:
        result.add(
            Issue(
                "warn",
                "too_short",
                "*",
                f"讲解总字数 {result.total_chars}，可能不足 5 分钟",
                10,
            )
        )
    elif result.total_chars > 2200:
        result.add(
            Issue(
                "warn",
                "too_long",
                "*",
                f"讲解总字数 {result.total_chars}，口播可能冗长",
                5,
            )
        )

    # 承上启下
    intro = narrations.get("intro-bridge", "")
    if chapter and chapter > 1:
        prev_lines = load_chapter_text(chapter - 1)
        prev_keywords = prev_lines[:12] if prev_lines else ""
        intro_ok = (
            f"第{chapter - 1}章" in intro
            or f"ch{chapter - 1:02d}" in intro.lower()
            or (prev_keywords and prev_keywords in intro)
            or _prev_chapter_mentioned(intro, chapter - 1)
        )
        if not intro_ok:
            result.add(
                Issue(
                    "warn",
                    "weak_bridge",
                    "intro-bridge",
                    f"intro 未明显承接上一章 ch{chapter-1:02d} 主题",
                    5,
                )
            )

    close = narrations.get("open-close", "")
    if "四条认知补丁" not in close and "四条" not in close:
        result.add(
            Issue("warn", "weak_close", "open-close", "收束缺少「四条认知补丁」结构", 5)
        )
    if chapter and chapter < 81 and "下一章" not in close:
        result.add(
            Issue("info", "no_next_tease", "open-close", "未预告下一章", 2)
        )

    # 原文覆盖（至少 2 条关键短语出现在破译段）
    if chapter:
        source = load_chapter_text(chapter)
        data = json.loads(TAOTECHING.read_text(encoding="utf-8"))
        source_lines = [
            ln.strip()
            for ln in data.get(str(chapter), "").split("\n")
            if len(ln.strip()) >= 3
        ][:10]
        body = " ".join(narrations.get(s, "") for s in ("s1", "s2", "s3", "s4", "s5"))
        hits = sum(
            1
            for ln in source_lines
            if ln[: min(6, len(ln))] in body or ln in body
        )
        if hits < 2 and source_lines:
            result.add(
                Issue(
                    "warn",
                    "low_source_coverage",
                    "s1-s5",
                    f"破译段与原文重合偏低（约 {hits}/{len(source_lines)} 条），易像泛泛而谈",
                    8,
                )
            )

    # 垫字 / 重复
    all_text = "\n".join(narrations.values())
    for pattern, code, ded in BOILERPLATE_PATTERNS:
        matches = re.findall(pattern, all_text)
        if not matches:
            continue
        count = len(matches)
        per_scene_avg = count / max(len(narrations), 1)
        if count >= 3 or per_scene_avg >= 0.5:
            sev = "error" if count >= 8 else "warn"
            result.add(
                Issue(
                    sev,
                    code,
                    "*",
                    f"套话「{pattern[:20]}…」出现 {count} 次（像机械垫字）",
                    min(ded * count, 25),
                )
            )

    # ch26 专用语误用
    if chapter != 26:
        for sid, text in narrations.items():
            if "失本或失君" in text or "失本" in text and "失君" in text:
                result.add(
                    Issue(
                        "error",
                        "wrong_ch26_quote",
                        sid,
                        "非第26章却出现「失本/失君」（ch26 专用语）",
                        6,
                    )
                )

    # 英文字母（除 MBTI 等白名单）
    for sid, text in narrations.items():
        if re.search(r"\b[A-Za-z]{3,}\b", text):
            if not re.search(r"MBTI|ENTJ|FOMO|SOP|KPI", text):
                result.add(
                    Issue("warn", "english_fragment", sid, "含英文片段，口播需确认", 3)
                )

    # 单镜过长（字幕 max_lines=1 约 40–55 字）
    for sid, text in narrations.items():
        if sid == "ending":
            continue
        # 按句号分，看最长一句
        sentences = re.split(r"[。！？]", text)
        long_sents = [s for s in sentences if len(s.strip()) > 58]
        if long_sents:
            result.add(
                Issue(
                    "warn",
                    "subtitle_too_long",
                    sid,
                    f"有 {len(long_sents)} 句超过 ~58 字，单屏字幕可能换行失败",
                    4,
                )
            )

    # s5 不应重复 open-close 功能
    s5 = narrations.get("s5", "")
    if "全章落点" in s5 and "四条" in s5:
        result.add(
            Issue("warn", "duplicate_close", "s5", "s5 与 open-close 功能重叠", 4)
        )

    # open-1 应短
    open1 = narrations.get("open-1", "")
    if len(open1) > 80:
        result.add(
            Issue("info", "open1_long", "open-1", "open-1 宜一句过渡，当前偏长", 2)
        )

    # 镜内同义收束（正文后空格再接摘要复读）
    for sid, text in narrations.items():
        if _has_echo_tail(text):
            result.add(
                Issue(
                    "warn",
                    "echo_tail",
                    sid,
                    "镜内疑似「正文 + 同义收束」复读，听感像凑时长",
                    10,
                )
            )

    # 镜内重复（同一句子片段出现两次）
    for sid, text in narrations.items():
        if len(text) < 40:
            continue
        half = len(text) // 2
        chunk = text[half - 15 : half + 15]
        if chunk and text.count(chunk) > 1:
            result.add(
                Issue("info", "intra_repeat", sid, "镜内疑似重复片段", 2)
            )

    total_deduction = sum(i.deduction for i in result.issues)
    result.score = max(0, 100 - total_deduction)
    result.passed = result.score >= PASS_SCORE and not any(
        i.severity == "error" for i in result.issues
    )
    return result


def format_report(r: ReviewResult) -> str:
    lines = [
        f"{'✅ PASS' if r.passed else '❌ FAIL'}  {r.path}  评分 {r.score}/100  ({r.total_chars} 字)",
        f"   {r.title}",
        "",
    ]
    if not r.issues:
        lines.append("   未发现明显问题。")
        return "\n".join(lines)

    for sev in ("error", "warn", "info"):
        group = [i for i in r.issues if i.severity == sev]
        if not group:
            continue
        label = {"error": "错误", "warn": "警告", "info": "提示"}[sev]
        lines.append(f"   [{label}]")
        for i in group:
            loc = i.scene if i.scene != "*" else "全章"
            lines.append(f"     · [{i.code}] {loc}: {i.message}")
    lines.append("")
    lines.append(f"   及格线: {PASS_SCORE} 分，且无 error。")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("storyboard", nargs="*", type=Path)
    parser.add_argument("--chapters", default=None, help="如 31-40 或 1,5,36")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-under", type=int, default=PASS_SCORE)
    args = parser.parse_args()

    paths: list[Path] = []
    if args.chapters:
        spec = args.chapters.strip()
        if "-" in spec:
            a, b = spec.split("-", 1)
            chapters = range(int(a), int(b) + 1)
        else:
            chapters = [int(x) for x in spec.split(",")]
        for ch in chapters:
            p = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
            if p.is_file():
                paths.append(p)
    paths.extend(args.storyboard)

    if not paths:
        parser.error("请指定 storyboard 文件或 --chapters")

    results = [review_storyboard(p.resolve()) for p in paths]

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "path": r.path,
                        "chapter": r.chapter,
                        "score": r.score,
                        "passed": r.passed,
                        "total_chars": r.total_chars,
                        "issues": [
                            {
                                "severity": i.severity,
                                "code": i.code,
                                "scene": i.scene,
                                "message": i.message,
                            }
                            for i in r.issues
                        ],
                    }
                    for r in results
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for r in results:
            print(format_report(r))

    failed = [r for r in results if r.score < args.fail_under or not r.passed]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
