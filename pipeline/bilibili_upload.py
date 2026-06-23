"""B 站投稿：元数据生成、导出包、可选 bilibili-api 上传。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .models import BilibiliConfig, Storyboard
from .youtube_upload import build_timestamps, resolve_output_video

BILIBILI_DESC_MAX = 2000
BILIBILI_TITLE_MAX = 80
BILIBILI_TAG_MAX = 10


def credential_path(project_root: Path) -> Path:
    return project_root / "credentials" / "bilibili_credential.json"


def _default_tags(storyboard: Storyboard, cfg: BilibiliConfig) -> list[str]:
    if cfg.tags:
        return [t.strip() for t in cfg.tags if t.strip()]
    return [t.strip() for t in storyboard.youtube.tags if t.strip()]


def prepare_bilibili_cover(
    src: Path,
    project_root: Path,
    *,
    max_bytes: int = 200_000,
    max_side: int = 1146,
) -> Path:
    """压缩封面为 JPEG（B 站 cover API 用 data:image/jpeg;base64，须控制在约 200KB 内）。"""
    import io

    from PIL import Image

    src = src.resolve()
    cache_dir = project_root / ".work" / "bilibili-cover"
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{src.stem}_bili_cover.jpg"
    if (
        out.is_file()
        and out.stat().st_mtime >= src.stat().st_mtime
        and out.stat().st_size <= max_bytes
    ):
        return out

    img = Image.open(src).convert("RGB")
    w, h = img.size
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    for quality in (88, 82, 75, 68, 60, 52, 45):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        if buf.tell() <= max_bytes:
            out.write_bytes(buf.getvalue())
            return out

    img.save(out, format="JPEG", quality=40, optimize=True)
    return out


def _reset_bilibili_http_sessions() -> None:
    """修改 timeout 后清空已缓存的 httpx 会话（否则会沿用默认短超时）。"""
    from bilibili_api.utils import network as net

    name = net.selected_client
    if not name:
        return
    net.session_pool[name] = {}
    net.lazy_settings[name] = {}


def configure_bilibili_http(*, timeout_sec: float = 180.0) -> str:
    """配置 bilibili-api HTTP 客户端（默认 curl_cffi，与库自带行为一致）。"""
    import os

    from bilibili_api import get_registered_clients, select_client
    from bilibili_api.utils.network import request_settings

    order: list[str] = []
    pref = os.environ.get("BILIBILI_HTTP_CLIENT", "").strip()
    if pref:
        order.append(pref)
    # httpx 在扫码轮询 passport API 时易 ReadTimeout，故放最后
    # 视频分片：curl_cffi 已验证可用；封面上传单独走 aiohttp
    order.extend(["curl_cffi", "aiohttp", "httpx"])

    chosen = ""
    for name in order:
        if name in get_registered_clients():
            select_client(name)
            chosen = name
            break
    if not chosen:
        raise RuntimeError(
            "未找到可用的 bilibili-api HTTP 客户端，请安装: pip install httpx"
        )

    proxy = os.environ.get("BILIBILI_PROXY", "").strip()
    request_settings.set_proxy(proxy)
    request_settings.set("trust_env", not bool(proxy))
    request_settings.set_timeout(timeout_sec)
    _reset_bilibili_http_sessions()
    return chosen


async def upload_cover_jpeg_file(cover_path: str, credential) -> str:
    """绕过 bilibili-api 的 PNG 转码（会把 JPEG 撑大导致 Broken pipe）。"""
    import asyncio
    import base64

    from bilibili_api.utils.network import Api
    from bilibili_api.utils.utils import get_api

    credential.raise_for_no_bili_jct()
    raw = Path(cover_path).read_bytes()
    if len(raw) > 400_000:
        raise ValueError(
            f"封面 JPEG 仍过大 ({len(raw) // 1024} KB)，请换更小图片或降低 bilibili.cover_image 分辨率"
        )
    payload = {
        "cover": f"data:image/jpeg;base64,{base64.b64encode(raw).decode('ascii')}"
    }
    api_def = get_api("video_uploader")["cover_up"]
    last_exc: Exception | None = None
    for attempt in range(1, 6):
        try:
            configure_bilibili_http(timeout_sec=90.0)
            # 封面上传 aiohttp 往往比 curl_cffi 稳
            from bilibili_api import get_registered_clients, select_client

            if "aiohttp" in get_registered_clients():
                select_client("aiohttp")
                _reset_bilibili_http_sessions()
            result = await Api(**api_def, credential=credential).update_data(**payload).result
            return result["url"]
        except Exception as exc:
            last_exc = exc
            if not _is_transient_network_error(exc) or attempt >= 5:
                break
            print(f"  封面上传重试 ({attempt}/5)…", flush=True)
            await asyncio.sleep(2 * attempt)
    raise RuntimeError(f"封面上传失败: {last_exc!r}") from last_exc


def _patch_bilibili_cover_upload(cover_url: str) -> None:
    """视频传完后 submit 需要 cover_url；此处直接返回已上传的 URL。"""
    import bilibili_api.video_uploader as vu

    async def _patched(*args, cover=None, credential=None, **kwargs):
        return cover_url

    vu.upload_cover = _patched


def _is_transient_network_error(exc: BaseException) -> bool:
    name = type(exc).__name__
    if "Timeout" in name or "timeout" in str(exc).lower():
        return True
    if "Connect" in name or "connection" in str(exc).lower():
        return True
    return False


def _preflight_bilibili_connectivity() -> None:
    """TCP 探测上传域名（HTTP 412 等不代表网络不通）。"""
    import socket

    hosts = ("member.bilibili.com", "api.bilibili.com")
    for host in hosts:
        try:
            with socket.create_connection((host, 443), timeout=8):
                pass
        except OSError as exc:
            raise RuntimeError(
                f"无法连接 {host}:443。\n"
                "常见原因：全局 VPN、终端代理未清（unset HTTPS_PROXY）。\n"
                "传 B 站时请直连国内，或暂时关闭 VPN。\n"
                f"原始错误: {exc!r}"
            ) from exc


def _clear_proxy_for_bilibili() -> dict[str, str]:
    """仅当 BILIBILI_CLEAR_PROXY=1 时清除终端代理（默认不动用户网络环境）。"""
    import os

    if os.environ.get("BILIBILI_CLEAR_PROXY", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        return {}

    saved: dict[str, str] = {}
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "http_proxy",
        "https_proxy",
        "ALL_PROXY",
        "all_proxy",
    ):
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    return saved


def _restore_proxy(saved: dict[str, str]) -> None:
    import os

    if saved:
        os.environ.update(saved)


def _chapter_from_storyboard(storyboard: Storyboard) -> int | None:
    fn = storyboard.output.filename or ""
    m = re.search(r"ch(\d+)", fn, re.I)
    return int(m.group(1)) if m else None


def _workdir_scene_cover(ch: int, project_root: Path) -> Path | None:
    seg = project_root / f"output/ch{ch:02d}-hybrid/commentary.work/segments"
    if not seg.is_dir():
        return None
    for name in ("intro-bridge_base.png", "open-1_base.png", "s1_base.png"):
        p = seg / name
        if p.is_file():
            return p.resolve()
    return None


def _chapter_asset_cover(ch: int, project_root: Path) -> Path | None:
    d = project_root / "assets" / "DaoDeJing"
    if not d.is_dir():
        return None
    pat = re.compile(rf"-\s*Ch{ch}\.", re.I)
    for p in sorted(d.iterdir()):
        if pat.search(p.name) and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            return p.resolve()
    return None


def resolve_upload_cover(storyboard: Storyboard, project_root: Path, cfg: BilibiliConfig) -> Path:
    from .brand import COVER_OUTPUT_DIR
    from .series_config import chapter_from_path

    root = project_root.resolve()
    if cfg.cover_image.strip():
        p = Path(cfg.cover_image)
        if not p.is_absolute():
            p = root / p
        if p.is_file():
            return p.resolve()

    yt_thumb = (storyboard.youtube.thumbnail_image or "").strip()
    if yt_thumb:
        p = Path(yt_thumb)
        if not p.is_absolute():
            p = root / p
        if p.is_file():
            return p.resolve()

    cover_img = (storyboard.cover.image or "").strip()
    if cover_img:
        p = Path(cover_img)
        if not p.is_absolute():
            p = root / p
        if p.is_file():
            return p.resolve()

    ch = _chapter_from_storyboard(storyboard)
    if ch is None:
        ch = chapter_from_path(storyboard.output.filename or "")
    if ch is None:
        ch = chapter_from_path(storyboard.cover_image_rel())
    if ch is not None:
        series_cover = root / COVER_OUTPUT_DIR / f"daodejing-ch{ch:02d}-cover.jpg"
        if series_cover.is_file():
            return series_cover.resolve()

    cover_path = root / storyboard.cover_image_rel()
    if cover_path.is_file():
        return cover_path.resolve()
    for scene in storyboard.scenes:
        if scene.image:
            p = Path(scene.image)
            if not p.is_absolute():
                p = project_root / p
            if p.is_file():
                return p.resolve()
    ch = _chapter_from_storyboard(storyboard)
    if ch is not None:
        for resolver in (_workdir_scene_cover, _chapter_asset_cover):
            p = resolver(ch, project_root)
            if p is not None:
                return p
    fallback = project_root / "assets" / "placeholder.jpg"
    if fallback.is_file():
        return fallback.resolve()
    raise FileNotFoundError(
        "未找到 B 站封面图：在 storyboard.bilibili.cover_image 指定，或确保分镜含 image"
    )


def build_description(
    storyboard: Storyboard,
    *,
    audio_dir: Path | None = None,
    config: BilibiliConfig | None = None,
    time_offset_sec: float = 0.0,
) -> str:
    cfg = config or storyboard.bilibili or BilibiliConfig()
    parts: list[str] = []

    hook = (storyboard.cover.hook or "").strip()
    if hook:
        parts.append(hook)
        parts.append("")

    intro = (cfg.description_intro or storyboard.youtube.description_intro or "").strip()
    if intro:
        parts.append(intro)
        parts.append("")

    if cfg.reuse_youtube_timeline and audio_dir and audio_dir.is_dir():
        heading = (storyboard.youtube.timeline_heading or "📌 章节时间轴").strip()
        timestamps = build_timestamps(
            storyboard,
            audio_dir,
            config=storyboard.youtube,
            time_offset_sec=time_offset_sec,
        )
        if timestamps:
            parts.append(heading)
            parts.extend(timestamps)
            parts.append("")

    url = (cfg.channel_url or storyboard.youtube.channel_url or "").strip()
    if url and "bilibili" in url:
        parts.append(f"🔗 {url}")

    text = "\n".join(parts).strip()
    if len(text) > BILIBILI_DESC_MAX:
        text = text[: BILIBILI_DESC_MAX - 1] + "…"
    return text


def build_metadata(
    storyboard: Storyboard,
    *,
    project_root: Path,
    video_path: Path | None = None,
    config: BilibiliConfig | None = None,
    audio_dir: Path | None = None,
    time_offset_sec: float = 0.0,
) -> dict:
    root = project_root.resolve()
    cfg = config or storyboard.bilibili or BilibiliConfig()
    if audio_dir is None:
        audio_dir = root / "output" / "audio"
    title = storyboard.title.strip()[:BILIBILI_TITLE_MAX]
    tags = _default_tags(storyboard, cfg)[:BILIBILI_TAG_MAX]
    cover = resolve_upload_cover(storyboard, root, cfg)
    return {
        "video": str(video_path) if video_path else None,
        "title": title,
        "desc": build_description(
            storyboard,
            audio_dir=audio_dir,
            config=cfg,
            time_offset_sec=time_offset_sec,
        ),
        "tags": tags,
        "tid": cfg.tid,
        "tid_name": "社科·法律·心理" if cfg.tid == 124 else f"分区 {cfg.tid}",
        "copyright_original": cfg.copyright_original,
        "dynamic": (cfg.dynamic or storyboard.cover.hook or "").strip()[:233],
        "cover": str(cover),
        "no_reprint": cfg.no_reprint,
        "open_elec": cfg.open_elec,
    }


def export_metadata_package(
    storyboard: Storyboard,
    *,
    project_root: Path,
    video_path: Path,
    out_dir: Path | None = None,
) -> Path:
    """导出创作中心手动投稿用的标题/简介/标签/分区说明。"""
    root = project_root.resolve()
    out = (out_dir or root / "output" / "bilibili-upload").resolve()
    out.mkdir(parents=True, exist_ok=True)

    meta = build_metadata(storyboard, project_root=root, video_path=video_path)
    (out / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    paste = "\n".join(
        [
            "=== 标题（≤80 字）===",
            meta["title"],
            "",
            f"=== 分区 tid ===",
            f"{meta['tid']}（{meta['tid_name']}）",
            "",
            "=== 类型 ===",
            "自制" if meta["copyright_original"] else "转载",
            "",
            "=== 标签（最多 10 个）===",
            ", ".join(meta["tags"]),
            "",
            "=== 简介（≤2000 字）===",
            meta["desc"],
            "",
            "=== 粉丝动态（可选）===",
            meta["dynamic"] or "（留空或填一句推广）",
            "",
            f"=== 封面图（Studio 里上传）===",
            meta["cover"],
        ]
    )
    (out / "studio-paste.txt").write_text(paste, encoding="utf-8")

    readme = f"""观念黑盒 · B 站手动投稿包
================================

视频文件:
  {video_path.resolve()}

元数据:
  {out / "studio-paste.txt"}

封面:
  {meta["cover"]}

步骤（国内网络推荐）:
  1. 打开 https://member.bilibili.com/platform/upload/video/frame
  2. 上传 mp4，等待转码
  3. 从 studio-paste.txt 填写标题、分区、标签、简介
  4. 上传封面图，选择「自制」
  5. 提交审核

API 自动上传（需先扫码登录）:
  pip install bilibili-api-python
  python3 scripts/upload_bilibili.py --auth-only
  python3 scripts/upload_bilibili.py

说明:
  B 站服务器在国内，一般比 YouTube API 更稳定。
  bilibili-api 使用创作中心接口（非开放平台 OAuth），需 B 站账号 Cookie/扫码。
  官方「开放平台」上传需企业应用与签名，个人 UP 主通常用上述两种方式。
"""
    (out / "README.txt").write_text(readme, encoding="utf-8")
    return out


def load_credential(project_root: Path):
    from bilibili_api import Credential

    root = project_root.resolve()
    import os

    env_map = {
        "sessdata": os.environ.get("BILIBILI_SESSDATA", "").strip(),
        "bili_jct": os.environ.get("BILIBILI_BILI_JCT", "").strip(),
        "buvid3": os.environ.get("BILIBILI_BUVID3", "").strip(),
        "dedeuserid": os.environ.get("BILIBILI_DEDEUSERID", "").strip(),
    }
    if all(env_map.values()):
        return Credential(**env_map)

    path = credential_path(root)
    if not path.is_file():
        raise FileNotFoundError(
            f"未找到 B 站凭据: {path}\n"
            "请运行: python3 scripts/upload_bilibili.py --auth-only\n"
            "或设置环境变量 BILIBILI_SESSDATA / BILIBILI_BILI_JCT / BILIBILI_BUVID3"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    cred = Credential(
        sessdata=data.get("sessdata") or data.get("SESSDATA"),
        bili_jct=data.get("bili_jct"),
        buvid3=data.get("buvid3") or data.get("BUVID3"),
        dedeuserid=data.get("dedeuserid") or data.get("DedeUserID"),
        buvid4=data.get("buvid4"),
        ac_time_value=data.get("ac_time_value"),
        proxy=None,
    )
    return cred


def save_credential(project_root: Path, credential) -> Path:
    path = credential_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    cookies = credential.get_cookies()
    path.write_text(json.dumps(cookies, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


async def verify_credential_async(project_root: Path) -> dict:
    from bilibili_api import user

    cred = load_credential(project_root)
    uid = cred.dedeuserid
    if not uid:
        raise RuntimeError("凭据缺少 DedeUserID，请重新导入 Cookie 或扫码登录")
    info = await user.User(uid, cred).get_user_info()
    name = info.get("name") or info.get("uname") or uid
    return {"uid": uid, "name": name}


async def auth_with_qrcode(project_root: Path) -> Path:
    client = configure_bilibili_http(timeout_sec=60.0)
    print(f"HTTP 客户端: {client}", flush=True)
    saved_proxy = _clear_proxy_for_bilibili()
    try:
        return await _auth_with_qrcode_impl(project_root)
    finally:
        _restore_proxy(saved_proxy)


async def _auth_with_qrcode_impl(project_root: Path) -> Path:
    import asyncio
    import time

    from bilibili_api.login_v2 import QrCodeLogin, QrCodeLoginEvents

    qr = QrCodeLogin()
    await qr.generate_qrcode()
    print(qr.get_qrcode_terminal())
    print("请使用 B 站 App 扫码并确认登录…", flush=True)
    deadline = time.time() + 180
    poll_errors = 0
    while time.time() < deadline:
        try:
            state = await qr.check_state()
            poll_errors = 0
        except Exception as exc:
            if not _is_transient_network_error(exc):
                raise
            poll_errors += 1
            if poll_errors > 20:
                raise RuntimeError(
                    "扫码状态轮询多次超时，请检查网络（关全局 VPN / unset 代理）后重试 --auth-only"
                ) from exc
            print(f"  网络抖动，继续等待扫码 ({poll_errors})…", flush=True)
            await asyncio.sleep(3)
            continue
        if state == QrCodeLoginEvents.DONE:
            break
        if state == QrCodeLoginEvents.TIMEOUT:
            raise RuntimeError("二维码已过期，请重新运行: python3 scripts/upload_bilibili.py --auth-only")
        await asyncio.sleep(2)
    else:
        raise RuntimeError("扫码超时（3 分钟），请重新运行: python3 scripts/upload_bilibili.py --auth-only")
    cred = qr.get_credential()
    path = save_credential(project_root, cred)
    print(f"B 站凭据已保存: {path}")
    return path


async def upload_video_async(
    video_path: Path,
    storyboard: Storyboard,
    *,
    project_root: Path,
    skip_credential_check: bool = False,
    audio_dir: Path | None = None,
    time_offset_sec: float = 0.0,
    publish_at_unix: int | None = None,
) -> dict:
    root = project_root.resolve()
    video_path = video_path.resolve()
    cfg = storyboard.bilibili or BilibiliConfig()

    client = configure_bilibili_http(timeout_sec=300.0)
    print(f"HTTP 客户端（视频）: {client}", flush=True)

    saved_proxy = _clear_proxy_for_bilibili()
    if saved_proxy:
        print("已按 BILIBILI_CLEAR_PROXY=1 临时关闭终端代理", flush=True)
    try:
        if not skip_credential_check:
            print("验证凭据…", flush=True)
            import asyncio

            try:
                who = await asyncio.wait_for(verify_credential_async(root), timeout=20.0)
                print(f"凭据有效: {who['name']} (uid {who['uid']})", flush=True)
            except TimeoutError:
                print("凭据验证超时，继续上传（可先运行 --check-credential）", flush=True)
        _preflight_bilibili_connectivity()
        print("网络预检通过", flush=True)
        return await _upload_video_async_impl(
            video_path,
            storyboard,
            project_root=root,
            cfg=cfg,
            audio_dir=audio_dir,
            time_offset_sec=time_offset_sec,
            publish_at_unix=publish_at_unix,
        )
    finally:
        _restore_proxy(saved_proxy)


async def _upload_video_async_impl(
    video_path: Path,
    storyboard: Storyboard,
    *,
    project_root: Path,
    cfg: BilibiliConfig,
    audio_dir: Path | None = None,
    time_offset_sec: float = 0.0,
    publish_at_unix: int | None = None,
) -> dict:
    from bilibili_api import video_uploader

    root = project_root.resolve()
    credential = load_credential(root)
    meta_dict = build_metadata(
        storyboard,
        project_root=root,
        video_path=video_path,
        config=cfg,
        audio_dir=audio_dir,
        time_offset_sec=time_offset_sec,
    )
    cover_src = Path(meta_dict["cover"])
    print("压缩封面…", flush=True)
    cover_file = prepare_bilibili_cover(cover_src, root)
    cover_path = str(cover_file)
    src_mb = cover_src.stat().st_size / (1024 * 1024)
    cov_kb = cover_file.stat().st_size / 1024
    print(
        f"封面: {cover_src.name} ({src_mb:.1f} MB) → {cover_file.name} ({cov_kb:.0f} KB)",
        flush=True,
    )

    print("上传封面（JPEG，约 10–40 秒）…", flush=True)
    cover_url = await upload_cover_jpeg_file(cover_path, credential)
    print(f"封面完成 ✓", flush=True)

    configure_bilibili_http(timeout_sec=300.0)

    vu_meta = video_uploader.VideoMeta(
        tid=meta_dict["tid"],
        title=meta_dict["title"],
        desc=meta_dict["desc"],
        cover=cover_path,
        tags=meta_dict["tags"],
        original=meta_dict["copyright_original"],
        source=cfg.source or None,
        no_reprint=cfg.no_reprint,
        open_elec=cfg.open_elec,
        dynamic=meta_dict["dynamic"] or None,
        delay_time=publish_at_unix,
    )
    page = video_uploader.VideoUploaderPage(
        path=str(video_path),
        title=meta_dict["title"],
        description="",
    )
    _patch_bilibili_cover_upload(cover_url)

    uploader = video_uploader.VideoUploader([page], vu_meta, credential)

    chunk_done = 0

    @uploader.on("__ALL__")
    async def on_event(data):
        nonlocal chunk_done
        if isinstance(data, str):
            print(f"  · {data}", flush=True)
            return
        if not isinstance(data, dict):
            return
        if "err" in data:
            print(f"  · 错误: {data['err']}", flush=True)
            return
        label = data.get("text") or data.get("event") or data.get("name")
        if label:
            print(f"  · {label}", flush=True)
        if "chunk" in str(label or "").lower() or data.get("chunk"):
            chunk_done += 1

    size_mb = video_path.stat().st_size / (1024 * 1024)
    print(f"上传视频（{size_mb:.1f} MB，约 5–15 分钟，见下方 PRE_CHUNK / AFTER_CHUNK）…", flush=True)
    result = await uploader.start()
    bvid = ""
    aid = ""
    if isinstance(result, dict):
        bvid = result.get("bvid", "") or ""
        aid = str(result.get("aid", "") or "")
    url = f"https://www.bilibili.com/video/{bvid}" if bvid else ""
    out = {"bvid": bvid, "aid": aid, "url": url, "result": result}
    series_id = resolve_bilibili_series_id(cfg.series_id, root)
    if series_id and aid:
        try:
            await add_videos_to_bilibili_series(series_id, [int(aid)], root)
        except Exception as exc:
            print(f"警告：加入 B 站视频列表失败: {exc}", flush=True)
    return out


def _video_editor_meta(meta_dict: dict) -> dict:
    return {
        "title": meta_dict["title"],
        "copyright": 1 if meta_dict["copyright_original"] else 2,
        "tag": ",".join(meta_dict["tags"]),
        "desc_format_id": 0,
        "desc": meta_dict["desc"],
        "dynamic": meta_dict.get("dynamic") or "",
        "interactive": 0,
        "new_web_edit": 1,
        "act_reserve_create": 0,
        "handle_staff": False,
        "topic_grey": 1,
        "no_reprint": 1 if meta_dict.get("no_reprint", True) else 0,
        "subtitles": {"lan": "", "open": 0},
        "web_os": 2,
    }


def _member_session_headers() -> dict[str, str]:
    return {
        "referer": "https://member.bilibili.com/platform/upload/video/frame",
        "origin": "https://member.bilibili.com",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    }


def _member_requests_session(credential) -> "requests.Session":
    """创作中心 requests 会话：补 buvid3、去掉空 Cookie 字段。"""
    import requests as req_lib

    session = req_lib.Session()
    session.headers.update(_member_session_headers())
    try:
        session.get("https://www.bilibili.com/", timeout=(10, 25))
    except Exception:
        pass
    cookies = {k: v for k, v in credential.get_cookies().items() if v}
    session.cookies.update(cookies)
    return session


BILIBILI_CAPTCHA_CODES = frozenset({340022, 601})


class BilibiliCaptchaRequiredError(RuntimeError):
    """B 站风控要求验证码（340022 / 601）。"""


def _fetch_archive_view_requests(credential, bvid: str) -> dict:
    """创作中心稿件详情（requests，比 bilibili-api 客户端更不易 412）。"""
    import time

    bvid = bvid.strip()
    session = _member_requests_session(credential)
    last_exc: Exception | None = None
    for attempt in range(1, 5):
        try:
            resp = session.get(
                "https://member.bilibili.com/x/vupre/web/archive/view",
                params={"topic_grey": 1, "bvid": bvid},
                timeout=(30, 180),
            )
            if resp.status_code != 200 or "412" in resp.text[:300]:
                raise RuntimeError(
                    f"archive/view 失败 HTTP {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
            code = data.get("code")
            if code in BILIBILI_CAPTCHA_CODES:
                raise BilibiliCaptchaRequiredError(data)
            if code != 0:
                raise RuntimeError(f"archive/view 失败: {data}")
            return data["data"]
        except BilibiliCaptchaRequiredError:
            raise
        except Exception as exc:
            last_exc = exc
            if attempt >= 4:
                break
            wait = 5 * attempt
            print(f"  archive/view 重试 ({attempt}/4)，{wait}s…", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"archive/view 失败: {last_exc!r}") from last_exc


def _resolve_bvid_for_edit(*, bvid: str = "", aid: int = 0) -> str:
    """aid 或 bvid → 创作中心 edit 用的 bvid。"""
    bvid = bvid.strip()
    if bvid:
        return bvid
    if aid <= 0:
        raise ValueError("aid 或 bvid 至少提供一个")
    import requests as req_lib

    resp = req_lib.get(
        "https://api.bilibili.com/x/web-interface/view",
        params={"aid": aid},
        timeout=(10, 30),
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"aid→bvid 失败 aid={aid}: {data}")
    bvid = str(data.get("data", {}).get("bvid", "")).strip()
    if not bvid:
        raise RuntimeError(f"aid→bvid 失败 aid={aid}: 无 bvid")
    return bvid


def _archive_int(value, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, dict):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _build_web_edit_body_from_view(
    view: dict,
    credential,
    *,
    cover: str | None = None,
    is_only_self: int | None = None,
) -> dict:
    """从 archive/view 构造 vu/web/edit 正文（须带齐字段，仅改 is_only_self 时也如此）。"""
    archive = view["archive"]
    videos = view["videos"]
    cover_val = cover if cover is not None else (archive.get("cover") or "")
    body = {
        "aid": archive["aid"],
        "tid": archive["tid"],
        "cover": cover_val,
        "title": archive["title"],
        "copyright": archive["copyright"],
        "tag": archive["tag"],
        "desc": archive["desc"],
        "desc_format_id": archive.get("desc_format_id", 0),
        "dynamic": archive.get("dynamic") or "",
        "interactive": _archive_int(archive.get("interactive"), 0),
        "no_reprint": _archive_int(archive.get("no_reprint"), 1),
        "recreate": _archive_int(archive.get("recreate"), -1),
        "no_disturbance": _archive_int(archive.get("no_disturbance"), 0),
        "new_web_edit": 1,
        "act_reserve_create": 0,
        "handle_staff": False,
        "topic_grey": 1,
        "mission_id": _archive_int(archive.get("mission_id"), 0),
        "is_360": _archive_int(archive.get("is_360"), -1),
        "subtitles": {"lan": "", "open": 0},
        "web_os": 2,
        "csrf": credential.bili_jct,
        "videos": [
            {
                "title": part["title"],
                "desc": part.get("desc") or "",
                "filename": part["filename"],
                "cid": part["cid"],
            }
            for part in videos
        ],
    }
    if is_only_self is not None:
        body["is_only_self"] = int(is_only_self)
    else:
        body["is_only_self"] = int(
            archive.get("is_only_self") or archive.get("no_public") or 0
        )
    return body


def _post_web_edit_via_requests(credential, body: dict) -> dict:
    """创作中心 edit：requests + 浏览器头（bilibili-api 客户端易触发 412）。"""
    import time

    import requests as req_lib

    headers = {
        **_member_session_headers(),
        "content-type": "application/json;charset=UTF-8",
    }
    last_exc: Exception | None = None
    for attempt in range(1, 5):
        try:
            resp = req_lib.post(
                "https://member.bilibili.com/x/vu/web/edit",
                params={"csrf": credential.bili_jct, "t": int(time.time())},
                headers=headers,
                cookies=credential.get_cookies(),
                json=body,
                timeout=(20, 120),
            )
            if resp.status_code != 200 or "412" in resp.text[:300]:
                raise RuntimeError(
                    f"B 站 edit 失败 HTTP {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
            code = data.get("code")
            if code in BILIBILI_CAPTCHA_CODES:
                raise BilibiliCaptchaRequiredError(data)
            if code != 0:
                raise RuntimeError(f"B 站 edit 失败: {data}")
            return data.get("data") or {}
        except BilibiliCaptchaRequiredError:
            raise
        except Exception as exc:
            last_exc = exc
            if attempt >= 4:
                break
            wait = 8 * attempt
            print(f"  edit 重试 ({attempt}/4)，{wait}s…", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"B 站 edit 失败: {last_exc!r}") from last_exc


def _edit_cover_via_requests(credential, bvid: str, body: dict) -> dict:
    return _post_web_edit_via_requests(credential, body)


def delete_archive_bilibili(
    project_root: Path,
    *,
    bvid: str | None = None,
    aid: int | None = None,
    max_retries: int = 4,
) -> dict:
    """删除 B 站稿件（创作中心接口，需 SESSDATA + bili_jct）。"""
    import time

    import requests as req_lib

    root = project_root.resolve()
    credential = load_credential(root)
    credential.raise_for_no_bili_jct()

    bvid = (bvid or "").strip()
    if aid is None:
        if not bvid:
            raise ValueError("需要 bvid 或 aid")
        view = _fetch_archive_view_requests(credential, bvid)
        aid = int(view["archive"]["aid"])
        title = view["archive"].get("title") or bvid
    else:
        title = bvid or f"aid={aid}"

    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = req_lib.post(
                "https://member.bilibili.com/x/web/archive/delete",
                data={"aid": aid, "csrf": credential.bili_jct},
                cookies=credential.get_cookies(),
                headers=_member_session_headers(),
                timeout=(20, 120),
            )
            if resp.status_code != 200 or "412" in resp.text[:300]:
                raise RuntimeError(
                    f"B 站删除失败 HTTP {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"B 站删除失败: {data}")
            print(f"已删除 B 站稿件: {title} ({bvid or aid})", flush=True)
            return {"aid": aid, "bvid": bvid, "response": data}
        except Exception as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            wait = 8 * attempt
            print(f"  删除重试 ({attempt}/{max_retries})，{wait}s…", flush=True)
            time.sleep(wait)
    raise RuntimeError(
        f"B 站删除失败 {bvid or aid}: {last_exc!r}"
    ) from last_exc


async def update_video_cover_async(
    bvid: str,
    cover_path: Path,
    storyboard: Storyboard,
    *,
    project_root: Path,
) -> dict:
    """已投稿视频仅更换封面（上传封面图 + 保留原稿件元数据 edit）。"""
    root = project_root.resolve()
    bvid = bvid.strip()
    if not bvid:
        raise ValueError("bvid 不能为空")

    saved_proxy = _clear_proxy_for_bilibili()
    if saved_proxy:
        print("已按 BILIBILI_CLEAR_PROXY=1 临时关闭终端代理", flush=True)
    try:
        configure_bilibili_http(timeout_sec=120.0)
        credential = load_credential(root)
        cover_file = prepare_bilibili_cover(cover_path.resolve(), root)
        print(f"B 站换封面 {bvid} ← {cover_file.name}", flush=True)
        cover_url = await upload_cover_jpeg_file(str(cover_file), credential)

        old = _fetch_archive_view_requests(credential, bvid)
        body = _build_web_edit_body_from_view(old, credential, cover=cover_url)

        result = _edit_cover_via_requests(credential, bvid, body)
        return {"bvid": bvid, "cover": cover_url, "result": result}
    finally:
        _restore_proxy(saved_proxy)


def update_video_cover(
    bvid: str,
    cover_path: Path,
    storyboard: Storyboard,
    *,
    project_root: Path,
) -> dict:
    from bilibili_api import sync

    return sync(
        update_video_cover_async(
            bvid, cover_path, storyboard, project_root=project_root
        )
    )


def _delete_archive_via_requests(credential, aid: int) -> dict:
    """创作中心删除稿件：requests + 浏览器头（aid + csrf）。"""
    import time

    session = _member_requests_session(credential)
    session.headers["referer"] = "https://member.bilibili.com/platform/upload/video/list"
    session.headers["content-type"] = "application/x-www-form-urlencoded"
    last_exc: Exception | None = None
    for attempt in range(1, 5):
        try:
            resp = session.post(
                "https://member.bilibili.com/x/web/archive/delete",
                data={"aid": int(aid), "csrf": credential.bili_jct},
                timeout=(20, 120),
            )
            if resp.status_code != 200 or "412" in resp.text[:300]:
                raise RuntimeError(
                    f"B 站 delete 失败 HTTP {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
            code = data.get("code")
            if code in BILIBILI_CAPTCHA_CODES:
                raise BilibiliCaptchaRequiredError(data)
            if code != 0:
                raise RuntimeError(f"B 站 delete 失败: {data}")
            return data.get("data") or {}
        except BilibiliCaptchaRequiredError:
            raise
        except Exception as exc:
            last_exc = exc
            if attempt >= 4:
                break
            wait = 8 * attempt
            print(f"  delete 重试 ({attempt}/4)，{wait}s…", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"B 站 delete 失败 aid={aid}: {last_exc!r}") from last_exc


def delete_video(
    project_root: Path,
    *,
    aid: int | None = None,
    bvid: str | None = None,
) -> bool:
    """删除 B 站稿件（创作中心 archive/delete，需 aid）。"""
    root = project_root.resolve()
    aid_val = int(aid or 0)
    bvid_val = (bvid or "").strip()

    saved_proxy = _clear_proxy_for_bilibili()
    if saved_proxy:
        print("已按 BILIBILI_CLEAR_PROXY=1 临时关闭终端代理", flush=True)
    try:
        credential = load_credential(root)
        if aid_val <= 0 and bvid_val:
            archive = _fetch_archive_view_requests(credential, bvid_val)
            aid_val = int(archive["archive"]["aid"])
        if aid_val <= 0:
            raise ValueError("aid 或 bvid 至少提供一个")

        label = bvid_val or f"aid={aid_val}"
        print(f"删除 B 站稿件 {label} (aid={aid_val})…", flush=True)
        _delete_archive_via_requests(credential, aid_val)
        print(f"已删除 B 站稿件: {label}", flush=True)
        return True
    finally:
        _restore_proxy(saved_proxy)


def set_archive_self_only(
    project_root: Path,
    *,
    aid: int | None = None,
    bvid: str | None = None,
    is_only_self: int = 1,
) -> bool:
    """将已投稿视频设为仅自己可见（is_only_self=1）或公开（0）。"""
    root = project_root.resolve()
    aid_val = int(aid or 0)
    bvid_val = (bvid or "").strip()
    is_only_self = 1 if is_only_self else 0
    vis = "仅自己可见" if is_only_self else "公开"

    saved_proxy = _clear_proxy_for_bilibili()
    if saved_proxy:
        print("已按 BILIBILI_CLEAR_PROXY=1 临时关闭终端代理", flush=True)
    try:
        credential = load_credential(root)
        credential.raise_for_no_bili_jct()
        bvid_val = _resolve_bvid_for_edit(bvid=bvid_val, aid=aid_val)
        view = _fetch_archive_view_requests(credential, bvid_val)
        title = view["archive"].get("title") or bvid_val
        current = int(
            view["archive"].get("is_only_self")
            or view["archive"].get("no_public")
            or 0
        )
        if current == is_only_self:
            print(f"已是{vis}，跳过: {title} ({bvid_val})", flush=True)
            return True
        body = _build_web_edit_body_from_view(
            view, credential, is_only_self=is_only_self
        )
        print(f"设为{vis}: {title} ({bvid_val})…", flush=True)
        _post_web_edit_via_requests(credential, body)
        print(f"已设为{vis}: {title} ({bvid_val})", flush=True)
        return True
    finally:
        _restore_proxy(saved_proxy)


def resolve_bilibili_series_id(storyboard_series_id: int, project_root: Path) -> int:
    from .series_config import resolve_bilibili_series_id as _resolve

    return _resolve(storyboard_series_id, project_root)


async def create_bilibili_video_series(
    project_root: Path,
    name: str,
    *,
    description: str = "",
    keywords: list[str] | None = None,
) -> dict:
    """新建 B 站「视频列表」（旧版 series，可 API 自动加稿）。"""
    from bilibili_api.channel_series import create_channel_series

    name = name.strip()
    if not name:
        raise ValueError("视频列表名称不能为空")
    credential = load_credential(project_root)
    kws = keywords or ["道德经", "观念黑盒", "八十一讲"]
    result = await create_channel_series(
        name,
        aids=[],
        keywords=kws,
        description=(description or "").strip(),
        credential=credential,
    )
    series_id = int(result.get("series_id") or result.get("data", {}).get("series_id") or 0)
    if not series_id:
        # 部分返回嵌套在 data
        if isinstance(result.get("data"), dict):
            series_id = int(result["data"].get("series_id") or 0)
    if not series_id:
        raise RuntimeError(f"创建视频列表成功但未解析 series_id: {result!r}")
    print(f"已创建 B 站视频列表: {name}\n  series_id={series_id}", flush=True)
    return {"series_id": series_id, "result": result}


async def add_videos_to_bilibili_series(
    series_id: int,
    aids: list[int],
    project_root: Path,
) -> dict:
    """将稿件加入旧版「视频列表」（series_id）。"""
    from bilibili_api.channel_series import add_aids_to_series

    credential = load_credential(project_root)
    aids = [int(a) for a in aids if int(a) > 0]
    if not aids:
        return {}
    result = await add_aids_to_series(series_id, aids, credential)
    print(f"已加入 B 站视频列表 series_id={series_id}（{len(aids)} 个稿件）", flush=True)
    return result


def import_credential_from_cookies(
    project_root: Path,
    *,
    sessdata: str,
    bili_jct: str,
    buvid3: str = "",
    dedeuserid: str = "",
) -> Path:
    from bilibili_api import Credential

    cred = Credential(
        sessdata=sessdata.strip(),
        bili_jct=bili_jct.strip(),
        buvid3=buvid3.strip() or None,
        dedeuserid=dedeuserid.strip() or None,
    )
    path = save_credential(project_root, cred)
    print(f"已保存凭据: {path}")
    return path


def upload_video(
    video_path: Path,
    storyboard: Storyboard,
    *,
    project_root: Path,
    skip_credential_check: bool = False,
    audio_dir: Path | None = None,
    time_offset_sec: float = 0.0,
    publish_at_unix: int | None = None,
) -> dict:
    from bilibili_api import sync

    return sync(
        upload_video_async(
            video_path,
            storyboard,
            project_root=project_root,
            skip_credential_check=skip_credential_check,
            audio_dir=audio_dir,
            time_offset_sec=time_offset_sec,
            publish_at_unix=publish_at_unix,
        )
    )


def verify_credential(project_root: Path) -> dict:
    from bilibili_api import sync

    return sync(verify_credential_async(project_root))
