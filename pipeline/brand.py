"""频道品牌固定配置（片尾、水印、画面文字风格）。"""

# 与 placeholder-home 暗区一致（#060f0c ~ #121f1a）
PALETTE_BG = "#0a1210"
PALETTE_MID = "#121f1a"
PALETTE_ACCENT = "#1a2e28"
BACKGROUND_COLOR = PALETTE_BG

# 示例占位图（scripts/make_placeholder.py）
PLACEHOLDER_IMAGE = "assets/placeholder.jpg"
PLACEHOLDER_HOME_IMAGE = "assets/placeholder-home.jpg"
PLACEHOLDER_CHAPTER_DIR = "assets/chapters"
DEFAULT_CHAPTER_PLACEHOLDERS = (
    ("chapter-01.jpg", "第一章"),
    ("chapter-02.jpg", "第二章"),
    ("chapter-03.jpg", "第三章"),
)

# 首页：宝盒背景（标题偏左中，右侧留给画面；字幕仍全幅）
HOOK_BG = "assets/hook_bg.webp"
HOOK_HOME_ZONE_LEFT_RATIO = 0.12
HOOK_HOME_ZONE_WIDTH_RATIO = 0.52

# 片尾：avatar 全屏（文案已印在图内）
BRAND_AVATAR = "assets/avatar.webp"
ENDING_SCENE_ID = "ending"
ENDING_IMAGE = BRAND_AVATAR
ENDING_NARRATION = ""
ENDING_DURATION_SEC = 4.0

# 字体：默认魏碑 SC（Weibei SC），与片尾 avatar.webp 内「打开观念黑盒…」一致
# None = 自动探测（见 pipeline/ffmpeg_util.find_weibei_font）；可改为本地 .otf 路径
FONT_PATH = None
FONT_FAMILY = "Weibei SC"
FONT_INDEX_REGULAR = 0
FONT_INDEX_LIGHT = 2

# 字幕：无黑底条，柔和阴影（更接近真人剪辑）
SUBTITLE_FONT_SIZE = 34
SUBTITLE_COLOR = "#f2f0e8"
SUBTITLE_MARGIN_BOTTOM = 100
SUBTITLE_MAX_WIDTH_RATIO = 0.78
SUBTITLE_MAX_LINES = 2
# 旁白超过此字数不烧录字幕（长段仅配音，避免满屏字）
SUBTITLE_MAX_CHARS = 100
# 默认按句 TTS 时间轴烧录（PIL 逐句换字 + 拼接），不再把整段旁白烙在画面上
SUBTITLE_TIMED = True
SUBTITLE_STYLE = "shadow"  # shadow | box
SUBTITLE_ALIGN = "center"  # center | left

# 左上角品牌 Logo（assets/Logo.png）
WATERMARK_IMAGE = "assets/Logo.png"
WATERMARK_MODE = "image"  # image | text | both
WATERMARK_WIDTH_RATIO = 0.0325
WATERMARK_OPACITY = 0.92
WATERMARK_MARGIN_X = 40
WATERMARK_MARGIN_Y = 40
WATERMARK_LABEL_GAP = 16
# Logo.png 常为白底；去浅底。小尺寸仅显示印章（墨迹缩小后易糊、不好看）
WATERMARK_SEAL_ONLY = True
WATERMARK_KEY_LIGHT_BG = True
WATERMARK_BACKPLATE = False
WATERMARK_BACKPLATE_PAD = 14
WATERMARK_BACKPLATE_RADIUS = 10

# 印章右侧品牌字（魏碑）
WATERMARK_TEXT = "观念黑盒"
WATERMARK_FONT_SIZE = 32
WATERMARK_COLOR = "#f2f0e8"
WATERMARK_STYLE = "minimal"
