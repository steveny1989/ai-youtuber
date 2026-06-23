#!/usr/bin/env python3
"""生成 ch06–ch10 hybrid 讲解分镜（观念黑盒结构，配图不重复 ch01–05）。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
CATALOG = ROOT / "assets/DaoDeJing/image_catalog.json"

CHAPTER_META = {
    6: {
        "title_short": "谷神不死",
        "yt_tag": "谷神不死",
        "bili_dynamic": "真正的生命力，来自空而不竭的谷。",
        "desc_intro": "观念黑盒：《道德经》第六章精解——谷神不死，玄牝之门。",
        "sections": {
            "plain": "谷神不死；玄牝；天地根；绵绵若存；用之不勤。",
            "east_west": "荣格阿尼玛；老子母性道体 vs 父权逻各斯。",
            "modern": "可持续创作、休息即生产力、别榨干谷神。",
            "closing": "认源头、守虚空、绵绵不断、用而不竭。",
        },
        "chapters": [
            ("承上：谷神", "过渡 · 承上启下"),
            ("五段破译", "五段破译"),
            ("东西方互证", "东西方互证"),
            ("可持续", "可持续创作"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [
            ("intro-bridge", "第五章讲大系统无偏爱。第六章，老子把镜头转向「生之源」：「谷神不死，是谓玄牝。」谷，是空虚而容纳；神，是持续运作的生机。很多人把这一章读成玄学母题。其实，它在描述一种可持续结构——真正的力量，来自空而不竭的源头。"),
            ("open-1", "我们逐段破译。"),
            ("s1", "第一段：「谷神不死。」山谷之神，象征因空而能生、因低而能纳的永恒生机。它不会因为你忽视就消失，也不会因为你过度开采就立刻报复——它默默在那里，像底层操作系统。"),
            ("s2", "第二段：「是谓玄牝。」玄牝，是幽深的母性、孕育之门。老子用「母」不是性别标签，而是结构隐喻：万物从「空而含」的门户中生出。"),
            ("s3", "第三段：「玄牝之门，是谓天地根。」这扇门，是天地万物的根。根不在高处，在低处、在空处、在愿意接纳之处。"),
            ("s4", "第四段：「绵绵若存，用之不勤。」它像细丝一样持续存在，越用越不虚。不是一次性爆发，而是长期涓流。"),
            ("s5", "第五段，全章落点：「用之不勤。」真正的好系统，不需要你24小时狂按加速键。它靠节律、靠留白、靠可恢复性，持续供给你。"),
            ("open-ext1", "荣格谈集体无意识里的「阿尼玛」，是心灵中接纳与孕育的一面。西方长期偏重逻各斯——分析、征服、命名；老子在这里补另一极：玄牝、谷神、母性道体。东方《易经》坤卦「厚德载物」，也在说：承载，比张扬更久。"),
            ("open-ext2", "回到今天。创作者把「谷神」榨干：日更、通宵、永远在线。短期看是勤奋，长期看是透支天地根。可持续产出，不是更狠，而是让源头有空、有眠、有恢复。"),
            ("s-ext2", "公司也一样：只榨 KPI、不补组织容量的团队，初期猛，后期崩。绵绵若存，要求你设计节律，而不是设计燃尽。"),
            ("open-close", "四条认知补丁：第一，认源头：力量来自空而不竭的谷。第二，守母门：别只崇拜锋锐，要留孕育之地。第三，绵绵不断：用节律，不用爆发。第四，用而不竭：恢复是生产力。下一章，「天长地久」——不自生，故能长生。"),
        ],
    },
    7: {
        "title_short": "天长地久",
        "yt_tag": "天长地久",
        "bili_dynamic": "越把自己放最后，系统越让你站得久。",
        "desc_intro": "观念黑盒：《道德经》第七章精解——后其身而身先。",
        "sections": {
            "plain": "天地长久；不自生；后身身先；外身身存；无私成私。",
            "east_west": "康德自律；儒家先忧后乐 vs 老子退后。",
            "modern": "抢功、抢镜、抢 C 位；长期主义领导者。",
            "closing": "学天地、后其身、外其身、以无私成。",
        },
        "chapters": [
            ("承上：长生", "过渡 · 承上启下"),
            ("五段破译", "五段破译"),
            ("东西方互证", "东西方互证"),
            ("抢位焦虑", "抢 C 位"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [
            ("intro-bridge", "第六章讲「谷神」——生之源在空处。第七章追问：为什么天地能长久？答案反直觉：「以其不自生，故能长生。」不是为自己活，反而活得久。这对今天所有「抢 C 位」的人，是一记闷棍。"),
            ("open-1", "我们逐段破译。"),
            ("s1", "第一段：「天长地久。天地所以能长且久者，以其不自生，故能长生。」天地不为自己生存而运转，所以能长久。把「自我保存」从第一位挪开，系统反而稳定。"),
            ("s2", "第二段：「是以圣人后其身而身先。」圣人把自己放后面，反而被推到前面。不是装谦虚，是不抢位置，让位置自然形成。"),
            ("s3", "第三段：「外其身而身存。」不把肉身和身份焊死在利益中心，反而能存住。你越把「我」顶在最前，越容易被攻击、被消耗、被替换。"),
            ("s4", "第四段：「非以其无私邪？故能成其私。」正因为不自私，反而成就了自己。这里的「私」，不是损人利己，是可持续的自我实现。"),
            ("s5", "全章落点：长久，来自退后；领导力，来自不抢。天地给你的模型，是「无私故长生」，不是「抢故赢」。"),
            ("open-ext1", "范仲淹「先天下之忧而忧，后天下之乐而乐」，是儒家的退后逻辑。康德讲自律：当你不被感性冲动牵着走，反而获得真正的自由。老子更早：后其身、外其身，是系统级的退后。"),
            ("open-ext2", "回到今天。职场抢功、会议抢话、内容抢热点——短期你靠前，长期你透支信任。真正走得远的团队，往往是那个愿意做后勤、做底座、做基础设施的人。"),
            ("s-ext2", "领导者若凡事抢镜，组织就学会表演；领导者若退后一步，组织才学会担当。后其身而身先，是结构，不是人设。"),
            ("open-close", "四条认知补丁：第一，学天地：不自生，故能长生。第二，后其身：别抢第一排。第三，外其身：别把身份焊死在功劳上。第四，以无私成：退后，反而站久。下一章，「上善若水」——不争之德。"),
        ],
    },
    8: {
        "title_short": "上善若水",
        "yt_tag": "上善若水",
        "bili_dynamic": "水从不证明自己是水，它只是在低处把路让出来。",
        "desc_intro": "观念黑盒：《道德经》第八章精解——水善利万物而不争。",
        "sections": {
            "plain": "上善若水；处恶；几于道；居善地心善渊；不争无尤。",
            "east_west": "泰勒斯万物源于水；庄子水至柔。",
            "modern": "处下、润下、协作型领导力。",
            "closing": "学水、处下、利他不争、顺势而为。",
        },
        "chapters": [
            ("承上：不争", "过渡 · 承上启下"),
            ("九善", "九善破译"),
            ("东西方互证", "东西方互证"),
            ("处下智慧", "处下"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [
            ("intro-bridge", "第七章讲退后能久。第八章，老子给出最熟悉的意象：「上善若水。」最高的善，像水一样。水不占高位，却润下万物；不与谁争名，却没有谁离得开它。这一章，是「不争」的操作手册。"),
            ("open-1", "我们逐段破译。"),
            ("s1", "第一段：「上善若水。水善利万物而不争。」水滋养一切，却不争功。它不需要被看见，只需要持续流动。"),
            ("s2", "第二段：「处众人之所恶，故几于道。」水往低处走，往人们嫌弃的缝隙里走，所以最接近道。处下，不是自贬，是接近真实运行层。"),
            ("s3", "第三段：「居善地，心善渊，与善仁，言善信，正善治，事善能，动善时。」居处选善地，心像深渊般静，交往有仁，说话有信，治事有正，做事能成，行动合时——这是水的九种善。"),
            ("s4", "第四段：「动善时。」尤其这一句：行动要合时。不是永远冲，是在该流时流，该停时停。"),
            ("s5", "全章落点：「夫唯不争，故无尤。」因为不争，所以没有怨尤。水从不证明自己是水，它只是在低处把路让出来。"),
            ("open-ext1", "泰勒斯说「万物源于水」，是西方哲学源头之一。庄子讲「至柔驰骋至坚」，与水克刚同一脉。老子在这里把水写成道德模板：利万物、处下、合时、不争。"),
            ("open-ext2", "回到今天。最高明的协作，往往像水：补位、润下、不抢镜。团队里那个「什么都接、从不争功」的人，往往是真正的基础设施。"),
            ("s-ext2", "个人品牌时代，人人想「站在高处」。但流量高处也干燥。处众人之所恶——去真正有问题、有摩擦、有需要的缝隙里，反而离道更近。"),
            ("open-close", "四条认知补丁：第一，学水：利而不争。第二，处下：去真实问题所在。第三，动善时：节奏比蛮力重要。第四，无尤：不争，才无后患。下一章，「持而盈之」——满则溢，锐则败。"),
        ],
    },
    9: {
        "title_short": "持而盈之",
        "yt_tag": "持而盈之",
        "bili_dynamic": "功成身退，不是怂，是懂天之道。",
        "desc_intro": "观念黑盒：《道德经》第九章精解——持而盈之，不如其已。",
        "sections": {
            "plain": "持盈；揣锐；金玉满堂；富贵而骄；功成身退。",
            "east_west": "苏格拉底知无知；易经亢龙有悔。",
            "modern": "过度优化、峰值膨胀、不知止。",
            "closing": "知止、收锐、戒骄、身退。",
        },
        "chapters": [
            ("承上：知止", "过渡 · 承上启下"),
            ("五段破译", "五段破译"),
            ("东西方互证", "东西方互证"),
            ("峰值膨胀", "不知止"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [
            ("intro-bridge", "第八章讲水的「不争」。第九章，老子直接警告膨胀：「持而盈之，不如其已。」端满了还继续加，不如停下。揣锐了还继续磨，不能久保。这是整套系统里的「止损章」。"),
            ("open-1", "我们逐段破译。"),
            ("s1", "第一段：「持而盈之，不如其已。」已经满了，还硬要再装，不如适可而止。对个人，是野心过载；对组织，是 KPI 堆到失真。"),
            ("s2", "第二段：「揣而锐之，不可长保。」把锋芒磨到最尖，无法长久。越锋利，越脆；越满，越溢。"),
            ("s3", "第三段：「金玉满堂，莫之能守；富贵而骄，自遗其咎。」堆满金玉，守不住；富贵而骄，自招祸患。资源过剩而不收，是系统失衡。"),
            ("s4", "第四段：「功成身退，天之道。」成了，就退。不是消极，是顺应天道：物极必反，峰值之后是下坡。"),
            ("s5", "全章落点：功成身退。今天最难的一课——在高光时主动收，在赢时主动止。"),
            ("open-ext1", "《易经》「亢龙有悔」：飞到最高，就有悔。苏格拉底「我知道我一无所知」，是认知上的功成身退。老子把同一逻辑写进权力与财富：别在峰值加杠杆。"),
            ("open-ext2", "回到今天。融资峰值、流量峰值、职级峰值——人人想再冲一把。但持而盈之：你的系统真的还能装吗？团队、健康、信誉，哪一个已经满了还在硬塞？"),
            ("s-ext2", "产品过度优化、功能无限叠加，也是「揣而锐之」。用户要的是解决问题，不是看你把刀磨得多亮。"),
            ("open-close", "四条认知补丁：第一，知止：满则止。第二，收锐：别把自己磨到最尖。第三，戒骄：富贵时最危险。第四，身退：成了，就退。下一章，「载营魄抱一」——身心合一的玄德。"),
        ],
    },
    10: {
        "title_short": "载营魄抱一",
        "yt_tag": "载营魄抱一",
        "bili_dynamic": "玄德不是表演完美，是生而不有、为而不恃。",
        "desc_intro": "观念黑盒：《道德经》第十章精解——涤除玄览，能无疵乎。",
        "sections": {
            "plain": "抱一；专气致柔；涤除玄览；无知无雌；玄德。",
            "east_west": "柏拉图灵魂三分；禅宗看心。",
            "modern": "身心分裂、过度管理、控制欲。",
            "closing": "合一、致柔、净览、玄德不争。",
        },
        "chapters": [
            ("承上：合一", "过渡 · 承上启下"),
            ("七问", "七问破译"),
            ("东西方互证", "东西方互证"),
            ("身心分裂", "控制欲"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [
            ("intro-bridge", "第九章讲「知止身退」。第十章，老子转向内在操作系统：「载营魄抱一，能无离乎？」魂与魄、身与心，能否合一？这一章是一连串「能……乎」的自检——不是道德题，是状态题。"),
            ("open-1", "我们逐段破译。"),
            ("s1", "第一段：「载营魄抱一，能无离乎？」让魂与魄、意识与身体抱一，能否不分离？现代人常见分裂：脑子在加班，身体在报警；人设在线，内心离线。"),
            ("s2", "第二段：「专气致柔，能婴儿乎？」把气专聚到柔软，能否像婴儿？不是幼稚，是恢复感知力——不被盔甲包住。"),
            ("s3", "第三段：「涤除玄览，能无疵乎？」洗净心镜，能否没有瑕疵？玄览，是深层的观照之镜。信息垃圾、情绪垃圾，都会在上面留斑。"),
            ("s4", "第四段：「爱民治国，能无知乎？天门开阖，能无雌乎？」治理家国，能否不用机心？门户开合，能否守柔？越聪明，越要警惕聪明变成控制。"),
            ("s5", "全章落点：「生之，畜之，生而不有，为而不恃，长而不宰，是谓玄德。」生养而不占有，帮助而不倚仗，助长而不主宰——这是玄德。"),
            ("open-ext1", "柏拉图灵魂三分：理性、意气、欲望，需要统合。禅宗「时时勤拂拭」，与「涤除玄览」同向。老子不问你怎么表演，只问：你合一了吗？"),
            ("open-ext2", "回到今天。管理者用 KPI 控制一切，父母用规划控制孩子，创作者用人设控制自己——都是「魄离于一」。玄德，是生而不有：帮忙，但不抢 ownership。"),
            ("s-ext2", "心理咨询里常说「与身体重新连接」。专气致柔，就是别只用脑活，把呼吸、睡眠、直觉还给自己。"),
            ("open-close", "四条认知补丁：第一，抱一：身心别分家。第二，致柔：恢复婴儿级感知。第三，净览：定期擦心镜。第四，玄德：生而不有，为而不恃。下一章，「三十辐共一毂」——无之以为用。"),
        ],
    },
}


def used_images() -> set[str]:
    used: set[str] = set()
    for ch in range(1, 6):
        sb = json.loads((EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json").read_text())
        for s in sb.get("scenes", []):
            img = s.get("image")
            if img and "avatar" not in img:
                used.add(img)
    return used


def pick_images(ch: int) -> list[str]:
    used = used_images()
    catalog = json.loads(CATALOG.read_text())
    avail = [img["file"] for img in catalog["images"] if img["file"] not in used]
    start = (ch - 6) * 11
    chunk = avail[start : start + 11]
    if len(chunk) < 11:
        raise SystemExit(f"第 {ch} 章可用配图不足 11 张")
    return chunk


def build_storyboard(ch: int, meta: dict) -> dict:
    imgs = pick_images(ch)
    scene_ids = [
        "intro-bridge", "open-1", "s1", "s2", "s3", "s4", "s5",
        "open-ext1", "open-ext2", "s-ext2", "open-close",
    ]
    scenes = []
    for i, (sid, narr) in enumerate(meta["scenes"]):
        scenes.append({
            "id": sid,
            "narration": narr,
            "image": imgs[i],
            "pause_after_sec": 0.45 if sid == "intro-bridge" else (0.4 if sid == "open-close" else 0.35),
        })
    ch_labels = meta["chapters"]
    return {
        "title": f"观念黑盒：《道德经》第{['','一','二','三','四','五','六','七','八','九','十'][ch]}章精解",
        "language": "zh-CN",
        "chapters": [{"id": str(i + 1), "label": ch_labels[i][0]} for i in range(5)],
        "output": {
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "filename": f"daodejing-ch{ch:02d}-commentary.mp4",
        },
        "style": {
            "background_color": "#0a1210",
            "subtitle_style": "shadow",
            "subtitle_align": "center",
            "subtitle_font_size": 58,
            "subtitle_color": "#f2f0e8",
            "subtitle_margin_bottom": 80,
            "subtitle_max_width_ratio": 0.94,
            "subtitle_max_lines": 1,
        },
        "watermark": {"text": "观念黑盒"},
        "tts": {
            "provider": "volcengine",
            "voice": "zh_male_ruyaqingnian_uranus_bigtts",
            "resource_id": "seed-tts-2.0",
            "emotion": "narrator",
            "rate": "-5%",
        },
        "cover": {"enabled": False},
        "youtube": {
            "privacy_status": "private",
            "category_id": "27",
            "channel_url": "https://www.youtube.com/@观念黑盒",
            "tags": ["道德经", "老子", "观念黑盒", meta["yt_tag"], "哲学", f"第{ch}章"],
            "description_intro": meta["desc_intro"],
            "timeline_heading": "📌 章节时间轴（点击时间戳跳转）",
            "timeline": [
                {"scene": sid, "label": ch_labels[i][1]}
                for i, sid in enumerate(["intro-bridge", "open-1", "open-ext1", "open-ext2", "open-close"])
            ],
            "playlist_id": "",
            "made_for_kids": False,
            "default_language": "zh-CN",
        },
        "bilibili": {
            "channel_url": "https://space.bilibili.com/481103225",
            "tid": 124,
            "copyright_original": True,
            "tags": ["道德经", "老子", "观念黑盒", meta["yt_tag"], "哲学", f"第{ch}章"],
            "description_intro": meta["desc_intro"],
            "dynamic": meta["bili_dynamic"],
            "no_reprint": True,
            "open_elec": False,
            "reuse_youtube_timeline": True,
        },
        "bgm": {
            "enabled": False,
            "tracks": [
                "assets/BGM/Music_fx_relaxing_chinese_flute.wav",
                "assets/BGM/Music_fx_relaxing_chinese_guzheng.wav",
            ],
            "volume": 0.14,
            "crossfade_sec": 5,
            "fade_in_sec": 2.5,
            "fade_out_sec": 5,
            "switch_at_scene": "open-ext1",
        },
        "ending": {
            "enabled": True,
            "image": "assets/avatar.webp",
            "duration_sec": 4,
            "narration": "",
        },
        "scenes": scenes,
    }


def main() -> int:
    commentary_path = ROOT / "assets/DaoDeJing/daodejing_81_commentary.json"
    data = json.loads(commentary_path.read_text(encoding="utf-8"))
    chapters = data.setdefault("chapters", {})

    for ch, meta in CHAPTER_META.items():
        sb = build_storyboard(ch, meta)
        out = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"
        out.write_text(json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out.name}")

        chapters[str(ch)] = {
            "title": meta["title_short"],
            "mode": "hybrid",
            "read_rate": "-18%",
            "read_video": f"output/ch{ch:02d}-hybrid/segments/ch{ch:02d}-read.mp4",
            "storyboard": f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json",
            "sections": meta["sections"],
        }

    commentary_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {commentary_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
