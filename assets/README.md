# 本地素材目录

此目录**不会**提交到 GitHub（见项目根目录 `.gitignore`）。

请在本机自行放置：

- `Logo.png` — **左上角品牌 Logo**（全片水印，见 `pipeline/brand.py`）
- `hook_bg.webp` — **首页**背景（标题偏左中，右侧宝盒）
- `avatar.webp` — **片尾**全屏
- `placeholder.jpg` — 正文镜头底色（与首页同系暗绿灰渐变，`./scripts/make_placeholder.sh`）
- `placeholder-home.jpg` — **首页/封面**（hook 底 + 品牌 + 标题）
- `chapters/chapter-01.jpg` … — **章节图**（同首页色调 + 右侧宝盒，左侧章节名）

生成章节图：

```bash
./scripts/make_placeholder.sh
./scripts/make_placeholder.sh --chapter "第四章:chapter-04.jpg"
./scripts/make_placeholder.sh --chapters-only
```
- 分镜图片、`素材库/` 等 — 按需本地管理

分镜 JSON 中的 `image` 字段仍可使用相对路径，例如 `assets/xxx.jpg`。

**画布底色**：全片默认 `#1a1a2e`（`pipeline/brand.py` → `BACKGROUND_COLOR`）。留边、片尾、占位图应与此一致；改一处后重跑 `./scripts/make_placeholder.sh` 并重新渲染。

**字体**：片尾图内文案为魏碑体（Weibei SC）；字幕/首页占位自动跟随。非 macOS 可放 `assets/fonts/WeibeiSC-Bold.otf`。
