"""抖音创作者平台自动上传：基于 patchright 模拟浏览器操作。

工作原理：
  1. 第一次运行 --auth-only：打开抖音创作中心，手动扫码/登录，保存 Cookie
  2. 后续运行 --upload：加载 Cookie，直接进入上传页面，全自动填写并发布

Cookie 文件默认存放：credentials/douyin_cookie.json

参考实现：github.com/dreammis/social-auto-upload
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import DouyinConfig, Storyboard

CREATOR_URL = "https://creator.douyin.com"
UPLOAD_URL = "https://creator.douyin.com/creator-micro/content/upload"
COOKIE_FILENAME = "douyin_cookie.json"
DEFAULT_TIMEOUT = 90_000
UPLOAD_TIMEOUT = 300_000


def cookie_path(project_root: Path) -> Path:
    return project_root / "credentials" / COOKIE_FILENAME


# ---------------------------------------------------------------------------
# Cookie 验证
# ---------------------------------------------------------------------------

async def _cookie_auth_async(account_file: Path) -> bool:
    from patchright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        try:
            context = await browser.new_context(storage_state=str(account_file))
            page = await context.new_page()
            await page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
            try:
                await page.wait_for_url(UPLOAD_URL, timeout=5000)
            except Exception:
                return False
            if await page.get_by_text("手机号登录").count() or await page.get_by_text("扫码登录").count():
                return False
            return True
        finally:
            await browser.close()


def verify_cookie(project_root: Path) -> bool:
    path = cookie_path(project_root)
    if not path.is_file():
        raise FileNotFoundError(
            f"未找到 Cookie: {path}\n请先运行: python3 scripts/upload_douyin.py --auth-only"
        )
    return asyncio.run(_cookie_auth_async(path))


# ---------------------------------------------------------------------------
# Auth：扫码登录保存 Cookie
# ---------------------------------------------------------------------------

async def _auth_async(out: Path) -> None:
    from patchright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(CREATOR_URL, timeout=DEFAULT_TIMEOUT)

        print("等待登录完成（最长 5 分钟）…", flush=True)
        deadline = time.time() + 300
        logged_in = False
        last_url = ""
        while time.time() < deadline:
            url = page.url
            if url != last_url:
                print(f"  URL: {url}", flush=True)
                last_url = url
            if (
                "douyin.com" in url
                and "/login" not in url
                and "passport" not in url
                and "sso" not in url
            ):
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
                logged_in = True
                break
            await asyncio.sleep(1)

        if not logged_in:
            await browser.close()
            raise RuntimeError("登录超时（5 分钟），请重新运行 --auth-only")

        await context.storage_state(path=str(out))
        print(f"\n✓ 登录成功，Cookie 已保存: {out}", flush=True)
        await browser.close()


def auth_and_save_cookie(project_root: Path) -> Path:
    out = cookie_path(project_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    print("=" * 60, flush=True)
    print("打开抖音创作者中心，请在浏览器中完成登录（扫码或账号密码）。", flush=True)
    print("登录成功后脚本会自动检测并保存 Cookie。", flush=True)
    print("=" * 60, flush=True)
    asyncio.run(_auth_async(out))
    return out


# ---------------------------------------------------------------------------
# 文案构建
# ---------------------------------------------------------------------------

def build_description(storyboard: "Storyboard", config: "DouyinConfig") -> str:
    """构建抖音视频文案。

    Fallback 优先级（简介）：
      1. config.description_intro
      2. storyboard.bilibili.description_intro
      3. storyboard.youtube.description_intro
      4. 第一个有旁白的分镜前 100 字
    """
    from .models import DOUYIN_DEFAULT_TAGS

    parts: list[str] = []

    hook = (storyboard.cover.hook or "").strip()
    if hook:
        parts.append(hook)

    intro = (config.description_intro or "").strip()
    if not intro:
        intro = (getattr(storyboard.bilibili, "description_intro", "") or "").strip()
    if not intro:
        intro = (getattr(storyboard.youtube, "description_intro", "") or "").strip()
    if not intro:
        for scene in storyboard.scenes:
            if scene.narration.strip():
                intro = scene.narration.strip()[:100]
                if len(scene.narration.strip()) > 100:
                    intro += "…"
                break
    if intro:
        parts.append(intro)

    tags = config.tags or []
    if set(tags) == set(DOUYIN_DEFAULT_TAGS):
        bili_tags = getattr(storyboard.bilibili, "tags", None) or []
        if bili_tags:
            tags = bili_tags
    tags = tags[:5]  # 抖音最多 5 个话题标签

    if tags:
        parts.append(" ".join(f"#{t.strip()}" for t in tags if t.strip()))

    text = "\n\n".join(parts).strip()
    if len(text) > 2200:
        text = text[:2200]
    return text


# ---------------------------------------------------------------------------
# 核心上传（async）
# ---------------------------------------------------------------------------

async def _upload_async(
    video_path: Path,
    title: str,
    tags: list[str],
    desc: str,
    account_file: Path,
    cover_path: Path | None,
    portrait_cover_path: Path | None,
    publish_at: str | None,
    playlist: str = "",
) -> dict:
    from patchright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(storage_state=str(account_file))
        page = await context.new_page()

        # ── 1. 进入上传页 ────────────────────────────────────────────
        print("打开抖音上传页…", flush=True)
        await page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
        await page.wait_for_url(UPLOAD_URL, timeout=DEFAULT_TIMEOUT)

        # ── 2. 选择视频文件 ──────────────────────────────────────────
        print("选择视频文件…", flush=True)
        await page.wait_for_selector("div[class^='container'] input", state="attached", timeout=60_000)
        await page.locator("div[class^='container'] input").set_input_files(str(video_path))
        print(f"已选择: {video_path.name}", flush=True)

        # ── 3. 等待跳转到发布编辑页 ──────────────────────────────────
        print("等待视频上传并跳转到发布页…", flush=True)
        while True:
            try:
                await page.wait_for_url(
                    "https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page",
                    timeout=3000,
                )
                print("进入 v1 发布页 ✓", flush=True)
                break
            except Exception:
                pass
            try:
                await page.wait_for_url(
                    "https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page",
                    timeout=3000,
                )
                print("进入 v2 发布页 ✓", flush=True)
                break
            except Exception:
                pass
            await asyncio.sleep(0.5)

        await asyncio.sleep(1)

        # ── 4. 填写标题 ──────────────────────────────────────────────
        print("填写标题…", flush=True)
        title_input = page.locator('input[placeholder*="填写作品标题"]').first
        await title_input.wait_for(state="visible", timeout=120_000)
        await title_input.fill(title[:30])
        print(f"标题填写: {title[:30]}", flush=True)

        # ── 5. 填写描述 + 话题 ───────────────────────────────────────
        print("填写描述和话题…", flush=True)
        desc_editor = page.locator('div.zone-container[contenteditable="true"]').first
        await desc_editor.wait_for(state="visible", timeout=30_000)
        await desc_editor.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Delete")

        # 先输入简介
        if desc:
            # 只取简介部分（不含 #标签），标签单独用 keyboard.type 触发联想
            intro_only = desc.split("\n\n")[0] if "\n\n" in desc else desc.split("#")[0].strip()
            if intro_only:
                await page.keyboard.type(intro_only)

        # 话题标签
        for tag in tags:
            await page.keyboard.type(" #" + tag)
            await page.keyboard.press("Space")
        await page.keyboard.press("Escape")  # 收起话题联想下拉
        print("描述和话题填写完成 ✓", flush=True)

        # ── 6. 等待视频上传完成（检测"重新上传"出现）───────────────
        print("等待视频转码完成…", flush=True)
        while True:
            try:
                count = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
                if count > 0:
                    print("视频上传完成 ✓", flush=True)
                    break
                if await page.locator('div.progress-div > div:has-text("上传失败")').count():
                    print("⚠️  上传失败，重试…", flush=True)
                    await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(str(video_path))
            except Exception:
                pass
            await asyncio.sleep(2)

        # ── 7. 封面 ──────────────────────────────────────────────────
        if cover_path or portrait_cover_path:
            print("上传封面…", flush=True)
            await page.wait_for_timeout(2000)
            try:
                # 先把焦点从描述编辑器移走
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)

                # 清 shepherd 浮层和话题下拉
                await page.evaluate(
                    "() => document.querySelectorAll('.shepherd-element,.shepherd-modal-overlay-container,[class*=\"mention-wrapper\"]').forEach(e=>e.remove())"
                )
                await page.get_by_text("选择封面", exact=True).first.click(force=True)
                await page.wait_for_selector("div.dy-creator-content-modal", timeout=20_000)
                cover_modal = page.locator("div.dy-creator-content-modal").first
                await page.wait_for_timeout(1500)

                # 横封面：[0]=AI推荐列表, [1]=真正的上传框
                if cover_path and cover_path.is_file():
                    try:
                        await cover_modal.get_by_text("设置横封面", exact=True).first.click(timeout=3000)
                        await page.wait_for_timeout(800)
                    except Exception:
                        pass
                    await cover_modal.locator("input.semi-upload-hidden-input").nth(1).set_input_files(str(cover_path))
                    await page.wait_for_timeout(2000)
                    print("横封面上传完成 ✓", flush=True)

                # 竖封面：切换 tab 后同样用 nth(1)
                if portrait_cover_path and portrait_cover_path.is_file():
                    try:
                        await cover_modal.get_by_text("设置竖封面", exact=True).first.click(timeout=3000)
                        await page.wait_for_timeout(800)
                    except Exception:
                        pass
                    await cover_modal.locator("input.semi-upload-hidden-input").nth(1).set_input_files(str(portrait_cover_path))
                    await page.wait_for_timeout(2000)
                    print("竖封面上传完成 ✓", flush=True)

                await cover_modal.get_by_role("button", name="完成", exact=True).first.click()
                await page.wait_for_selector("div.dy-creator-content-modal", state="hidden", timeout=20_000)
                print("封面设置完成 ✓", flush=True)
            except Exception as exc:
                print(f"⚠️  封面上传失败: {exc}", flush=True)

        # ── 8. 自主声明 ──────────────────────────────────────────────
        print("设置自主声明…", flush=True)
        try:
            entry = page.get_by_text("请选择自主声明").first
            await entry.wait_for(state="visible", timeout=6000)
            await entry.click()
            dialog = page.locator(".semi-modal-content").filter(has_text="对作品内容添加声明").first
            await dialog.wait_for(state="visible", timeout=6000)
            option = dialog.locator(".semi-radio").filter(has_text="内容为个人观点或见解").first
            if await option.count():
                await option.click(timeout=6000)
            await dialog.get_by_role("button", name="确定").click(timeout=6000)
            print("自主声明设置完成 ✓", flush=True)
        except Exception as exc:
            print(f"⚠️  自主声明跳过: {exc}", flush=True)

        # ── 9. 合集 ──────────────────────────────────────────────────
        if playlist:
            print(f"设置合集: {playlist}…", flush=True)
            try:
                # 点「请选择合集」下拉框
                selector = page.locator(".select-collection-nkL6sA").first
                await selector.wait_for(state="visible", timeout=6000)
                await selector.click()
                await page.wait_for_timeout(800)

                # 在下拉列表里选匹配的合集
                option = page.locator(f'[role="option"]:has-text("{playlist}")').first
                if not await option.count():
                    # 备用：li 里找
                    option = page.locator(f'li:has-text("{playlist}")').first
                if await option.count():
                    await option.click()
                    print(f"合集已选择: {playlist} ✓", flush=True)
                else:
                    print(f"⚠️  未找到合集「{playlist}」，可用选项：")
                    opts = await page.locator('[role="option"]').all()
                    for o in opts[:10]:
                        print(f"    - {await o.inner_text()}")
            except Exception as exc:
                print(f"⚠️  合集设置跳过: {exc}", flush=True)

        # ── 10. 定时发布 ─────────────────────────────────────────────
        if publish_at:
            try:
                # publish_at 格式：'YYYY-MM-DD HH:MM'，需转为抖音接受的 'YYYY年MM月DD日 HH:MM'
                from datetime import datetime as _dt
                dt = _dt.strptime(publish_at, "%Y-%m-%d %H:%M")
                publish_at_cn = dt.strftime("%Y年%m月%d日 %H:%M")

                await page.locator("[class^='radio']:has-text('定时发布')").click()
                await asyncio.sleep(1)
                time_input = page.locator('.semi-input[placeholder="日期和时间"]').first
                await time_input.click()
                await asyncio.sleep(1)
                await page.keyboard.press("Control+KeyA")
                await page.keyboard.type(publish_at_cn)
                await page.keyboard.press("Enter")
                await asyncio.sleep(1)
                val = await time_input.evaluate("e => e.value")
                print(f"定时发布设置: {val} ✓", flush=True)
            except Exception as exc:
                print(f"⚠️  定时发布设置失败: {exc}", flush=True)

        # ── 10. 点击发布 ─────────────────────────────────────────────
        print("点击发布按钮…", flush=True)
        deadline = asyncio.get_event_loop().time() + 60  # 最多等 60 秒
        while asyncio.get_event_loop().time() < deadline:
            try:
                await page.evaluate(
                    "() => { document.querySelectorAll('.shepherd-element,.shepherd-modal-overlay-container,[class*=\"mention-wrapper\"]').forEach(e=>e.remove()); }"
                )
                # 定时发布后按钮文字可能变为"定时发布"，立即发布时是"发布"
                for btn_name in ["发布", "定时发布"]:
                    publish_btn = page.get_by_role("button", name=btn_name, exact=True)
                    if await publish_btn.count() and await publish_btn.is_enabled():
                        await publish_btn.click(force=True)
                        break
                await page.wait_for_url(
                    "https://creator.douyin.com/creator-micro/content/manage**",
                    timeout=5000,
                )
                print("\n✓ 抖音视频发布成功！", flush=True)
                break
            except Exception:
                await asyncio.sleep(0.5)
        else:
            print("\n⚠️  发布按钮超时，请手动检查抖音后台", flush=True)

        result_url = page.url
        await context.storage_state(path=str(account_file))
        await context.close()
        await browser.close()

    return {
        "title": title,
        "url": result_url,
        "video": str(video_path),
        "publish_at": publish_at or "immediate",
    }


# ---------------------------------------------------------------------------
# 对外接口（同步包装）
# ---------------------------------------------------------------------------

def upload_video(
    video_path: Path,
    storyboard: "Storyboard",
    *,
    project_root: Path,
    config: "DouyinConfig | None" = None,
    cover_path: Path | None = None,
    publish_at: str | None = None,
    dry_run: bool = False,
) -> dict:
    cfg = config or storyboard.douyin
    title = storyboard.title.strip()[:30]
    desc = build_description(storyboard, cfg)
    tags = cfg.tags or []

    # tags fallback 到 bilibili，最多取 5 个
    from .models import DOUYIN_DEFAULT_TAGS
    if set(tags) == set(DOUYIN_DEFAULT_TAGS):
        bili_tags = getattr(storyboard.bilibili, "tags", None) or []
        if bili_tags:
            tags = bili_tags
    tags = tags[:5]  # 抖音话题标签最多 5 个

    print("\n── 抖音上传信息 ──────────────────────────────────", flush=True)
    print(f"  视频:   {video_path}", flush=True)
    print(f"  标题:   {title}", flush=True)
    print(f"  文案:   {desc[:80]}{'…' if len(desc) > 80 else ''}", flush=True)
    print(f"  标签:   {' '.join('#'+t for t in tags[:5])}", flush=True)
    print(f"  封面:   {cover_path or '（跳过）'}", flush=True)
    print(f"  发布:   {'定时 ' + publish_at if publish_at else '立即发布'}", flush=True)
    print("────────────────────────────────────────────────\n", flush=True)

    if dry_run:
        print("dry-run 模式，不实际上传。", flush=True)
        return {"dry_run": True, "title": title, "desc": desc}

    account_file = cookie_path(project_root)
    if not account_file.is_file():
        raise FileNotFoundError(
            f"未找到 Cookie: {account_file}\n请先运行: python3 scripts/upload_douyin.py --auth-only"
        )

    video_path = video_path.resolve()
    if not video_path.is_file():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # 竖封面：优先用 cover_path 同名的 -douyin.jpg，没有则自动生成
    portrait_cover: Path | None = None
    if cover_path and cover_path.is_file():
        douyin_cover = cover_path.with_name(
            cover_path.stem.replace("-cover", "-cover-douyin") + cover_path.suffix
        )
        if not douyin_cover.is_file():
            # 从 storyboard 自动生成竖封面
            try:
                import re as _re
                m = _re.search(r"ch(\d+)", cover_path.stem)
                if m:
                    ch = int(m.group(1))
                    from scripts.make_chapter_cover import make_cover as _make_cover
                    douyin_cover = _make_cover(ch, project_root=project_root, vertical=True)
                    print(f"竖封面已生成: {douyin_cover}", flush=True)
            except Exception as exc:
                print(f"⚠️  竖封面生成失败: {exc}，跳过", flush=True)
                douyin_cover = None
        portrait_cover = douyin_cover if douyin_cover and douyin_cover.is_file() else None

    return asyncio.run(_upload_async(
        video_path=video_path,
        title=title,
        tags=tags,
        desc=desc,
        account_file=account_file,
        cover_path=cover_path,
        portrait_cover_path=portrait_cover,
        publish_at=publish_at,
        playlist=cfg.playlist or "",
    ))
