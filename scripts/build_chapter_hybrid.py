#!/usr/bin/env python3
"""混合版单章精解：朗读段（章节水墨动画）+ 讲解段（pipeline 静图分镜）。

第 1 章示例：
  python3 scripts/build_chapter_hybrid.py --chapter 1

流程：
  1. 原文慢速 TTS + Chapter_N 水墨动画 → read 段
  2. pipeline 渲染 storyboard 讲解段（静图 + 逐句字幕 + BGM + 片尾）
  3. FFmpeg 拼接 → 成片

数据：
  assets/DaoDeJing/daodejing_81_commentary.json  （mode: hybrid + storyboard 路径）
  assets/DaoDeJing/taoteching_full.json
  examples/storyboard-daodejing-chNN-commentary.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.bgm import mix_bgm_into_video  # noqa: E402
from pipeline.env_util import load_dotenv  # noqa: E402
from pipeline.ffmpeg_util import probe_duration_sec, require_ffmpeg  # noqa: E402
from pipeline.models import BgmConfig, RenderedScene, Scene, Storyboard, TtsConfig  # noqa: E402
from pipeline.render import _concat_videos, render_storyboard  # noqa: E402
from pipeline.tts import generate_scene_audio  # noqa: E402

import importlib.util

_b81_spec = importlib.util.spec_from_file_location(
    "build_daodejing_81_full",
    ROOT / "scripts" / "build_daodejing_81_full.py",
)
_b81 = importlib.util.module_from_spec(_b81_spec)
assert _b81_spec.loader
_b81_spec.loader.exec_module(_b81)

list_chapter_videos = _b81.list_chapter_videos
load_chapter_texts = _b81.load_chapter_texts
mux_chapter_segment = _b81.mux_chapter_segment
build_rendered_scenes = _b81.build_rendered_scenes


def build_hybrid_bgm_scenes(
    *,
    read_id: str,
    read_duration: float,
    storyboard: Storyboard,
    comm_work: Path,
) -> list[RenderedScene]:
    """全片 BGM 时间轴：朗读段 + 讲解各镜。"""
    scenes: list[RenderedScene] = []
    if read_duration > 0:
        scenes.append(
            RenderedScene(
                scene=Scene(id=read_id, narration=""),
                audio_path=Path("."),
                audio_duration_sec=read_duration,
            )
        )
    audio_dir = comm_work / "audio"
    for scene in storyboard.all_scenes():
        audio_path = audio_dir / f"{scene.id}.mp3"
        if audio_path.is_file() and audio_path.stat().st_size > 500:
            dur = probe_duration_sec(audio_path)
        elif not scene.narration.strip():
            dur = scene.duration_sec or 3.0
        else:
            continue
        scenes.append(
            RenderedScene(
                scene=scene,
                audio_path=audio_path,
                audio_duration_sec=dur,
            )
        )
    return scenes

COMMENTARY_JSON = ROOT / "assets/DaoDeJing/daodejing_81_commentary.json"
DEFAULT_OUT = ROOT / "output/daodejing-ch01-hybrid.mp4"


def load_chapter_config(chapter: int) -> dict:
    data = json.loads(COMMENTARY_JSON.read_text(encoding="utf-8"))
    raw = (data.get("chapters") or {}).get(str(chapter))
    if not raw:
        raise SystemExit(f"第 {chapter} 章无讲解稿: {COMMENTARY_JSON}")
    if isinstance(raw, str):
        return {"title": f"第{chapter}章", "mode": "classic", "explain": raw.strip()}
    cfg = dict(raw)
    cfg.setdefault("mode", "classic")
    cfg.setdefault("read_rate", "-18%")
    cfg.setdefault(
        "storyboard",
        f"examples/storyboard-daodejing-ch{chapter:02d}-commentary.json",
    )
    return cfg


def read_narration(chapter: int, texts: dict[int, str]) -> str:
    """沉浸朗读：仅原文，句号停顿，不加「第 N 章」前缀。"""
    body = texts[chapter]
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    pairs = {
        1: (
            "道可道，非常道。名可名，非常名。无名，天地之始；有名，万物之母。"
            "故常无欲，以观其妙；常有欲，以观其徼。此两者同出而异名，同谓之玄。"
            "玄之又玄，众妙之门。"
        ),
        2: (
            "天下皆知美之为美，斯恶已。皆知善之为善，斯不善已。"
            "故有无相生，难易相成，长短相较，高下相倾，音声相和，前后相随。"
            "是以圣人处无为之事，行不言之教。万物作焉而不辞，生而不有，为而不恃，功成而弗居。"
            "夫唯弗居，是以不去。"
        ),
        3: (
            "不尚贤，使民不争。不贵难得之货，使民不为盗。不见可欲，使民心不乱。"
            "是以圣人之治，虚其心，实其腹，弱其志，强其骨。"
            "常使民无知无欲，使夫智者不敢为也。为无为，则无不治。"
        ),
        4: (
            "道冲而用之或不盈，渊兮似万物之宗。"
            "挫其锐，解其纷，和其光，同其尘。"
            "湛兮似或存，吾不知谁之子，象帝之先。"
        ),
        5: (
            "天地不仁，以万物为刍狗。圣人不仁，以百姓为刍狗。"
            "天地之间，其犹橐龠乎，虚而不屈，动而愈出。"
            "多言数穷，不如守中。"
        ),
        6: (
            "谷神不死，是谓玄牝。玄牝之门，是谓天地根。"
            "绵绵若存，用之不勤。"
        ),
        7: (
            "天长地久。天地所以能长且久者，以其不自生，故能长生。"
            "是以圣人后其身而身先，外其身而身存。"
            "非以其无私邪？故能成其私。"
        ),
        8: (
            "上善若水。水善利万物而不争，处众人之所恶，故几于道。"
            "居善地，心善渊，与善仁，言善信，正善治，事善能，动善时。"
            "夫唯不争，故无尤。"
        ),
        9: (
            "持而盈之，不如其已。揣而锐之，不可长保。"
            "金玉满堂，莫之能守。富贵而骄，自遗其咎。"
            "功成身退，天之道。"
        ),
        10: (
            "载营魄抱一，能无离乎？专气致柔，能婴儿乎？"
            "涤除玄览，能无疵乎？爱民治国，能无知乎？"
            "天门开阖，能无雌乎？明白四达，能无为乎？"
            "生之，畜之，生而不有，为而不恃，长而不宰，是谓玄德。"
        ),
        11: (
            "三十辐共一毂，当其无，有车之用。"
            "埏埴以为器，当其无，有器之用。"
            "凿户牖以为室，当其无，有室之用。"
            "故有之以为利，无之以为用。"
        ),
        12: (
            "五色令人目盲，五音令人耳聋，五味令人口爽。"
            "驰骋畋猎令人心发狂，难得之货令人行妨。"
            "是以圣人为腹不为目，故去彼取此。"
        ),
        13: (
            "宠辱若惊，贵大患若身。"
            "何谓宠辱若惊？宠为下，得之若惊，失之若惊，是谓宠辱若惊。"
            "何谓贵大患若身？吾所以有大患者，为吾有身，及吾无身，吾有何患？"
            "故贵以身为天下，若可寄天下；爱以身为天下，若可托天下。"
        ),
        14: (
            "视之不见名曰夷，听之不闻名曰希，搏之不得名曰微。"
            "此三者不可致诘，故混而为一。"
            "其上不皦，其下不昧，绳绳不可名，复归于无物。"
            "是谓无状之状，无物之象，是谓惚恍。"
            "迎之不见其首，随之不见其后。"
            "执古之道，以御今之有。能知古始，是谓道纪。"
        ),
        15: (
            "古之善为士者，微妙玄通，深不可识。"
            "夫唯不可识，故强为之容。"
            "豫焉若冬涉川，犹兮若畏四邻，俨兮其若客，涣兮若冰之将释，"
            "敦兮其若朴，旷兮其若谷，混兮其若浊。"
            "孰能浊以静之徐清？孰能安以久动之徐生？"
            "保此道者不欲盈。夫唯不盈，故能蔽不新成。"
        ),
        16: (
            "致虚极，守静笃。万物并作，吾以观复。"
            "夫物芸芸，各复归其根。归根曰静，是谓复命。"
            "复命曰常，知常曰明。不知常，妄作凶。"
            "知常容，容乃公，公乃王，王乃天，天乃道，道乃久，没身不殆。"
        ),
        17: (
            "太上，下知有之。其次，亲而誉之。其次，畏之。其次，侮之。"
            "信不足焉，有不信焉。悠兮其贵言。"
            "功成事遂，百姓皆谓我自然。"
        ),
        18: (
            "大道废，有仁义。慧智出，有大伪。"
            "六亲不和，有孝慈。国家昏乱，有忠臣。"
            "大道既废，乃尚仁义。智慧既出，大伪乃生。"
            "六亲不和，孝慈乃显。国家昏乱，忠臣乃出。"
        ),
        19: (
            "绝圣弃智，民利百倍。绝仁弃义，民复孝慈。绝巧弃利，盗贼无有。"
            "此三者，以为文不足，故令有所属：见素抱朴，少私寡欲。"
            "见素抱朴，少私寡欲。为文不足，故有所属。"
        ),
        20: (
            "绝学无忧。唯之与阿，相去几何？善之与恶，相去若何？"
            "人之所畏，不可不畏。"
            "众人熙熙，如享太牢，如春登台。"
            "我独泊兮其未兆，如婴儿之未孩。傫傫兮若无所归。"
            "众人皆有余，而我独若遗。我愚人之心也哉。"
            "俗人昭昭，我独昏昏。俗人察察，我独闷闷。"
            "澹兮其若海，飂兮若无止。众人皆有以，而我独顽似鄙。"
            "我独异于人，而贵食母。"
        ),
        21: (
            "孔德之容，惟道是从。道之为物，惟恍惟惚。"
            "惚兮恍兮，其中有象；恍兮惚兮，其中有物。"
            "窈兮冥兮，其中有精；其精甚真，其中有信。"
            "自古及今，其名不去，以阅众甫。"
            "吾何以知众甫之状哉？以此。"
        ),
        22: (
            "曲则全，枉则直，洼则盈，敝则新，少则得，多则惑。"
            "是以圣人抱一，为天下式。"
            "不自见故明，不自是故彰，不自伐故有功，不自矜故长。"
            "夫唯不争，故天下莫能与之争。"
            "古之所谓曲则全者，岂虚言哉？诚全而归之。"
        ),
        23: (
            "希言自然。故飘风不终朝，骤雨不终日。"
            "孰为此者？天地。天地尚不能久，而况于人乎？"
            "故从事于道者，同于道；德者，同于德；失者，同于失。"
            "同于道者，道亦乐得之；同于德者，德亦乐得之；同于失者，失亦乐得之。"
            "信不足焉，有不信焉。"
        ),
        24: (
            "企者不立，跨者不行。"
            "自见者不明，自是者不彰，自伐者无功，自矜者不长。"
            "其在道也，曰余食赘行。物或恶之，故有道者不处。"
            "企者不立，跨者不行；自见者不明，自是者不彰。"
            "余食赘行，有道者不处。"
        ),
        25: (
            "有物混成，先天地生。寂兮寥兮，独立不改，周行而不殆，可以为天下母。"
            "吾不知其名，字之曰道，强为之名曰大。"
            "大曰逝，逝曰远，远曰反。"
            "故道大，天大，地大，王亦大。域中有四大，而王居其一焉。"
            "人法地，地法天，天法道，道法自然。"
        ),
        26: (
            "重为轻根，静为躁君。是以圣人终日行不离辎重。"
            "虽有荣观，燕处超然。奈何万乘之主，而以身轻天下？"
            "轻则失本，躁则失君。"
        ),
        27: (
            "善行无辙迹，善言无瑕谪，善数不用筹策。"
            "善闭无关楗而不可开，善结无绳约而不可解。"
            "是以圣人常善救人，故无弃人；常善救物，故无弃物，是谓袭明。"
            "故善人者，不善人之师；不善人者，善人之资。"
        ),
        28: (
            "知其雄，守其雌，为天下溪。知其白，守其黑，为天下式。"
            "知其荣，守其辱，为天下谷。"
            "常德不离，复归于婴儿。朴散则为器，圣人用之则为官长，故大制不割。"
        ),
        29: (
            "将欲取天下而为之，吾见其不得已。"
            "天下神器，不可为也，为者败之，执者失之。"
            "故物或行或随，或歔或吹，或强或羸，或挫或隳。"
            "是以圣人去甚、去奢、去泰。"
        ),
        30: (
            "以道佐人主者，不以兵强天下。其事好还。"
            "师之所处，荆棘生焉；大军之后，必有凶年。"
            "善有果而已，不敢以取强。"
            "果而勿矜，果而勿伐，果而勿骄，果而不得已，果而勿强。"
            "物壮则老，是谓不道，不道早已。"
        ),
        31: (
            "夫佳兵者，不祥之器，物或恶之，故有道者不处。"
            "君子居则贵左，用兵则贵右。兵者，不祥之器，非君子之器，不得已而用之，恬淡为上。"
            "胜而不美，而美之者，是乐杀人。夫乐杀人者，则不可以得志于天下矣。"
            "吉事尚左，凶事尚右。偏将军居左，上将军居右，言以丧礼处之。"
            "杀人之众，以哀悲泣之；战胜，以丧礼处之。"
        ),
        32: (
            "道常无名，朴虽小，天下莫能臣也。侯王若能守之，万物将自宾。"
            "天地相合以降甘露，民莫之令而自均。"
            "始制有名，名亦既有，夫亦将知止，知止可以不殆。"
            "譬道之在天下，犹川谷之于江海。"
        ),
        33: (
            "知人者智，自知者明。胜人者有力，自胜者强。知足者富，强行者有志。"
            "不失其所者久，死而不亡者寿。"
        ),
        34: (
            "大道泛兮，其可左右。万物恃之而生而不辞，功成不名有，衣养万物而不为主。"
            "常无欲，可名于小；万物归焉而不为主，可名为大。"
            "以其终不自为大，故能成其大。"
        ),
        35: (
            "执大象，天下往。往而不害，安平太。"
            "乐与饵，过客止。道之出口，淡乎其无味，视之不足见，听之不足闻，用之不足既。"
        ),
        36: (
            "将欲歙之，必固张之；将欲弱之，必固强之；将欲废之，必固兴之；将欲夺之，必固与之。"
            "是谓微明。柔弱胜刚强。鱼不可脱于渊，国之利器不可以示人。"
        ),
        37: (
            "道常无为而无不为。侯王若能守之，万物将自化。"
            "化而欲作，吾将镇之以无名之朴。无名之朴，夫亦将无欲。"
            "不欲以静，天下将自定。"
        ),
        38: (
            "上德不德，是以有德；下德不失德，是以无德。"
            "上德无为而无以为，下德为之而有以为。"
            "失道而后德，失德而后仁，失仁而后义，失义而后礼。"
            "夫礼者，忠信之薄而乱之首。"
            "是以大丈夫处其厚，不居其薄；处其实，不居其华。故去彼取此。"
        ),
        39: (
            "昔之得一者：天得一以清，地得一以宁，神得一以灵，谷得一以盈，万物得一以生，"
            "侯王得一以为天下贞。"
            "故贵以贱为本，高以下为基。是以侯王自谓孤寡不穀。"
            "不欲琭如玉，珞如石。"
        ),
        40: (
            "反者，道之动；弱者，道之用。天下万物生于有，有生于无。"
        ),
    }
    if chapter in pairs:
        return pairs[chapter]
    return "。".join(lines) + "。"


def build_read_segment(
    chapter: int,
    *,
    work_dir: Path,
    tts: TtsConfig,
    skip_tts: bool,
    force_tts: bool,
    crf: int,
) -> Path:
    videos = list_chapter_videos()
    video_path = videos[chapter - 1]
    texts = load_chapter_texts()

    audio_dir = work_dir / "audio"
    seg_dir = work_dir / "segments"
    audio_dir.mkdir(parents=True, exist_ok=True)
    seg_dir.mkdir(parents=True, exist_ok=True)

    read_id = f"ch{chapter:02d}-read"
    read_seg = seg_dir / f"{read_id}.mp4"
    read_audio = audio_dir / f"{read_id}.mp3"
    narration = read_narration(chapter, texts)

    if force_tts and read_audio.exists():
        read_audio.unlink()
    if force_tts or not skip_tts:
        if not read_audio.exists() or read_audio.stat().st_size < 500:
            print(f"[{chapter:02d}] TTS 朗读（{tts.provider} {tts.rate}）…")
            generate_scene_audio(narration, read_audio, tts)
    elif not read_audio.exists():
        raise SystemExit(f"缺少朗读配音: {read_audio}")

    print(f"[{chapter:02d}] 合成朗读段（水墨动画）…")
    mux_chapter_segment(video_path, read_audio, read_seg, crf=crf)
    return read_seg


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter", type=int, default=1)
    parser.add_argument("-o", "--output", type=Path, default=None)
    parser.add_argument("--work-dir", type=Path, default=None)
    parser.add_argument("--skip-tts", action="store_true")
    parser.add_argument("--skip-read", action="store_true", help="不拼接朗读段（仅讲解）")
    parser.add_argument(
        "--reread",
        action="store_true",
        help="用 storyboard TTS 重录朗读段（忽略 read_video）",
    )
    parser.add_argument(
        "--read-video",
        type=Path,
        default=None,
        help="已有朗读段 mp4（默认读 JSON read_video）",
    )
    parser.add_argument("--skip-commentary", action="store_true", help="仅渲染朗读段")
    parser.add_argument(
        "--allow-missing-images",
        action="store_true",
        help="允许讲解段缺失配图（黑底；默认无图则中止）",
    )
    parser.add_argument("--read-rate", default=None, help="覆盖 JSON 中的 read_rate")
    parser.add_argument("--crf", type=int, default=20)
    args = parser.parse_args()

    ch = args.chapter
    cfg = load_chapter_config(ch)
    if cfg.get("mode") != "hybrid":
        print(
            f"第 {ch} 章 mode={cfg.get('mode')!r}，非 hybrid。"
            f"请用 scripts/build_daodejing_commentary.py",
            file=sys.stderr,
        )
        return 1

    storyboard_path = ROOT / cfg["storyboard"]
    if not storyboard_path.is_file():
        raise SystemExit(f"缺少讲解分镜: {storyboard_path}")

    work = (args.work_dir or ROOT / f"output/ch{ch:02d}-hybrid").resolve()
    out = (args.output or ROOT / f"output/daodejing-ch{ch:02d}-hybrid.mp4").resolve()
    read_rate = args.read_rate or cfg.get("read_rate", "-18%")

    segment_paths: list[Path] = []
    durations: list[tuple[str, float]] = []
    read_duration = 0.0
    read_id = f"ch{ch:02d}-read"
    comm_work = work / "commentary.work"

    storyboard = Storyboard.load(storyboard_path)
    read_tts = replace(storyboard.tts, rate=read_rate)

    if not args.skip_read:
        read_src = None if args.reread else args.read_video
        if read_src is None and not args.reread and cfg.get("read_video"):
            read_src = ROOT / cfg["read_video"]
        if read_src is not None:
            read_src = read_src.resolve()
            if not read_src.is_file():
                print(f"[{ch:02d}] 朗读段不存在，重新合成: {read_src.relative_to(ROOT)}")
                read_src = None
            else:
                print(f"[{ch:02d}] 使用已有朗读段: {read_src.relative_to(ROOT)}")
                segment_paths.append(read_src)
                read_duration = probe_duration_sec(read_src)
                durations.append((read_src.stem, read_duration))
        if read_src is None:
            read_seg = build_read_segment(
                ch,
                work_dir=work,
                tts=read_tts,
                skip_tts=args.skip_tts,
                force_tts=args.reread,
                crf=args.crf,
            )
            segment_paths.append(read_seg)
            read_duration = probe_duration_sec(read_seg)
            durations.append((read_seg.stem, read_duration))

    if not args.skip_commentary:
        comm_out = work / "commentary"
        print(f"[{ch:02d}] pipeline 讲解段…")
        commentary_path = render_storyboard(
            storyboard_path,
            work_dir=comm_work,
            output_dir=comm_out,
            skip_tts=args.skip_tts,
            allow_missing_images=args.allow_missing_images,
        )
        segment_paths.append(commentary_path)
        durations.append(("commentary", probe_duration_sec(commentary_path)))

    if not segment_paths:
        raise SystemExit("没有可拼接的片段")

    concat_path = work / "hybrid_concat.mp4"
    print(f"拼接 {len(segment_paths)} 段…")
    _concat_videos(require_ffmpeg(), segment_paths, concat_path)

    out.parent.mkdir(parents=True, exist_ok=True)

    bgm_cfg = storyboard.bgm
    if bgm_cfg.enabled or (bgm_cfg.tracks and not args.skip_commentary):
        bgm = BgmConfig(
            enabled=True,
            tracks=bgm_cfg.tracks,
            volume=bgm_cfg.volume,
            crossfade_sec=bgm_cfg.crossfade_sec,
            fade_in_sec=bgm_cfg.fade_in_sec,
            fade_out_sec=bgm_cfg.fade_out_sec,
            switch_at_scene=bgm_cfg.switch_at_scene,
        )
        bgm_scenes = build_hybrid_bgm_scenes(
            read_id=read_id,
            read_duration=read_duration,
            storyboard=storyboard,
            comm_work=comm_work,
        )
        if not bgm_scenes:
            bgm_scenes = build_rendered_scenes(durations)
        print("混入全片 BGM…")
        mix_bgm_into_video(concat_path, ROOT, bgm, bgm_scenes, out_path=out)
    else:
        shutil.copy2(concat_path, out)

    sb_data = json.loads(storyboard_path.read_text(encoding="utf-8"))
    comm_filename = sb_data.get("output", {}).get("filename", "commentary.mp4")

    total_min = sum(d for _, d in durations) / 60
    print(f"\n完成。约 {total_min:.1f} 分钟")
    print(f"成片: {out}")
    read_label = str(
        work / "segments" / f"ch{ch:02d}-read.mp4"
        if args.reread or not cfg.get("read_video")
        else args.read_video or cfg.get("read_video")
    )
    print(f"朗读段: {read_label}")
    print(f"讲解段: {work / 'commentary' / comm_filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
