"""根据 storyboard JSON 自动生成首页 / 章节占位图并解析镜头素材。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .brand import PLACEHOLDER_HOME_IMAGE
from .models import ChapterDef, Scene, Storyboard
from .slides import (
    default_chapter_path,
    render_chapter_slide,
    render_cover_hook_slide,
    render_home_slide,
)


def _resolve_asset_path(project_root: Path, rel: str) -> Path:
    return (project_root / rel).resolve()


def prepare_storyboard_assets(
    storyboard: Storyboard,
    project_root: Path,
    *,
    storyboard_path: Path | None = None,
) -> Storyboard:
    """
    - cover.enabled → 生成 assets/covers/<本期>-cover.jpg（独立，不覆盖 placeholder-home）
    - 根据 chapters[] 生成章节 JPG
    - scene_type=intro → 绑定 placeholder-home（仅旧式 intro 镜头）
    """
    if storyboard_path:
        project_root = storyboard_path.parent.parent.resolve()
    else:
        project_root = project_root.resolve()

    hook = _resolve_asset_path(project_root, "assets/hook_bg.webp")
    logo = _resolve_asset_path(project_root, "assets/Logo.png")
    chapter_by_id = {c.id: c for c in storyboard.chapters}
    hook_path = hook if hook.exists() else None
    logo_path = logo if logo.exists() else None

    if storyboard.cover.enabled:
        cover_rel = storyboard.cover_image_rel()
        cover_out = _resolve_asset_path(project_root, cover_rel)
        cover_out.parent.mkdir(parents=True, exist_ok=True)
        if storyboard.cover.hook.strip():
            render_cover_hook_slide(
                storyboard.cover.hook.strip(),
                storyboard.cover.subtitle,
                cover_out,
                hook_path=hook_path,
                logo_path=logo_path,
            )
        else:
            render_home_slide(
                storyboard.title,
                cover_out,
                hook_path=hook_path,
                logo_path=logo_path,
            )

    needs_legacy_home = any(
        (s.scene_type or "").strip().lower() == "intro" for s in storyboard.scenes
    )
    if needs_legacy_home:
        home_out = _resolve_asset_path(project_root, PLACEHOLDER_HOME_IMAGE)
        if not storyboard.cover.enabled:
            render_home_slide(
                storyboard.title,
                home_out,
                hook_path=hook_path,
                logo_path=logo_path,
            )

    for ch in storyboard.chapters:
        rel = default_chapter_path(ch.id, ch.file)
        out = _resolve_asset_path(project_root, rel)
        render_chapter_slide(
            ch.label,
            out,
            hook_path=hook_path,
            logo_path=logo_path,
        )

    new_scenes: list[Scene] = []
    for scene in storyboard.scenes:
        image = scene.image
        scene_type = (scene.scene_type or "").strip().lower()

        if scene_type == "intro":
            image = PLACEHOLDER_HOME_IMAGE

        elif scene_type == "chapter" or scene.chapter or scene.chapter_title:
            label: str | None = scene.chapter_title
            rel: str | None = None
            if scene.chapter:
                ch = chapter_by_id.get(scene.chapter)
                if not ch:
                    raise ValueError(
                        f"镜头 {scene.id} 引用了未知章节 chapter={scene.chapter!r}，"
                        f"请在顶层 chapters 中定义"
                    )
                label = label or ch.label
                rel = default_chapter_path(ch.id, ch.file)
            elif label:
                safe = scene.id.replace("/", "-")
                rel = default_chapter_path(safe, None)
            else:
                raise ValueError(
                    f"镜头 {scene.id} 为 chapter 类型但未提供 chapter 或 chapter_title"
                )

            out = _resolve_asset_path(project_root, rel)
            render_chapter_slide(
                label,
                out,
                hook_path=hook_path,
                logo_path=logo_path,
            )
            image = rel

        new_scenes.append(replace(scene, image=image))

    return replace(storyboard, scenes=new_scenes)
