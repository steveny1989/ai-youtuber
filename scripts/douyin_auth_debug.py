#!/usr/bin/env python3
"""抖音登录调试脚本——复用已有 Chrome 登录态保存 Cookie。"""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COOKIE_OUT = ROOT / "credentials" / "douyin_cookie.json"
COOKIE_OUT.parent.mkdir(parents=True, exist_ok=True)

print("启动 playwright...", flush=True)
from playwright.sync_api import sync_playwright

# macOS 下 Chrome 的用户数据目录
CHROME_USER_DATA = Path.home() / "Library/Application Support/Google/Chrome"

with sync_playwright() as p:
    print("启动浏览器（复用你的 Chrome 登录态）...", flush=True)
    exe = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    # 用你自己 Chrome 的 Default profile，这样直接带登录态
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(CHROME_USER_DATA),
        executable_path=exe,
        headless=False,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        viewport={"width": 1440, "height": 900},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
    )

    page = context.new_page()
    print("打开抖音创作者中心...", flush=True)
    page.goto("https://creator.douyin.com", timeout=60_000)

    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        pass

    url = page.url
    print(f"当前URL: {url}", flush=True)

    if "/login" in url or "passport" in url:
        print("\n⚠️  还未登录，请在浏览器里完成登录后按回车...", flush=True)
        input()
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass

    # 保存 storage state
    context.storage_state(path=str(COOKIE_OUT))
    print(f"\n✓ Cookie 已保存: {COOKIE_OUT}", flush=True)
    context.close()
