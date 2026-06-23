"""封面弹窗调试：上传视频后精确测试封面上传流程，严格按 social-auto-upload 逻辑。"""
import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COOKIE = PROJECT_ROOT / "credentials" / "douyin_cookie.json"
VIDEO = PROJECT_ROOT / "output" / "daodejing-ch01-hybrid.mp4"
COVER_H = PROJECT_ROOT / "assets" / "covers" / "daodejing-ch01-cover.jpg"
COVER_V = PROJECT_ROOT / "assets" / "covers" / "daodejing-ch01-cover-douyin.jpg"
WORK = PROJECT_ROOT / ".work"

async def main():
    from patchright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, channel="chrome",
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(storage_state=str(COOKIE))
        page = await ctx.new_page()

        # 进入上传页
        await page.goto("https://creator.douyin.com/creator-micro/content/upload",
                        wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=90000)
        await page.wait_for_selector("div[class^='container'] input", state="attached", timeout=60000)
        await page.locator("div[class^='container'] input").set_input_files(str(VIDEO))

        # 等跳转
        while True:
            for pattern in ["**/post/video?enter_from=publish_page", "**/publish?enter_from=publish_page"]:
                try:
                    await page.wait_for_url(pattern, timeout=2000)
                    print(f"已进入发布页: {page.url}")
                    break
                except Exception:
                    pass
            else:
                await asyncio.sleep(0.5)
                continue
            break

        # 等转码完成
        print("等待转码…")
        while True:
            count = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
            if count > 0:
                break
            await asyncio.sleep(2)
        print("转码完成")
        await asyncio.sleep(2)

        # ── 严格按 social-auto-upload 的 set_thumbnail 逻辑 ──────────
        # 1. 清 shepherd 浮层
        await page.evaluate(
            "() => document.querySelectorAll('.shepherd-element,.shepherd-modal-overlay-container').forEach(e=>e.remove())"
        )

        # 2. 点击「选择封面」
        await page.get_by_text("选择封面", exact=True).first.click(force=True)
        cover_locator_str = "div.dy-creator-content-modal"
        await page.wait_for_selector(cover_locator_str, timeout=20000)
        cover_locator = page.locator(cover_locator_str).first
        await page.wait_for_timeout(1500)

        # 截图：弹窗打开后
        await page.screenshot(path=str(WORK / "cover_modal_open.png"))
        print("截图: cover_modal_open.png")

        # 打印弹窗内所有 file input
        fis = await cover_locator.locator("input[type='file']").all()
        print(f"\n弹窗内 file input 数量: {len(fis)}")
        for i, fi in enumerate(fis):
            cls = await fi.evaluate("e => e.className || ''")
            accept = await fi.evaluate("e => e.accept || ''")
            print(f"  [{i}] cls={cls!r}  accept={accept!r}")

        # 3. 先上传横封面
        print("\n切换到横封面 tab…")
        try:
            await cover_locator.get_by_text("设置横封面", exact=True).first.click(timeout=3000)
            await page.wait_for_timeout(800)
            print("横封面 tab 已点击")
        except Exception as e:
            print(f"横封面 tab 点击失败: {e}")

        await page.screenshot(path=str(WORK / "cover_modal_landscape_tab.png"))
        print("截图: cover_modal_landscape_tab.png")

        # 打印每个 semi-upload-hidden-input 的父元素结构，找到横封面的那个
        fis_now = await cover_locator.locator("input.semi-upload-hidden-input").all()
        print(f"\n横封面 tab 下 semi-upload-hidden-input 数量: {len(fis_now)}")
        for i, fi in enumerate(fis_now):
            # 往上找 3 层父元素的 class
            parent_info = await fi.evaluate("""e => {
                let info = [];
                let node = e;
                for (let j = 0; j < 4; j++) {
                    node = node.parentElement;
                    if (!node) break;
                    info.push(node.className || '(no class)');
                }
                return info;
            }""")
            print(f"  [{i}] 父元素链: {parent_info}")

        # 试试每个都上传，看哪个生效
        print("\n尝试 nth(0) 上传横封面…")
        await cover_locator.locator("input.semi-upload-hidden-input").nth(0).set_input_files(str(COVER_H))
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(WORK / "cover_modal_try_nth0.png"))
        print("截图: cover_modal_try_nth0.png")

        # 4. 上传竖封面
        print("\n切换到竖封面 tab…")
        try:
            await cover_locator.get_by_text("设置竖封面", exact=True).first.click(timeout=3000)
            await page.wait_for_timeout(800)
            print("竖封面 tab 已点击")
        except Exception as e:
            print(f"竖封面 tab 点击失败: {e}，直接上传")

        await page.screenshot(path=str(WORK / "cover_modal_portrait_tab.png"))
        print("截图: cover_modal_portrait_tab.png")

        cover_upload = cover_locator.locator("input.semi-upload-hidden-input").nth(1)
        print(f"准备上传竖封面: {COVER_V}")
        await cover_upload.set_input_files(str(COVER_V))
        await page.wait_for_timeout(3000)

        await page.screenshot(path=str(WORK / "cover_modal_after_portrait.png"))
        print("截图: cover_modal_after_portrait.png")

        # 4. 点「完成」
        await cover_locator.get_by_role("button", name="完成", exact=True).first.click()
        await page.wait_for_selector("div.dy-creator-content-modal", state="hidden", timeout=20000)
        print("封面设置完成 ✓")

        await browser.close()

asyncio.run(main())
