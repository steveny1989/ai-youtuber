#!/usr/bin/env python3
"""测试不同的发音修正方案"""

# 测试文本
test_text = "老子"

# 测试不同的分隔方案
test_variants = {
    "方案1-全角空格": "老　子",
    "方案2-顿号": "老、子",
    "方案3-双空格": "老  子",
    "方案4-拼音注音": "老[lǎo]子[zǐ]",
    "方案5-间隔号": "老·子",
    "方案6-逗号": "老，子",
}

print("=" * 60)
print("不同分隔符方案测试")
print("=" * 60)
for name, variant in test_variants.items():
    marker = " ⭐️ 已实现" if "方案4" in name else ""
    print(f"{name}{marker}: {variant}")

print("\n" + "=" * 60)
print("方案4优点：")
print("=" * 60)
print("✅ 精确指定每个字的发音")
print("✅ 不依赖分隔符的停顿效果")
print("✅ 适配火山引擎TTS拼音标注功能")
print("✅ 字幕渲染时可用正则剥离注音")

print("\n" + "=" * 60)
print("实际效果演示：")
print("=" * 60)

from pipeline.text_preprocess import fix_pronunciation_for_tts

test_sentences = [
    "如果你去读孔子，他会教你如何成为一个完美的社会零件。",
    "老子的《道德经》是道家经典。",
    "庄子写了《逍遥游》，讲述鲲鹏的故事。",
    "为什么是庄周？为什么我们要在这个时间点去读他？",
    "老聃依然是在游戏规则之内。但庄周，完全是另一个维度的存在。",
]

for sentence in test_sentences:
    fixed = fix_pronunciation_for_tts(sentence, "volcengine")
    if fixed != sentence:
        print(f"\n原文: {sentence}")
        print(f"修正: {fixed}")
