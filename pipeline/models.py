from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .brand import (
    BACKGROUND_COLOR,
    ENDING_DURATION_SEC,
    ENDING_IMAGE,
    ENDING_NARRATION,
    ENDING_SCENE_ID,
    HOOK_BG,
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
    voice: str = "zh-CN-YunxiNeural"
    rate: str = "+0%"


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
    ending: EndingConfig = field(default_factory=EndingConfig)
    watermark: WatermarkConfig = field(default_factory=WatermarkConfig)

    def all_scenes(self) -> list[Scene]:
        """正文分镜 + 固定片尾（若已启用且未手动定义 ending 镜头）。"""
        scenes = list(self.scenes)
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
        watermark = WatermarkConfig(
            **{**WatermarkConfig().__dict__, **data.get("watermark", {})}
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
            ending=ending,
            watermark=watermark,
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
