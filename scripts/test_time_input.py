"""专门测试定时发布时间填写——不上传视频，直接打开已有草稿或发布页测试。"""
import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COOKIE = PROJECT_ROOT / "credentials" / "douyin_cookie.json"

# 目标时间
TARGET = "2026-06-25 20:00"

async def main():
    from patchright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome",
                                           args=["--no-sandbox"])
        ctx = await browser.new_context(storage_state=str(COOKIE))
        page = await ctx.new_page()

        # 直接去内容管理页，手动选一个草稿进去，或者直接测试时间选择器
        # 先访问上传页，不上传文件，只测试页面上的定时发布元素
        await page.goto("https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page",
                        timeout=30000)
        await asyncio.sleep(2)
        print(f"URL: {page.url}")

        # 找定时发布 radio
        radio = page.locator("[class^='radio']:has-text('定时发布')")
        count = await radio.count()
        print(f"定时发布 radio 数量: {count}")

        if count > 0:
            await radio.click()
            await asyncio.sleep(1)

            # 截图看当前状态
            await page.screenshot(path=str(PROJECT_ROOT / ".work" / "time_input_test.png"))
            print("截图: .work/time_input_test.png")

            # 找时间输入框
            inp = page.locator('.semi-input[placeholder="日期和时间"]').first
            print(f"时间框存在: {await inp.count() > 0}")

            if await inp.count() > 0:
                val = await inp.evaluate("e => e.value")
                print(f"当前值: {val!r}")

                # 方法1: triple_click + type
                await inp.click()
                await page.keyboard.press("Meta+A")
                await page.keyboard.type(TARGET)
                await asyncio.sleep(0.5)
                await page.keyboard.press("Enter")
                await asyncio.sleep(1)

                val_after = await inp.evaluate("e => e.value")
                print(f"方法1 填写后: {val_after!r}")

                await page.screenshot(path=str(PROJECT_ROOT / ".work" / "time_after_type.png"))
                print("截图: .work/time_after_type.png")

                # 如果方法1失败，尝试方法2: 先清空再逐字符
                if TARGET not in val_after:
                    print("方法1失败，尝试方法2: fill()")
                    await inp.click()
                    await inp.fill(TARGET)
                    await asyncio.sleep(0.5)
                    await page.keyboard.press("Tab")
                    await asyncio.sleep(1)
                    val_after2 = await inp.evaluate("e => e.value")
                    print(f"方法2 填写后: {val_after2!r}")

        # 保持浏览器开着让你看
        print("\n浏览器保持开着，请检查时间是否正确填入")
        await asyncio.sleep(30)
        await browser.close()

asyncio.run(main())
