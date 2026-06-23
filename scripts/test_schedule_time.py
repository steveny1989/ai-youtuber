"""测试定时发布时间填写是否正确。"""
import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COOKIE = PROJECT_ROOT / "credentials" / "douyin_cookie.json"
VIDEO = PROJECT_ROOT / "output" / "daodejing-ch01-hybrid.mp4"
PUBLISH_AT = "2026-06-25 20:00"  # 测试用时间

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

        while True:
            for pat in ["**/post/video?enter_from=publish_page", "**/publish?enter_from=publish_page"]:
                try:
                    await page.wait_for_url(pat, timeout=2000)
                    break
                except Exception:
                    pass
            else:
                await asyncio.sleep(0.5)
                continue
            break

        # 等转码
        while True:
            count = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
            if count > 0:
                break
            await asyncio.sleep(2)
        await asyncio.sleep(2)

        # 截图：点定时发布前
        await page.screenshot(path=str(PROJECT_ROOT / ".work" / "schedule_before.png"))

        # 点「定时发布」radio
        radio = page.locator("[class^='radio']:has-text('定时发布')")
        await radio.click()
        await asyncio.sleep(1)

        # 截图：点击后，看时间输入框
        await page.screenshot(path=str(PROJECT_ROOT / ".work" / "schedule_radio_clicked.png"))
        print("截图: schedule_radio_clicked.png")

        # 打印时间输入框信息
        time_inputs = await page.query_selector_all('input[placeholder*="日期"], input[placeholder*="时间"], .semi-input[placeholder*="日期"]')
        print(f"找到 {len(time_inputs)} 个时间输入框:")
        for i, inp in enumerate(time_inputs):
            ph = await inp.evaluate("e => e.placeholder || ''")
            val = await inp.evaluate("e => e.value || ''")
            cls = await inp.evaluate("e => e.className || ''")
            print(f"  [{i}] ph={ph!r} val={val!r} cls={cls[:60]!r}")

        # 尝试填写时间
        time_input = page.locator('.semi-input[placeholder="日期和时间"]').first
        await time_input.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.type(PUBLISH_AT)
        await asyncio.sleep(1)
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)

        # 截图：填完后
        await page.screenshot(path=str(PROJECT_ROOT / ".work" / "schedule_filled.png"))
        print("截图: schedule_filled.png")

        # 读取填写后的值
        val_after = await time_input.evaluate("e => e.value || ''")
        print(f"填写后时间框值: {val_after!r}")

        await browser.close()

asyncio.run(main())
