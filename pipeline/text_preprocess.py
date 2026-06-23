"""TTS文本预处理：修正常见多音字发音。"""

import re

# 哲学人物名称发音修正表
# 格式：(原文, 拼音标注, 说明)
PRONUNCIATION_FIXES = [
    # 先秦哲学家
    ("老子", "lǎo zǐ", "道家创始人，不是儿子的'子'"),
    ("庄子", "zhuāng zǐ", "道家代表，不是儿子的'子'"),
    ("孔子", "kǒng zǐ", "儒家创始人，不是儿子的'子'"),
    ("孟子", "mèng zǐ", "儒家亚圣，不是儿子的'子'"),
    ("荀子", "xún zǐ", "儒家代表，不是儿子的'子'"),
    ("墨子", "mò zǐ", "墨家创始人，不是儿子的'子'"),
    ("韩非子", "hán fēi zǐ", "法家集大成者"),
    ("列子", "liè zǐ", "道家代表"),
    ("管子", "guǎn zǐ", "法家先驱"),
    
    # 其他常见多音字
    ("道德经", "dào dé jīng", "不是'经过'的经"),
    ("逍遥游", "xiāo yáo yóu", "庄子篇名"),
    ("论语", "lún yǔ", "不是'语言'的语"),
    ("孙子兵法", "sūn zǐ bīng fǎ", "兵书"),
    
    # 专有名词
    ("鲲鹏", "kūn péng", "庄子寓言中的大鸟"),
    ("老聃", "lǎo dān", "老子的字"),
    ("庄周", "zhuāng zhōu", "庄子本名"),
]


def fix_pronunciation_for_tts(text: str, provider: str = "volcengine") -> str:
    """
    为TTS修正文本中的发音问题。
    
    参数:
        text: 原始文本
        provider: TTS提供商 ('volcengine', 'edge')
    
    返回:
        修正后的文本
    """
    if provider == "volcengine":
        # 火山引擎：使用拼音注音方案 (方案4)
        result = text
        
        # 处理所有发音修正项
        for original, pinyin, _ in PRONUNCIATION_FIXES:
            if original in result:
                # 使用拼音注音格式：老子 → 老[lǎo]子[zǐ]
                chars = list(original)
                syllables = pinyin.split()
                
                if len(chars) == len(syllables):
                    # 为每个字添加拼音注音
                    annotated = "".join([f"{char}[{syl}]" for char, syl in zip(chars, syllables)])
                    result = result.replace(original, annotated)
        
        return result
    
    elif provider == "edge":
        # Edge TTS支持SSML
        result = text
        for original, pinyin, _ in PRONUNCIATION_FIXES:
            if original in result:
                # 使用SSML phoneme标签
                # result = result.replace(
                #     original,
                #     f'<phoneme alphabet="ipa" ph="{pinyin}">{original}</phoneme>'
                # )
                # Edge暂时也用空格方案
                if original.endswith("子") and len(original) == 2:
                    spaced = original[0] + "　" + original[1]
                    result = result.replace(original, spaced)
        
        return result
    
    return text


def strip_pinyin_annotations(text: str) -> str:
    """
    从文本中剥离拼音注音，用于字幕渲染。
    
    例如：
        "老[lǎo]子[zǐ]" → "老子"
        "庄[zhuāng]周[zhōu]" → "庄周"
    
    参数:
        text: 包含拼音注音的文本
    
    返回:
        剥离拼音后的纯文本
    """
    # 使用正则表达式移除所有 [拼音] 标注
    return re.sub(r'\[.*?\]', '', text)


def test_fixes():
    """测试发音修正效果。"""
    test_cases = [
        "如果你去读孔子，他会教你如何成为一个完美的社会零件。",
        "老子的《道德经》是道家经典。",
        "庄子写了《逍遥游》，讲述鲲鹏的故事。",
        "孙子兵法是古代兵书。",
        "为什么是庄周？为什么我们要在这个时间点去读他？",
        "老聃依然是在游戏规则之内，教你成为一个最顶级的玩家。但庄周，完全是另一个维度的存在。",
        "韩非子是法家集大成者。",
    ]
    
    print("=" * 60)
    print("TTS发音修正测试（方案4：拼音注音）")
    print("=" * 60)
    for text in test_cases:
        fixed = fix_pronunciation_for_tts(text, "volcengine")
        if text != fixed:
            print(f"\n原文: {text}")
            print(f"修正: {fixed}")
            stripped = strip_pinyin_annotations(fixed)
            print(f"字幕: {stripped}")
        else:
            print(f"\n无需修正: {text}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_fixes()
