# TTS发音修正方案

## 问题描述
火山引擎TTS在朗读"老子"、"孔子"、"庄子"等哲学家名字时，容易将"子"读成 **zi（轻声）** 而不是正确的 **zǐ（第三声）**。

## 解决方案

### 方案4：拼音注音方案 ⭐️ 已实现

**原理：** 为每个字添加拼音标注，格式为 `字[pīn yīn]`，指导TTS引擎准确发音。

**实现位置：** `pipeline/text_preprocess.py`

**修正列表：**
- 老子 → 老[lǎo]子[zǐ]
- 孔子 → 孔[kǒng]子[zǐ]
- 庄子 → 庄[zhuāng]子[zǐ]
- 孟子 → 孟[mèng]子[zǐ]
- 荀子 → 荀[xún]子[zǐ]
- 墨子 → 墨[mò]子[zǐ]
- 韩非子 → 韩[hán]非[fēi]子[zǐ]
- 列子 → 列[liè]子[zǐ]
- 管子 → 管[guǎn]子[zǐ]
- 老聃 → 老[lǎo]聃[dān]
- 庄周 → 庄[zhuāng]周[zhōu]

**优点：**
- ✅ 精确指定发音，最准确的方式
- ✅ 每个字都有清晰的发音指导
- ✅ 适用于火山引擎TTS API
- ✅ 不影响原文字符（拼音注解在渲染时可剥离）

**缺点：**
- ⚠️ 文本长度增加
- ⚠️ 字幕渲染时需要剥离拼音标注

### 方案1：全角空格分词法（已弃用）

**原理：** 在多音字之间插入全角空格（　），强制TTS引擎将其作为两个独立的词来处理。

**缺点：**
- ⚠️ 字幕中会显示全角空格
- ⚠️ 对顽固的多音字效果不佳

### 方案2：顿号分词法（已弃用）

**原理：** 使用顿号（、）或逗号（，）强制停顿。

**缺点：**
- ⚠️ 字幕中会显示标点符号
- ⚠️ 改变了原文的标点结构

### 方案3：同音字替换法（不推荐）

将"子"替换为同音字"籽"或"梓"，但这会改变原文，不推荐。

## 使用方法

### 自动修正
代码已集成到TTS流程中，**无需手动操作**。所有通过`synthesize_volcengine()`生成的音频都会自动应用发音修正。

### 测试效果
1. 生成测试音频：
   ```bash
   python3 -m pipeline examples/storyboard-pronunciation-test.json
   ```

2. 播放音频文件检查发音：
   ```bash
   open output/audio/test-01.mp3  # 包含"孔子"
   open output/audio/test-02.mp3  # 包含"老子"、"老聃"
   open output/audio/test-03.mp3  # 包含"庄子"、"庄周"
   ```

### 添加新的发音修正
编辑 `pipeline/text_preprocess.py`，在 `PRONUNCIATION_FIXES` 列表中添加：

```python
PRONUNCIATION_FIXES = [
    ("新词", "拼音", "说明"),
    # 例如：
    ("老子", "lǎo zǐ", "道家创始人"),
]
```

### 字幕渲染时剥离拼音
在字幕渲染模块中使用 `strip_pinyin_annotations()` 函数：

```python
from pipeline.text_preprocess import strip_pinyin_annotations

# TTS使用带拼音标注的文本
tts_text = "老[lǎo]子[zǐ]的《道[dào]德[dé]经[jīng]》"

# 字幕显示纯文本
subtitle_text = strip_pinyin_annotations(tts_text)
# 结果: "老子的《道德经》"
```

## 技术细节

### 代码位置
- **预处理模块：** `pipeline/text_preprocess.py`
- **集成点：** `pipeline/tts_volcengine.py` 的 `synthesize_volcengine()` 函数

### 工作流程
```
原始文本 
  ↓
fix_pronunciation_for_tts() [插入全角空格]
  ↓
火山引擎TTS API
  ↓
MP3音频文件
```

### 测试函数
```bash
# 运行内置测试
python3 pipeline/text_preprocess.py
```

## 效果验证

| 原文 | 修正后 | 效果 |
|------|--------|------|
| 如果你去读孔子 | 如果你去读孔[kǒng]子[zǐ] | ✅ 正确发音 zǐ |
| 老子的《道德经》 | 老[lǎo]子[zǐ]的《道德经》 | ✅ 正确发音 zǐ |
| 庄子写了《逍遥游》 | 庄[zhuāng]子[zǐ]写了《逍遥游》 | ✅ 正确发音 zǐ |
| 为什么是庄周 | 为什么是庄[zhuāng]周[zhōu] | ✅ 正确发音 zhōu |
| 孙子兵法 | 孙[sūn]子[zǐ]兵[bīng]法[fǎ] | ✅ 精确发音指导 |

## 注意事项

1. **字幕渲染：** 拼音标注会在TTS音频中生效，但字幕渲染时需要剥离拼音（使用正则表达式 `\[.*?\]`）
2. **文本长度：** 添加拼音注音后文本会变长，但不影响TTS准确性
3. **火山引擎支持：** 此方案专门针对火山引擎TTS优化
4. **扩展性：** 可根据需要在 `PRONUNCIATION_FIXES` 表中添加更多多音字修正规则

## 相关文件

- `pipeline/text_preprocess.py` - 发音修正核心逻辑
- `pipeline/tts_volcengine.py` - TTS集成点
- `examples/storyboard-pronunciation-test.json` - 测试故事板
- `output/audio/test-*.mp3` - 测试音频输出

---

**更新日期：** 2026-06-17  
**状态：** ✅ 已实现并集成到生产流程
