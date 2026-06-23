"""YouTube Data API v3：OAuth 上传与分镜元数据。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .ffmpeg_util import probe_duration_sec
from .models import Storyboard, YouTubeConfig, YouTubeTimelineMarker

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
SCOPES_MANAGE = ["https://www.googleapis.com/auth/youtube.force-ssl"]
SCOPES_MANAGE = ["https://www.googleapis.com/auth/youtube.force-ssl"]
YOUTUBE_UPLOAD_INIT_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def parse_publish_datetime(value: str) -> datetime:
    """解析 ISO8601 或常见本地时间字符串为 aware datetime。"""
    text = value.strip()
    if not text:
        raise ValueError("publish-at 不能为空")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        from zoneinfo import ZoneInfo

        dt = dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    return dt


def format_youtube_publish_at(dt: datetime) -> str:
    """YouTube API 要求 RFC3339 UTC。"""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def publish_at_unix(dt: datetime) -> int:
    return int(dt.timestamp())


def _credentials_dir(project_root: Path) -> Path:
    return project_root / "credentials"


def client_secrets_path(project_root: Path) -> Path:
    import os

    env = os.environ.get("YOUTUBE_CLIENT_SECRETS", "").strip()
    if env:
        p = Path(env)
        return p if p.is_absolute() else (project_root / p)
    return _credentials_dir(project_root) / "client_secret.json"


def token_path(project_root: Path) -> Path:
    return _credentials_dir(project_root) / "youtube_token.json"


def _format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _scene_duration_sec(scene, audio_dir: Path) -> float:
    ap = audio_dir / f"{scene.id}.mp3"
    if ap.is_file():
        return probe_duration_sec(ap) + (scene.pause_after_sec or 0)
    if scene.duration_sec:
        return scene.duration_sec + (scene.pause_after_sec or 0)
    return 0.0


def build_scene_start_times(
    storyboard: Storyboard,
    audio_dir: Path | None,
    *,
    time_offset_sec: float = 0.0,
) -> dict[str, float]:
    """各镜在成片中的起始秒数（与渲染顺序一致）。"""
    if not audio_dir or not audio_dir.is_dir():
        return {}
    starts: dict[str, float] = {}
    cursor = max(0.0, time_offset_sec)
    for scene in storyboard.all_scenes():
        starts[scene.id] = cursor
        cursor += _scene_duration_sec(scene, audio_dir)
    return starts


def _fallback_timestamp_label(scene, chapter_by_id: dict) -> str | None:
    explicit = (getattr(scene, "timestamp_label", None) or "").strip()
    if explicit:
        return explicit

    sid = scene.id
    if sid == "cover":
        return "片头 Hook"
    if sid == "intro-1":
        return "先导①"
    if sid == "intro-2":
        return "先导②"
    if sid == "open-1":
        return "论点一 · 地图不是道"
    if sid == "open-2":
        return "论点二 · 上善若水"
    if sid == "open-3":
        return "论点三 · 生产者的牢笼"
    if sid == "open-4":
        return "收官 · 地图脱钩练习"
    if sid == "protocol-1":
        return "五讲链 & 协议三步"
    if sid == "closing-1":
        return "收束 & 下期预告"
    if sid == "ending":
        return "片尾"

    if (scene.scene_type or "").strip().lower() == "chapter" and scene.chapter:
        ch = chapter_by_id.get(scene.chapter)
        return ch.label if ch else f"章节 {scene.chapter}"
    return None


def build_timestamps(
    storyboard: Storyboard,
    audio_dir: Path | None,
    *,
    config: YouTubeConfig | None = None,
    time_offset_sec: float = 0.0,
) -> list[str]:
    starts = build_scene_start_times(
        storyboard, audio_dir, time_offset_sec=time_offset_sec
    )
    if not starts:
        return []

    cfg = config or storyboard.youtube or YouTubeConfig()
    markers: list[YouTubeTimelineMarker] = list(cfg.timeline or [])
    lines: list[str] = []

    if markers:
        for marker in markers:
            if marker.scene not in starts:
                continue
            lines.append(f"{_format_timestamp(starts[marker.scene])} {marker.label}")
        return lines

    chapter_by_id = {c.id: c for c in storyboard.chapters}
    for scene in storyboard.all_scenes():
        label = _fallback_timestamp_label(scene, chapter_by_id)
        if not label:
            continue
        if scene.id not in starts:
            continue
        ap = (audio_dir / f"{scene.id}.mp3") if audio_dir else None
        if label and (ap is None or ap.is_file() or scene.duration_sec):
            lines.append(f"{_format_timestamp(starts[scene.id])} {label}")

    return lines


def build_description(
    storyboard: Storyboard,
    *,
    audio_dir: Path | None = None,
    config: YouTubeConfig | None = None,
    time_offset_sec: float = 0.0,
) -> str:
    cfg = config or storyboard.youtube or YouTubeConfig()
    parts: list[str] = []

    hook = (storyboard.cover.hook or "").strip()
    if hook:
        parts.append(hook)
        parts.append("")

    intro = (cfg.description_intro or "").strip()
    if not intro:
        for scene in storyboard.scenes:
            if scene.narration.strip():
                intro = scene.narration.strip()[:280]
                if len(scene.narration.strip()) > 280:
                    intro += "…"
                break
    if intro:
        parts.append(intro)
        parts.append("")

    timestamps = build_timestamps(
        storyboard, audio_dir, config=cfg, time_offset_sec=time_offset_sec
    )
    if timestamps:
        heading = (cfg.timeline_heading or "📌 章节时间轴").strip()
        parts.append(heading)
        parts.extend(timestamps)
        parts.append("")

    if storyboard.chapters and len(timestamps) < 5:
        parts.append("本期结构：")
        for ch in storyboard.chapters:
            parts.append(f"· {ch.label}")
        parts.append("")

    footer = (cfg.description_footer or "").strip()
    if not footer:
        footer_parts = []
        about_zh = (cfg.channel_about_zh or "").strip()
        if about_zh:
            footer_parts.append(about_zh)
        url = (cfg.channel_url or "").strip()
        if url:
            footer_parts.append(f"🔗 {url}")
        about_en = (cfg.channel_about_en or "").strip()
        if about_en:
            footer_parts.append(about_en)
        footer_parts.append(
            "#道德经 #老子 #观念黑盒 #TheBlackbox #人生哲学 #权力系统 #道德经五讲"
        )
        footer = "\n\n".join(footer_parts)
    if footer:
        parts.append("—")
        parts.append(footer)

    text = "\n".join(parts).strip()
    if len(text) > 4900:
        text = text[:4900] + "\n…"
    return text


def build_upload_body(
    storyboard: Storyboard,
    *,
    audio_dir: Path | None = None,
    config: YouTubeConfig | None = None,
    time_offset_sec: float = 0.0,
    publish_at: str | None = None,
) -> dict:
    cfg = config or storyboard.youtube

    title = storyboard.title.strip()[:100]
    description = build_description(
        storyboard,
        audio_dir=audio_dir,
        config=cfg,
        time_offset_sec=time_offset_sec,
    )
    tags = [t.strip() for t in cfg.tags if t.strip()][:30]

    snippet: dict = {
        "title": title,
        "description": description,
        "tags": tags,
        "categoryId": str(cfg.category_id),
        "defaultLanguage": cfg.default_language,
        "defaultAudioLanguage": cfg.default_language,
    }
    if cfg.recording_date:
        snippet["recordingDate"] = cfg.recording_date

    status = {
        "privacyStatus": cfg.privacy_status,
        "selfDeclaredMadeForKids": bool(cfg.made_for_kids),
    }
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at

    return {"snippet": snippet, "status": status}


def resolve_thumbnail_path(storyboard: Storyboard, project_root: Path) -> Path | None:
    """投稿缩略图路径：显式配置 → assets/covers/daodejing-chNN-cover.jpg → 场景图。"""
    from .brand import COVER_OUTPUT_DIR
    from .series_config import chapter_from_path

    root = project_root.resolve()
    explicit = (storyboard.youtube.thumbnail_image or "").strip()
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = root / p
        if p.is_file():
            return p.resolve()

    bili_cover = (storyboard.bilibili.cover_image or "").strip()
    if bili_cover:
        p = Path(bili_cover)
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

    ch = chapter_from_path(storyboard.output.filename or "")
    if ch is None:
        ch = chapter_from_path(storyboard.cover_image_rel())
    if ch is not None:
        series_cover = root / COVER_OUTPUT_DIR / f"daodejing-ch{ch:02d}-cover.jpg"
        if series_cover.is_file():
            return series_cover.resolve()

    from .bilibili_upload import resolve_upload_cover

    try:
        return resolve_upload_cover(storyboard, root, storyboard.bilibili)
    except FileNotFoundError:
        return None


def prepare_youtube_thumbnail(
    src: Path,
    project_root: Path,
    *,
    max_bytes: int = 2_000_000,
    max_side: int = 1280,
) -> Path:
    """压缩为 YouTube 缩略图（JPEG，≤2MB，长边 ≤1280）。"""
    import io

    from PIL import Image

    src = src.resolve()
    cache_dir = project_root / ".work" / "youtube-thumbnail"
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{src.stem}_yt_thumb.jpg"
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

    for quality in (90, 85, 78, 72, 65, 58, 50, 42):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        if buf.tell() <= max_bytes:
            out.write_bytes(buf.getvalue())
            return out

    img.save(out, format="JPEG", quality=35, optimize=True)
    return out


def upload_thumbnail_requests(
    session,
    video_id: str,
    thumbnail_path: Path,
    *,
    max_retries: int = 8,
    timeout_sec: int = 120,
) -> None:
    thumbnail_path = thumbnail_path.resolve()
    if not thumbnail_path.is_file():
        raise FileNotFoundError(f"缩略图不存在: {thumbnail_path}")

    suffix = thumbnail_path.suffix.lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
    }.get(suffix, "image/jpeg")
    data = thumbnail_path.read_bytes()
    if len(data) > 2_000_000:
        raise ValueError(
            f"缩略图过大 ({len(data) // 1024} KB)，YouTube 上限 2MB"
        )

    r = _request_with_retry(
        session,
        "POST",
        "https://www.googleapis.com/upload/youtube/v3/thumbnails/set",
        max_retries=max_retries,
        timeout_sec=timeout_sec,
        params={"videoId": video_id},
        headers={"Content-Type": mime},
        data=data,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(
            f"缩略图上传失败 HTTP {r.status_code}: {r.text[:500]}"
        )


def upload_thumbnail_googleapiclient(
    project_root: Path,
    video_id: str,
    thumbnail_path: Path,
    *,
    timeout_sec: int = 600,
) -> None:
    from googleapiclient.http import MediaFileUpload

    thumbnail_path = thumbnail_path.resolve()
    youtube = get_youtube_service(project_root, timeout_sec=timeout_sec)
    suffix = thumbnail_path.suffix.lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
    }.get(suffix, "image/jpeg")
    media = MediaFileUpload(str(thumbnail_path), mimetype=mime)
    youtube.thumbnails().set(videoId=video_id, media_body=media).execute()


def upload_thumbnail(
    video_id: str,
    thumbnail_path: Path,
    *,
    project_root: Path,
    method: str = "requests",
    timeout_sec: int = 600,
    max_retries: int = 8,
) -> None:
    if method == "googleapiclient":
        upload_thumbnail_googleapiclient(
            project_root, video_id, thumbnail_path, timeout_sec=timeout_sec
        )
        return
    session = get_authorized_session(project_root)
    upload_thumbnail_requests(
        session,
        video_id,
        thumbnail_path,
        max_retries=max_retries,
        timeout_sec=timeout_sec,
    )


def load_youtube_credentials(
    project_root: Path,
    *,
    scopes: list[str] | None = None,
):
    """加载或刷新 OAuth token（授权浏览器仅首次需要）。"""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    active_scopes = scopes or SCOPES
    root = project_root.resolve()
    secrets = client_secrets_path(root)
    if not secrets.is_file():
        raise FileNotFoundError(
            f"未找到 OAuth 客户端文件: {secrets}\n"
            "请在 Google Cloud Console 创建 OAuth 桌面客户端，下载 JSON 存为 "
            "credentials/client_secret.json，或设置 YOUTUBE_CLIENT_SECRETS"
        )

    tok = token_path(root)

    def _refresh_session():
        import requests as req_lib

        session = req_lib.Session()
        proxies = _proxy_from_env()
        if proxies:
            session.proxies.update(proxies)
        return Request(session=session)

    def _run_oauth_flow() -> Credentials:
        print(
            "请在浏览器完成 Google 授权（须为 @观念黑盒 频道账号）…",
            flush=True,
        )
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets), active_scopes)
        return flow.run_local_server(port=0, prompt="consent")

    def _save(creds: Credentials) -> Credentials:
        tok.parent.mkdir(parents=True, exist_ok=True)
        tok.write_text(creds.to_json(), encoding="utf-8")
        return creds

    def _scope_sufficient(creds: Credentials | None) -> bool:
        if not creds:
            return False
        granted = set(creds.scopes or [])
        return all(scope in granted for scope in active_scopes)

    creds = None
    if tok.is_file():
        creds = Credentials.from_authorized_user_file(str(tok), active_scopes)

    if creds and creds.valid and _scope_sufficient(creds):
        return creds

    if (
        creds
        and creds.expired
        and creds.refresh_token
        and _scope_sufficient(creds)
    ):
        try:
            creds.refresh(_refresh_session())
            return _save(creds)
        except RefreshError as exc:
            print(
                f"旧 token 已失效（{exc!s}），将打开浏览器重新授权…",
                flush=True,
            )
            tok.unlink(missing_ok=True)
            return _save(_run_oauth_flow())

    if creds and not _scope_sufficient(creds):
        print(
            f"当前 token 权限不足（需要 {active_scopes}），将重新授权…",
            flush=True,
        )
        tok.unlink(missing_ok=True)

    return _save(_run_oauth_flow())


def _proxy_from_env() -> dict[str, str] | None:
    import os

    proxy = (
        os.environ.get("YOUTUBE_PROXY", "").strip()
        or os.environ.get("HTTPS_PROXY", "").strip()
        or os.environ.get("https_proxy", "").strip()
    )
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def get_authorized_session(
    project_root: Path,
    *,
    scopes: list[str] | None = None,
):
    """requests 会话（默认上传方式，比 httplib2 更稳，支持 HTTPS_PROXY）。"""
    from google.auth.transport.requests import AuthorizedSession

    creds = load_youtube_credentials(project_root, scopes=scopes)
    session = AuthorizedSession(creds)
    proxies = _proxy_from_env()
    if proxies:
        session.proxies.update(proxies)
        print(f"使用网络代理: {proxies['https']}", flush=True)
    return session


def get_youtube_service(
    project_root: Path,
    *,
    timeout_sec: int = 600,
    scopes: list[str] | None = None,
):
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp
    from googleapiclient.discovery import build

    creds = load_youtube_credentials(project_root, scopes=scopes)
    http = httplib2.Http(timeout=timeout_sec)
    authed_http = AuthorizedHttp(creds, http=http)
    return build("youtube", "v3", http=authed_http)


def delete_video(
    project_root: Path,
    video_id: str,
    *,
    method: str = "requests",
    timeout_sec: int = 600,
    max_retries: int = 4,
) -> bool:
    """删除 YouTube 视频（需 youtube.force-ssl 权限）。"""
    video_id = video_id.strip()
    if not video_id:
        raise ValueError("video_id 不能为空")

    if method == "googleapiclient":
        youtube = get_youtube_service(
            project_root,
            timeout_sec=timeout_sec,
            scopes=SCOPES_MANAGE,
        )
        youtube.videos().delete(id=video_id).execute()
    else:
        import time

        session = get_authorized_session(project_root, scopes=SCOPES_MANAGE)
        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                resp = session.delete(
                    f"{YOUTUBE_API_BASE}/videos",
                    params={"id": video_id},
                    timeout=timeout_sec,
                )
                if resp.status_code in (200, 204):
                    break
                raise RuntimeError(
                    f"YouTube 删除失败 HTTP {resp.status_code}: {resp.text[:500]}"
                )
            except Exception as exc:
                last_exc = exc
                if attempt >= max_retries:
                    raise RuntimeError(
                        f"YouTube 删除失败 {video_id}: {last_exc!r}"
                    ) from last_exc
                wait = 3 * attempt
                print(f"  删除重试 ({attempt}/{max_retries})，{wait}s…", flush=True)
                time.sleep(wait)

    print(f"已删除 YouTube 视频: {video_id}", flush=True)
    return True


def _upload_resumable(request, *, max_retries: int = 8) -> dict:
    """分块上传，网络超时/握手失败时自动重试（可断点续传）。"""
    import ssl
    import time

    response = None
    retries = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"上传中… {pct}%", flush=True)
            retries = 0
        except (
            TimeoutError,
            OSError,
            ssl.SSLError,
            ConnectionError,
            BrokenPipeError,
        ) as exc:
            retries += 1
            if retries > max_retries:
                raise RuntimeError(
                    f"上传失败：网络在 {max_retries} 次重试后仍不可用（{exc!r}）。\n"
                    "请检查网络/VPN，或稍后在终端重新运行：python3 scripts/upload_youtube.py"
                ) from exc
            wait = min(60, 5 * retries)
            print(
                f"网络中断（{type(exc).__name__}），{wait}s 后重试 "
                f"({retries}/{max_retries})…",
                flush=True,
            )
            time.sleep(wait)
    return response


def _request_with_retry(session, method: str, url: str, *, max_retries: int, timeout_sec: int, **kwargs):
    import ssl
    import time

    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return session.request(
                method, url, timeout=(30, timeout_sec), **kwargs
            )
        except (
            TimeoutError,
            OSError,
            ssl.SSLError,
            ConnectionError,
            BrokenPipeError,
        ) as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            wait = min(60, 5 * attempt)
            print(
                f"网络异常（{type(exc).__name__}），{wait}s 后重试 "
                f"({attempt}/{max_retries})…",
                flush=True,
            )
            time.sleep(wait)
    raise RuntimeError(
        f"连接 Google 失败（已重试 {max_retries} 次）：{last_exc!r}\n"
        "常见原因：无法稳定访问 googleapis.com（需代理/VPN），或防火墙拦截。\n"
        "可改用：python3 scripts/upload_youtube.py --export-metadata\n"
        "然后在 YouTube Studio 网页端手动上传视频并粘贴简介。"
    ) from last_exc


def _parse_upload_range(range_header: str | None) -> int | None:
    if not range_header:
        return None
    part = range_header.strip().split("=")[-1]
    if "-" not in part:
        return None
    end = int(part.split("-")[1])
    return end + 1


def upload_video_requests(
    video_path: Path,
    body: dict,
    *,
    project_root: Path,
    playlist_id: str = "",
    thumbnail_path: Path | None = None,
    timeout_sec: int = 600,
    max_retries: int = 8,
    chunk_size: int = 4 * 1024 * 1024,
) -> dict:
    """用 requests 断点续传（推荐；走系统代理更可靠）。"""
    video_path = video_path.resolve()
    if not video_path.is_file():
        raise FileNotFoundError(f"视频不存在: {video_path}")

    file_size = video_path.stat().st_size
    size_mb = file_size / (1024 * 1024)
    print(
        f"上传方式: requests 断点续传 | 文件: {size_mb:.1f} MB",
        flush=True,
    )

    session = get_authorized_session(project_root)
    init_headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(file_size),
    }
    init = _request_with_retry(
        session,
        "POST",
        YOUTUBE_UPLOAD_INIT_URL,
        max_retries=max_retries,
        timeout_sec=timeout_sec,
        params={"uploadType": "resumable", "part": "snippet,status"},
        headers=init_headers,
        json=body,
    )
    if init.status_code not in (200, 201):
        raise RuntimeError(
            f"创建上传会话失败 HTTP {init.status_code}: {init.text[:500]}"
        )
    upload_url = init.headers.get("Location")
    if not upload_url:
        raise RuntimeError("YouTube 未返回上传 URL（Location 头缺失）")

    sent = 0
    response_data: dict | None = None
    with video_path.open("rb") as fh:
        while sent < file_size:
            if sent > 0:
                fh.seek(sent)
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            end = sent + len(chunk) - 1
            headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {sent}-{end}/{file_size}",
            }
            put = _request_with_retry(
                session,
                "PUT",
                upload_url,
                max_retries=max_retries,
                timeout_sec=timeout_sec,
                headers=headers,
                data=chunk,
            )
            if put.status_code in (200, 201):
                response_data = put.json()
                sent = file_size
                pct = 100
            elif put.status_code == 308:
                resume = _parse_upload_range(put.headers.get("Range"))
                sent = resume if resume is not None else end + 1
                pct = int(sent / file_size * 100)
            else:
                raise RuntimeError(
                    f"上传分块失败 HTTP {put.status_code}: {put.text[:500]}"
                )
            print(f"上传中… {pct}%", flush=True)

    if not response_data or "id" not in response_data:
        raise RuntimeError("上传结束但未收到视频 ID")

    video_id = response_data["id"]
    url = f"https://www.youtube.com/watch?v={video_id}"
    pid = playlist_id.strip()
    if pid:
        add_video_to_playlist_requests(
            session,
            pid,
            video_id,
            max_retries=max_retries,
            timeout_sec=timeout_sec,
        )

    if thumbnail_path is not None:
        print("上传缩略图…", flush=True)
        upload_thumbnail_requests(
            session,
            video_id,
            thumbnail_path,
            max_retries=max_retries,
            timeout_sec=timeout_sec,
        )
        print("缩略图完成 ✓", flush=True)

    return {"id": video_id, "url": url, "response": response_data}


def add_video_to_playlist_requests(
    session,
    playlist_id: str,
    video_id: str,
    *,
    position: int | None = None,
    max_retries: int = 8,
    timeout_sec: int = 600,
) -> bool:
    pid = playlist_id.strip()
    if not pid:
        return False
    snippet: dict = {
        "playlistId": pid,
        "resourceId": {"kind": "youtube#video", "videoId": video_id},
    }
    if position is not None:
        snippet["position"] = max(0, position)
    pl = _request_with_retry(
        session,
        "POST",
        f"{YOUTUBE_API_BASE}/playlistItems",
        max_retries=max_retries,
        timeout_sec=timeout_sec,
        params={"part": "snippet"},
        json={"snippet": snippet},
    )
    if pl.status_code not in (200, 201):
        print(f"警告：加入播放列表失败 HTTP {pl.status_code}", flush=True)
        return False
    print(f"已加入播放列表: {pid}", flush=True)
    return True


def create_youtube_playlist(
    project_root: Path,
    title: str,
    *,
    description: str = "",
    privacy_status: str = "public",
    method: str = "requests",
) -> dict:
    """在已授权频道下新建播放列表，返回 {id, url}。"""
    title = title.strip()
    if not title:
        raise ValueError("播放列表标题不能为空")
    body = {
        "snippet": {"title": title, "description": (description or "").strip()},
        "status": {"privacyStatus": privacy_status},
    }
    if method == "googleapiclient":
        youtube = get_youtube_service(project_root)
        resp = (
            youtube.playlists()
            .insert(part="snippet,status", body=body)
            .execute()
        )
    else:
        session = get_authorized_session(project_root)
        r = _request_with_retry(
            session,
            "POST",
            f"{YOUTUBE_API_BASE}/playlists",
            max_retries=8,
            timeout_sec=600,
            params={"part": "snippet,status"},
            json=body,
        )
        if r.status_code not in (200, 201):
            raise RuntimeError(
                f"创建播放列表失败 HTTP {r.status_code}: {r.text[:500]}"
            )
        resp = r.json()
    pid = resp["id"]
    url = f"https://www.youtube.com/playlist?list={pid}"
    print(f"已创建 YouTube 播放列表: {title}\n  id={pid}\n  {url}", flush=True)
    return {"id": pid, "url": url, "response": resp}


def add_video_to_playlist(
    project_root: Path,
    playlist_id: str,
    video_id: str,
    *,
    position: int | None = None,
    method: str = "requests",
    timeout_sec: int = 600,
    max_retries: int = 8,
) -> bool:
    """将已有视频加入播放列表（用于补登记后的批量同步）。"""
    if method == "googleapiclient":
        youtube = get_youtube_service(project_root, timeout_sec=timeout_sec)
        snippet: dict = {
            "playlistId": playlist_id.strip(),
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
        if position is not None:
            snippet["position"] = max(0, position)
        youtube.playlistItems().insert(part="snippet", body={"snippet": snippet}).execute()
        print(f"已加入播放列表: {playlist_id.strip()}", flush=True)
        return True
    session = get_authorized_session(project_root)
    return add_video_to_playlist_requests(
        session,
        playlist_id,
        video_id,
        position=position,
        max_retries=max_retries,
        timeout_sec=timeout_sec,
    )


def upload_video_googleapiclient(
    video_path: Path,
    body: dict,
    *,
    project_root: Path,
    playlist_id: str = "",
    thumbnail_path: Path | None = None,
    timeout_sec: int = 600,
    max_retries: int = 8,
) -> dict:
    from googleapiclient.http import MediaFileUpload

    video_path = video_path.resolve()
    if not video_path.is_file():
        raise FileNotFoundError(f"视频不存在: {video_path}")

    size_mb = video_path.stat().st_size / (1024 * 1024)
    print(f"上传方式: googleapiclient | 文件: {size_mb:.1f} MB", flush=True)

    youtube = get_youtube_service(project_root, timeout_sec=timeout_sec)
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=4 * 1024 * 1024,
    )
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )
    response = _upload_resumable(request, max_retries=max_retries)
    video_id = response["id"]
    url = f"https://www.youtube.com/watch?v={video_id}"

    pid = playlist_id.strip()
    if pid:
        add_video_to_playlist(
            project_root,
            pid,
            video_id,
            method="googleapiclient",
            timeout_sec=timeout_sec,
            max_retries=max_retries,
        )

    if thumbnail_path is not None:
        print("上传缩略图…", flush=True)
        upload_thumbnail_googleapiclient(
            project_root, video_id, thumbnail_path, timeout_sec=timeout_sec
        )
        print("缩略图完成 ✓", flush=True)

    return {"id": video_id, "url": url, "response": response}


def upload_video(
    video_path: Path,
    body: dict,
    *,
    project_root: Path,
    playlist_id: str = "",
    thumbnail_path: Path | None = None,
    timeout_sec: int = 600,
    max_retries: int = 8,
    method: str = "requests",
) -> dict:
    if method == "googleapiclient":
        return upload_video_googleapiclient(
            video_path,
            body,
            project_root=project_root,
            playlist_id=playlist_id,
            thumbnail_path=thumbnail_path,
            timeout_sec=timeout_sec,
            max_retries=max_retries,
        )
    return upload_video_requests(
        video_path,
        body,
        project_root=project_root,
        playlist_id=playlist_id,
        thumbnail_path=thumbnail_path,
        timeout_sec=timeout_sec,
        max_retries=max_retries,
    )


def export_metadata_package(
    storyboard: Storyboard,
    *,
    project_root: Path,
    video_path: Path,
    out_dir: Path | None = None,
) -> Path:
    """导出供 YouTube Studio 手动上传的标题/简介/标签（不经过 API 传视频）。"""
    root = project_root.resolve()
    out = (out_dir or root / "output" / "youtube-upload").resolve()
    out.mkdir(parents=True, exist_ok=True)

    meta = preview_metadata(storyboard, project_root=root, video_path=video_path)
    thumb = resolve_thumbnail_path(storyboard, root)
    if thumb is not None:
        meta["thumbnail"] = str(thumb)
    (out / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    privacy_zh = {
        "private": "私享",
        "unlisted": "不公开",
        "public": "公开",
    }.get(meta["privacy"], meta["privacy"])

    paste_parts = [
        "=== 标题 ===",
        meta["title"],
        "",
        f"=== 可见性 ===",
        privacy_zh,
        "",
        "=== 标签（Studio 里逐条添加或粘贴） ===",
        ", ".join(meta["tags"]),
        "",
        "=== 简介 ===",
        meta["description"],
        "",
    ]
    if meta.get("thumbnail"):
        paste_parts.extend(
            [
                "=== 缩略图（Studio 里上传） ===",
                meta["thumbnail"],
                "",
            ]
        )
    paste = "\n".join(paste_parts)
    (out / "studio-paste.txt").write_text(paste, encoding="utf-8")

    readme = f"""观念黑盒 · YouTube 手动上传包
================================

视频文件（拖进 Studio）:
  {video_path.resolve()}

元数据（复制粘贴）:
  {out / "studio-paste.txt"}

步骤:
  1. 浏览器打开 https://studio.youtube.com （需能访问 Google）
  2. 右上角「创建」→「上传视频」
  3. 选择上面的 mp4 文件，等待处理
  4. 标题 / 简介 / 标签 从 studio-paste.txt 复制
  5. 上传缩略图（见 studio-paste.txt 中的路径）
  6. 可见性选「{privacy_zh}」→ 发布

说明:
  API 上传连的是 googleapis.com，与 Studio 网页是同一类服务。
  若脚本上传 SSL 超时，通常是本地网络无法稳定访问 Google，
  用浏览器 + Studio 上传往往更稳（可走系统 VPN/代理）。

  有代理时也可再试 API:
    export HTTPS_PROXY=http://127.0.0.1:7890
    python3 scripts/upload_youtube.py --method requests
"""
    (out / "README.txt").write_text(readme, encoding="utf-8")
    return out


def resolve_audio_dir(
    project_root: Path,
    audio_dir: Path | None = None,
) -> Path:
    """各镜 mp3 目录；81 章通读默认 output/daodejing-81-full/audio。"""
    if audio_dir is not None:
        return audio_dir.resolve()
    root = project_root.resolve()
    d81 = root / "output" / "daodejing-81-full" / "audio"
    if d81.is_dir() and (d81 / "ch01.mp3").is_file():
        return d81
    return (root / "output" / "audio").resolve()


def resolve_output_video(project_root: Path, filename: str) -> Path:
    """解析成片路径；JSON 中的 filename 不存在时回退到 output 下最新 mp4。"""
    out_dir = project_root / "output"
    preferred = out_dir / filename
    if preferred.is_file():
        return preferred.resolve()

    candidates = [
        p
        for p in out_dir.glob("*.mp4")
        if p.is_file() and p.parent.resolve() == out_dir.resolve()
    ]
    if not candidates:
        raise FileNotFoundError(
            f"未找到视频。请将成片放在 {preferred}，或 output/*.mp4"
        )
    return max(candidates, key=lambda p: p.stat().st_mtime).resolve()


def preview_metadata(
    storyboard: Storyboard,
    *,
    project_root: Path,
    video_path: Path | None = None,
    audio_dir: Path | None = None,
    time_offset_sec: float = 0.0,
    publish_at: str | None = None,
) -> dict:
    root = project_root.resolve()
    if audio_dir is None:
        audio_dir = resolve_audio_dir(root)
    cfg = getattr(storyboard, "youtube", None) or YouTubeConfig()
    body = build_upload_body(
        storyboard,
        audio_dir=audio_dir,
        config=cfg,
        time_offset_sec=time_offset_sec,
        publish_at=publish_at,
    )
    out = {
        "video": str(video_path) if video_path else None,
        "title": body["snippet"]["title"],
        "description": body["snippet"]["description"],
        "tags": body["snippet"]["tags"],
        "privacy": body["status"]["privacyStatus"],
        "category_id": body["snippet"]["categoryId"],
    }
    return out
