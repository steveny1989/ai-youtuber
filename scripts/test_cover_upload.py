"""单独测试封面上传流程，截图记录每一步。"""
import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COOKIE = PROJECT_ROOT / "credentials" / "douyin_cookie.json"
VIDEO = PROJECT_ROOT / "output" / "daodejing-ch01-hybrid.mp4"
COVER = PROJECT_ROOT / "assets" / "covers" / "daodejing-ch01-cover.jpg"
WORK = PROJECT_ROOT / ".work"

async def main():
    from patchright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome",
                                           args=["--no-sandbox"])
        ctx = await browser.new_context(storage_state=str(COOKIE))
        page = await ctx.new_page()

        # 进入上传页
        await page.goto("https://creator.douyin.com/creator-micro/content/upload",
                        wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=90000)
        await page.wait_for_selector("div[class^='container'] input", state="attached", timeout=60000)
        await page.locator("div[class^='container'] input").set_input_files(str(VIDEO))

        # 等跳转到发布页
        while True:
            try:
                await page.wait_for_url("**/post/video?enter_from=publish_page", timeout=2000)
                break
            except Exception:
                try:
                    await page.wait_for_url("**/publish?enter_from=publish_page", timeout=2000)
                    break
                except Exception:
                    await asyncio.sleep(0.5)

        print("已进入发布页")

        # 等视频转码完成
        print("等待转码…")
        while True:
            count = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
            if count > 0:
                break
            await asyncio.sleep(2)
        print("转码完成")
        await asyncio.sleep(2)

        # 截图：点击前
        await page.screenshot(path=str(WORK / "cover_before_click.png"))
        print("截图1: cover_before_click.png")

        # 清浮层，点击选择封面
        await page.evaluate(
            "() => document.querySelectorAll('.shepherd-element,.shepherd-modal-overlay-container').forEach(e=>e.remove())"
        )
        cover_btn = page.get_by_text("选择封面", exact=True).first
        print(f"选择封面按钮可见: {await cover_btn.is_visible()}")
        await cover_btn.click(force=True)
        print("已点击选择封面")
        await asyncio.sleep(3)

        # 截图：点击后
        await page.screenshot(path=str(WORK / "cover_after_click.png"))
        print("截图2: cover_after_click.png")

        # 打印所有可见的 modal/dialog/cover 相关元素
        all_els = await page.query_selector_all("*")
        visible_modals = []
        for el in all_els:
            try:
                cls = await el.evaluate("e => e.className || ''")
                if not cls:
                    continue
                if any(k in cls for k in ['modal', 'dialog', 'Modal', 'cover', 'Cover', 'overlay']):
                    visible = await el.is_visible()
                    if visible:
                        tag = await el.evaluate("e => e.tagName")
                        visible_modals.append(f"{tag}  {cls[:100]}")
            except Exception:
                pass
        print(f"\n弹窗点击后可见的 modal/cover 元素 ({len(visible_modals)}):")
        for m in visible_modals:
            print(f"  {m}")

        # 打印所有 file input
        fis = await page.query_selector_all("input[type='file']")
        print(f"\n找到 {len(fis)} 个 file input:")
        for i, fi in enumerate(fis):
            accept = await fi.evaluate("e => e.accept || ''")
            cls = await fi.evaluate("e => e.className || ''")
            visible = await fi.is_visible()
            print(f"  [{i}] accept={accept!r}  cls={cls!r}  visible={visible}")

        await browser.close()

asyncio.run(main())
