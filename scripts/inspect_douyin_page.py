import time
from playwright.sync_api import sync_playwright
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.douyin_upload import _make_context, UPLOAD_URL

project_root = Path(__file__).resolve().parents[1]
cookie = project_root / "credentials" / "douyin_cookie.json"
video = project_root / "output" / "daodejing-ch01-hybrid.mp4"

with sync_playwright() as p:
    ctx, browser = _make_context(p, project_root=project_root, headless=False, storage_state=cookie)
    page = ctx.new_page()
    page.goto(UPLOAD_URL, timeout=60000)
    page.wait_for_load_state("networkidle", timeout=15000)

    fi = page.query_selector("input[type=file]")
    if not fi:
        print("ERROR: 找不到 file input，URL:", page.url)
        ctx.close()
        exit(1)

    fi.set_input_files(str(video.resolve()))
    page.wait_for_url("**/post/video**", timeout=30000)
    page.wait_for_selector("input[placeholder*='填写作品标题']", timeout=30000)
    time.sleep(5)

    # 打印所有 file input
    fis = page.query_selector_all("input[type='file']")
    print(f"\n找到 {len(fis)} 个 file input:")
    for i, f in enumerate(fis):
        accept = f.evaluate("e => e.accept || ''")
        cls = f.evaluate("e => (e.className||'').substring(0,60)")
        print(f"  [{i}] accept={accept!r} class={cls!r}")

    page.screenshot(path=str(project_root / ".work" / "douyin_post_page.png"), full_page=True)
    print("\n截图: .work/douyin_post_page.png")
    ctx.close()
    if browser:
        browser.close()
