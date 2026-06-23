"""点击「选择封面」后截图并打印弹窗 class，找到正确选择器。"""
import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COOKIE = PROJECT_ROOT / "credentials" / "douyin_cookie.json"
VIDEO = PROJECT_ROOT / "output" / "daodejing-ch01-hybrid.mp4"

async def main():
    from patchright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome",
                                           args=["--no-sandbox"])
        ctx = await browser.new_context(storage_state=str(COOKIE))
        page = await ctx.new_page()

        await page.goto("https://creator.douyin.com/creator-micro/content/upload",
                        wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=90000)
        await page.wait_for_selector("div[class^='container'] input", state="attached", timeout=60000)
        await page.locator("div[class^='container'] input").set_input_files(str(VIDEO))

        # 等跳转
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

        # 等视频上传完成
        print("等待视频上传完成…")
        while True:
            count = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
            if count > 0:
                break
            await asyncio.sleep(2)
        print("上传完成，点击选择封面…")

        await asyncio.sleep(1)
        await page.evaluate(
            "() => document.querySelectorAll('.shepherd-element,.shepherd-modal-overlay-container').forEach(e=>e.remove())"
        )
        await page.get_by_text("选择封面", exact=True).first.click(force=True)
        await asyncio.sleep(3)

        # 截图
        await page.screenshot(path=str(PROJECT_ROOT / ".work" / "cover_modal.png"), full_page=False)
        print("截图已保存: .work/cover_modal.png")

        # 打印所有可见的 modal/dialog class
        modals = await page.query_selector_all("[class*='modal'],[class*='dialog'],[class*='Modal'],[class*='cover']")
        print(f"\n找到 {len(modals)} 个弹窗相关元素:")
        for el in modals[:20]:
            cls = await el.evaluate("e => e.className")
            visible = await el.is_visible()
            if visible:
                print(f"  VISIBLE  {cls[:100]}")

        await browser.close()

asyncio.run(main())
