"""截图发布页底部，找合集相关元素。"""
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

        # 全页截图
        await page.screenshot(path=str(PROJECT_ROOT / ".work" / "publish_full.png"), full_page=True)
        print("截图: .work/publish_full.png")

        # 找合集相关文字
        texts = ["合集", "添加合集", "添加到合集", "关联合集", "选择合集", "请选择合集"]
        for t in texts:
            els = await page.get_by_text(t, exact=False).all()
            if els:
                for el in els[:3]:
                    try:
                        txt = await el.inner_text()
                        tag = await el.evaluate("e => e.tagName")
                        cls = await el.evaluate("e => e.className or ''")
                        print(f"找到「{t}」: {tag} text={txt!r} cls={cls[:80]!r}")
                    except:
                        pass

        # 打印所有包含"集"字的可见元素
        print("\n所有包含「集」字的可见元素:")
        all_els = await page.query_selector_all("*")
        for el in all_els:
            try:
                txt = await el.evaluate("e => e.innerText.trim()")
                if "集" in txt and len(txt) < 30:
                    visible = await el.is_visible()
                    if visible:
                        tag = await el.evaluate("e => e.tagName")
                        cls = await el.evaluate("e => (e.className||'').substring(0,80)")
                        print(f"  {tag} text={txt!r}  cls={cls!r}")
            except:
                pass

        await browser.close()

asyncio.run(main())
