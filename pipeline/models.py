from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .brand import (
    BACKGROUND_COLOR,
    COVER_DURATION_SEC,
    COVER_OUTPUT_DIR,
    COVER_SCENE_ID,
    ENDING_DURATION_SEC,
    ENDING_IMAGE,
    ENDING_NARRATION,
    ENDING_SCENE_ID,
    HOOK_BG,
    PLACEHOLDER_HOME_IMAGE,
    FONT_INDEX_LIGHT,
    FONT_INDEX_REGULAR,
    FONT_PATH,
    SUBTITLE_ALIGN,
    SUBTITLE_COLOR,
    SUBTITLE_FONT_SIZE,
    SUBTITLE_MARGIN_BOTTOM,
    SUBTITLE_MAX_CHARS,
    SUBTITLE_MAX_LINES,
    SUBTITLE_MAX_WIDTH_RATIO,
    SUBTITLE_STYLE,
    WATERMARK_COLOR,
    WATERMARK_FONT_SIZE,
    WATERMARK_IMAGE,
    WATERMARK_LABEL_GAP,
    WATERMARK_MARGIN_X,
    WATERMARK_MARGIN_Y,
    WATERMARK_MODE,
    WATERMARK_BACKPLATE,
    WATERMARK_BACKPLATE_PAD,
    WATERMARK_BACKPLATE_RADIUS,
    WATERMARK_KEY_LIGHT_BG,
    WATERMARK_OPACITY,
    WATERMARK_SEAL_ONLY,
    WATERMARK_STYLE,
    WATERMARK_TEXT,
    WATERMARK_WIDTH_RATIO,
)


@dataclass
class OutputConfig:
    width: int = 1920
    height: int = 1080
    fps: int = 30
    filename: str = "final.mp4"


@dataclass
class StyleConfig:
    background_color: str = BACKGROUND_COLOR
    motion: str = "auto"  # auto | static | kenburns_in | kenburns_out | pan_up | …
    subtitle_font_size: int = SUBTITLE_FONT_SIZE
    subtitle_color: str = SUBTITLE_COLOR
    subtitle_margin_bottom: int = SUBTITLE_MARGIN_BOTTOM
    subtitle_max_width_ratio: float = SUBTITLE_MAX_WIDTH_RATIO
    subtitle_max_lines: int = SUBTITLE_MAX_LINES
    subtitle_max_chars: int = SUBTITLE_MAX_CHARS
    subtitle_style: str = SUBTITLE_STYLE
    subtitle_align: str = SUBTITLE_ALIGN
    font_path: str | None = FONT_PATH
    font_index: int = FONT_INDEX_REGULAR


@dataclass
class TtsConfig:
    provider: str = "edge"  # edge | volcengine | gemini | google_cloud
    voice: str = "zh-CN-YunxiNeural"
    rate: str = "+0%"
    model: str = "gemini-2.5-flash-preview-tts"
    language_code: str = "zh-CN"
    resource_id: str = "seed-tts-2.0"  # 火山：seed-tts-2.0 | seed-tts-1.0
    emotion: str = ""  # 火山情感，如 narrator / storytelling


@dataclass
class ChapterDef:
    """章节定义；渲染前自动生成对应 JPG。"""

    id: str
    label: str
    file: str | None = None


@dataclass
class Scene:
    id: str
    narration: str
    image: str | None = None
    duration_sec: float | None = None
    pause_after_sec: float = 0.3
    scene_type: str | None = None  # intro | chapter | body
    chapter: str | None = None  # 引用 chapters[].id
    chapter_title: str | None = None  # 直接指定章节名（无 chapters 表时）
    subtitle: str | None = None  # 可选；烧录用短字幕（省略则用旁白，且受字数限制）
    burn_subtitles: bool | None = None  # 强制开/关烧录字幕
    timestamp_label: str | None = None  # YouTube 简介时间轴打点（该镜起始时刻）
    motion: str | None = None  # 覆盖 style.motion：static | kenburns_in | kenburns_out | pan_*


def _scene_from_dict(data: dict[str, Any]) -> Scene:
    fields = {f.name for f in Scene.__dataclass_fields__.values()}
    return Scene(**{k: v for k, v in data.items() if k in fields})


def _chapter_from_dict(data: dict[str, Any]) -> ChapterDef:
    fields = {f.name for f in ChapterDef.__dataclass_fields__.values()}
    return ChapterDef(**{k: v for k, v in data.items() if k in fields})


@dataclass
class WatermarkConfig:
    """左上角品牌水印（默认 Logo 图片）。"""

    enabled: bool = True
    mode: str = WATERMARK_MODE
    image: str = WATERMARK_IMAGE
    width_ratio: float = WATERMARK_WIDTH_RATIO
    opacity: float = WATERMARK_OPACITY
    text: str = WATERMARK_TEXT
    font_size: int = WATERMARK_FONT_SIZE
    color: str = WATERMARK_COLOR
    margin_x: int = WATERMARK_MARGIN_X
    margin_y: int = WATERMARK_MARGIN_Y
    label_gap: int = WATERMARK_LABEL_GAP
    style: str = WATERMARK_STYLE
    font_index: int = FONT_INDEX_LIGHT
    seal_only: bool = WATERMARK_SEAL_ONLY
    key_light_bg: bool = WATERMARK_KEY_LIGHT_BG
    backplate: bool = WATERMARK_BACKPLATE
    backplate_pad: int = WATERMARK_BACKPLATE_PAD
    backplate_radius: int = WATERMARK_BACKPLATE_RADIUS


@dataclass
class AmbientConfig:
    """全片氛围层（浮尘 / 水墨缘晕 / 水面粼光）。"""

    enabled: bool = True
    dust_opacity: float = 0.15
    ink_opacity: float = 0.07
    water_opacity: float = 0.09
    water_chapters: list[int] | None = None  # None → 内置水柔章列表


@dataclass
class BgmConfig:
    """背景音乐（assets/BGM，成片后混音）。"""

    enabled: bool = True
    tracks: list[str] = field(
        default_factory=lambda: [
            "assets/BGM/Music_fx_relaxing_chinese_flute.wav",
            "assets/BGM/Music_fx_relaxing_chinese_guzheng.wav",
        ]
    )
    volume: float = 0.16
    crossfade_sec: float = 4.0
    fade_in_sec: float = 1.5
    fade_out_sec: float = 4.0
    switch_at_scene: str = "open-2"


YOUTUBE_DEFAULT_TAGS = (
    "道德经",
    "老子",
    "观念黑盒",
    "The Blackbox",
    "人生哲学",
    "权力系统",
    "马基雅维利",
    "道德经五讲",
    "中文",
)

CHANNEL_ABOUT_ZH = """你以为的规律，其实是锁死你的系统。

欢迎来到【观念黑盒】。
我们不熬鸡汤，只做历史沙盘与权力系统的暴力拆解。
从《道德经》里的顶级「苟」道，到现代社会的隐形霸权；
用「马基雅维利」的冷酷视角，剥离道德滤镜，还原利益链条与底层逻辑。

弱者才需要天天证明自己强大，真正的执棋者，都在极力证明自己「人畜无害」。

打开观念黑盒，重新认识自己。"""

CHANNEL_ABOUT_EN = """The rules you believe in are merely the system locking you in.
Welcome to The Blackbox.
We deconstruct history, power dynamics, and societal frameworks from a macro, systems-theory perspective.
Open the blackbox. Unplug from the matrix."""


@dataclass
class YouTubeTimelineMarker:
    """简介章节时间轴：在指定 scene 起始处打点（scene 为分镜 id，含 cover / ending）。"""

    scene: str
    label: str


@dataclass
class YouTubeConfig:
    """YouTube 上传元数据（videos.insert）。"""

    privacy_status: str = "unlisted"
    category_id: str = "27"
    tags: list[str] = field(default_factory=lambda: list(YOUTUBE_DEFAULT_TAGS))
    description_intro: str = ""
    channel_url: str = "https://www.youtube.com/@观念黑盒"
    channel_about_zh: str = CHANNEL_ABOUT_ZH
    channel_about_en: str = CHANNEL_ABOUT_EN
    description_footer: str = ""
    timeline: list[YouTubeTimelineMarker] = field(default_factory=list)
    timeline_heading: str = "📌 章节时间轴（点击时间戳跳转）"
    playlist_id: str = ""
    made_for_kids: bool = False
    default_language: str = "zh-CN"
    recording_date: str = ""
    thumbnail_image: str = ""  # 投稿缩略图；空则与 B 站 cover 同源解析


DOUYIN_DEFAULT_TAGS = (
    "道德经",
    "老子",
    "庄子",
    "国学",
    "观念黑盒",
    "人生哲学",
)


@dataclass
class DouyinConfig:
    """抖音投稿元数据（Playwright 浏览器上传）。"""

    tags: list[str] = field(default_factory=lambda: list(DOUYIN_DEFAULT_TAGS))
    description_intro: str = ""
    # 允许评论：open | close | friend（仅好友）
    comment_type: str = "open"
    # 视频发布权限：public | private | friend
    privacy: str = "public"
    # 合集 / 话题（填写名称字符串，脚本会在页面中查找并选择）
    playlist: str = ""
    # 地理位置标签（可留空）
    location: str = ""


@dataclass
class BilibiliConfig:
    """B 站投稿元数据（创作中心 / bilibili-api 上传）。"""

    tid: int = 124  # 知识区 · 社科·法律·心理
    copyright_original: bool = True
    tags: list[str] = field(default_factory=list)
    description_intro: str = ""
    dynamic: str = ""
    channel_url: str = "https://space.bilibili.com/481103225"
    cover_image: str = ""
    series_id: int = 0  # 旧版「视频列表」series_id，上传后可 API 归入
    season_id: int = 0  # 空间「合集·XXX」season_id（对照用；排序多在创作中心）
    no_reprint: bool = True
    open_elec: bool = False
    source: str = ""
    reuse_youtube_timeline: bool = True


def _youtube_timeline_from_dict(items: list) -> list[YouTubeTimelineMarker]:
    out: list[YouTubeTimelineMarker] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        scene = str(item.get("scene", "")).strip()
        label = str(item.get("label", "")).strip()
        if scene and label:
            out.append(YouTubeTimelineMarker(scene=scene, label=label))
    return out


@dataclass
class CoverConfig:
    """片头封面（首页幻灯片，默认静音）。"""

    enabled: bool = True
    duration_sec: float = COVER_DURATION_SEC
    narration: str = ""
    pause_after_sec: float = 0.0
    hook: str = ""
    subtitle: str = "观念黑盒 · 道德经五讲"
    image: str = ""  # 本期独立封面 JPG，如 assets/covers/daodejing-ep02-cover.jpg


@dataclass
class EndingConfig:
    """片尾镜头；默认 hook_bg + 左侧片尾文案。"""

    enabled: bool = True
    image: str = ENDING_IMAGE
    duration_sec: float = ENDING_DURATION_SEC
    narration: str = ENDING_NARRATION
    pause_after_sec: float = 0.0


@dataclass
class Storyboard:
    title: str
    language: str = "zh-CN"
    output: OutputConfig = field(default_factory=OutputConfig)
    style: StyleConfig = field(default_factory=StyleConfig)
    tts: TtsConfig = field(default_factory=TtsConfig)
    scenes: list[Scene] = field(default_factory=list)
    chapters: list[ChapterDef] = field(default_factory=list)
    cover: CoverConfig = field(default_factory=CoverConfig)
    ending: EndingConfig = field(default_factory=EndingConfig)
    watermark: WatermarkConfig = field(default_factory=WatermarkConfig)
    ambient: AmbientConfig = field(default_factory=AmbientConfig)
    bgm: BgmConfig = field(default_factory=BgmConfig)
    youtube: YouTubeConfig = field(default_factory=YouTubeConfig)
    bilibili: BilibiliConfig = field(default_factory=BilibiliConfig)
    douyin: DouyinConfig = field(default_factory=DouyinConfig)

    def cover_image_rel(self) -> str:
        """本期片头/投稿封面路径（每期独立，互不覆盖）。"""
        if self.cover.image.strip():
            return self.cover.image.strip()
        stem = Path(self.output.filename or "final.mp4").stem or "episode"
        safe = re.sub(r"[^\w\-一-龥]", "-", stem).strip("-") or "episode"
        return f"{COVER_OUTPUT_DIR}/{safe}-cover.jpg"

    def all_scenes(self) -> list[Scene]:
        """封面 + 正文分镜 + 片尾（若已启用且未手动定义）。"""
        scenes: list[Scene] = []
        if self.cover.enabled and not any(s.id == COVER_SCENE_ID for s in self.scenes):
            scenes.append(
                Scene(
                    id=COVER_SCENE_ID,
                    scene_type="intro",
                    narration=self.cover.narration,
                    image=self.cover_image_rel(),
                    duration_sec=self.cover.duration_sec,
                    pause_after_sec=self.cover.pause_after_sec,
                )
            )
        scenes.extend(self.scenes)
        if not self.ending.enabled:
            return scenes
        if any(s.id == ENDING_SCENE_ID for s in scenes):
            return scenes
        scenes.append(
            Scene(
                id=ENDING_SCENE_ID,
                narration=self.ending.narration,
                image=self.ending.image,
                duration_sec=self.ending.duration_sec,
                pause_after_sec=self.ending.pause_after_sec,
            )
        )
        return scenes

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Storyboard:
        output = OutputConfig(**{**OutputConfig().__dict__, **data.get("output", {})})
        style = StyleConfig(**{**StyleConfig().__dict__, **data.get("style", {})})
        tts = TtsConfig(**{**TtsConfig().__dict__, **data.get("tts", {})})
        ending = EndingConfig(**{**EndingConfig().__dict__, **data.get("ending", {})})
        cover = CoverConfig(**{**CoverConfig().__dict__, **data.get("cover", {})})
        watermark = WatermarkConfig(
            **{**WatermarkConfig().__dict__, **data.get("watermark", {})}
        )
        ambient = AmbientConfig(
            **{**AmbientConfig().__dict__, **data.get("ambient", {})}
        )
        bgm = BgmConfig(**{**BgmConfig().__dict__, **data.get("bgm", {})})
        yt_raw = data.get("youtube", {})
        timeline = _youtube_timeline_from_dict(yt_raw.get("timeline", []))
        yt_fields = {f.name for f in YouTubeConfig.__dataclass_fields__.values()}
        youtube = YouTubeConfig(
            **{
                k: v
                for k, v in {**YouTubeConfig().__dict__, **yt_raw}.items()
                if k in yt_fields and k != "timeline"
            },
            timeline=timeline,
        )
        bili_raw = data.get("bilibili", {})
        bili_fields = {f.name for f in BilibiliConfig.__dataclass_fields__.values()}
        bilibili = BilibiliConfig(
            **{
                k: v
                for k, v in {**BilibiliConfig().__dict__, **bili_raw}.items()
                if k in bili_fields
            }
        )
        douyin_raw = data.get("douyin", {})
        douyin_fields = {f.name for f in DouyinConfig.__dataclass_fields__.values()}
        douyin = DouyinConfig(
            **{
                k: v
                for k, v in {**DouyinConfig().__dict__, **douyin_raw}.items()
                if k in douyin_fields
            }
        )
        scenes = [_scene_from_dict(s) for s in data.get("scenes", [])]
        chapters = [_chapter_from_dict(c) for c in data.get("chapters", [])]
        return cls(
            title=data["title"],
            language=data.get("language", "zh-CN"),
            output=output,
            style=style,
            tts=tts,
            scenes=scenes,
            chapters=chapters,
            cover=cover,
            ending=ending,
            watermark=watermark,
            ambient=ambient,
            bgm=bgm,
            youtube=youtube,
            bilibili=bilibili,
            douyin=douyin,
        )

    @classmethod
    def load(cls, path: Path) -> Storyboard:
        with path.open(encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


@dataclass
class RenderedScene:
    scene: Scene
    audio_path: Path
    audio_duration_sec: float
    segment_path: Path | None = None
