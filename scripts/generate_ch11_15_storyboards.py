#!/usr/bin/env python3
"""生成 ch11–ch15 hybrid 讲解分镜（观念黑盒结构，配图不重复 ch01–10）。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
CATALOG = ROOT / "assets/DaoDeJing/image_catalog.json"

CHAPTER_META = {
    11: {
        "title_short": "三十辐共一毂",
        "yt_tag": "三十辐共一毂",
        "bili_dynamic": "真正有用的，往往是中间那块「空」。",
        "desc_intro": "观念黑盒：《道德经》第十一章精解——无之以为用。",
        "sections": {
            "plain": "三十辐毂；埏埴器；凿户牖室；有之利；无之用。",
            "east_west": "海德格尔器具；日本侘寂留白。",
            "modern": "产品设计留白、组织冗余、接口与空间。",
            "closing": "看见无、设计空、利在有用、用在无中。",
        },
        "chapters": [
            ("承上：无之用", "过渡 · 承上启下"),
            ("五段破译", "五段破译"),
            ("东西方互证", "东西方互证"),
            ("留白设计", "空与用"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [
            (
                "intro-bridge",
                "第十章讲「抱一」「玄德」——生而不有。第十一章，老子用三个日常器物，把同一逻辑推到结构层：「三十辐共一毂，当其无，有车之用。」辐条再多，靠的却是毂里的空。这一章，是整套系统里的「设计论」——有，给你利；无，才给你用。",
            ),
            ("open-1", "我们逐段破译。"),
            (
                "s1",
                "第一段：「三十辐共一毂，当其无，有车之用。」三十根辐条汇到毂心，正因为毂心是空的，车才能转。结构的力量，不在塞满，在留空。",
            ),
            (
                "s2",
                "第二段：「埏埴以为器，当其无，有器之用。」揉土成器，因为中间是空的，才能装水、装饭。容器哲学：价值在容纳，不在壁厚。",
            ),
            (
                "s3",
                "第三段：「凿户牖以为室，当其无，有室之用。」开窗凿门，因为墙里有空，人才住得进去。建筑不是砌满，是划出可居之处。",
            ),
            (
                "s4",
                "第四段：「故有之以为利，无之以为用。」「有」带来便利、材料、可见的利；「无」才产生真正的功能。很多人只优化「有」，忘了「无」才是用武之地。",
            ),
            (
                "s5",
                "全章落点：无之以为用。轮子、碗、房间、团队流程、日程表——凡是能运转的，背后都有一块刻意留出的空。",
            ),
            (
                "open-ext1",
                "海德格尔谈「器具」：锤子顺手时，你几乎感觉不到它；你感觉到的是「在干活」。日本侘寂强调留白——不是缺，是让意义发生的空间。老子更早：当其无，才有用。",
            ),
            (
                "open-ext2",
                "回到今天。产品界面塞满按钮，日程表排满会议，组织不留冗余——短期看高效，长期看转不动。好的设计，是知道哪里该空：接口、缓冲、休息、未定义。",
            ),
            (
                "s-ext2",
                "领导者若把团队填到 100% 利用率，就没有应对变化的空。三十辐共一毂——辐条再密，毂心若堵死，车就废。",
            ),
            (
                "open-close",
                "四条认知补丁：第一，看见无：别只盯着可见部分。第二，设计空：功能来自容纳与流转。第三，有之为利：材料与结构要够。第四，无之为用：留白是核心能力。下一章，「五色令人目盲」——感官过载的代价。",
            ),
        ],
    },
    12: {
        "title_short": "五色令人目盲",
        "yt_tag": "五色令人目盲",
        "bili_dynamic": "刺激越多，感知越钝；为腹，不为目。",
        "desc_intro": "观念黑盒：《道德经》第十二章精解——圣人为腹不为目。",
        "sections": {
            "plain": "五色目盲；五音耳聋；畋猎心狂；难得行妨；为腹去彼。",
            "east_west": "斯宾诺莎情欲奴役；佛教六根。",
            "modern": "信息流、短视频、消费主义注意力。",
            "closing": "减刺激、养腹、去彼取此、守感知。",
        },
        "chapters": [
            ("承上：感官", "过渡 · 承上启下"),
            ("五段破译", "五段破译"),
            ("东西方互证", "东西方互证"),
            ("注意力", "信息过载"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [
            (
                "intro-bridge",
                "第十一章讲「无之用」——空处生功能。第十二章，老子转向输入端：「五色令人目盲，五音令人耳聋，五味令人口爽。」刺激越多，感知越钝。这一章，是注意力时代的先知文本。",
            ),
            ("open-1", "我们逐段破译。"),
            (
                "s1",
                "第一段：「五色令人目盲。」色彩过载，眼睛反而失去分辨。不是眼睛坏了，是神经系统被劫持——你看见很多，却什么也看不清。",
            ),
            (
                "s2",
                "第二段：「五音令人耳聋；五味令人口爽。」声音太杂，听不清关键；味道太重，味觉麻木。感官享受若变成无限叠加，会反向剥夺感受力。",
            ),
            (
                "s3",
                "第三段：「驰骋畋猎令人心发狂；难得之货令人行妨。」追逐狩猎让人心狂；稀缺之物让人走路都不安。刺激驱动行动，行动再要更多刺激——这是成瘾回路。",
            ),
            (
                "s4",
                "第四段：「是以圣人为腹不为目。」圣人养内在的腹——真实需求、根本满足；不追逐外在的目——炫耀、表象、给别人看。腹，是本体；目，是表演。",
            ),
            (
                "s5",
                "全章落点：「故去彼取此。」去掉追逐表象的那一端，守住滋养本体的那一端。不是禁欲，是止损感官通货膨胀。",
            ),
            (
                "open-ext1",
                "斯宾诺莎说人常被情欲奴役，以为自由其实在被推送。佛教讲六根接触生染，与「目盲耳聋」同向。老子不跟你讲理论，直接讲后果：刺激过量，感知破产。",
            ),
            (
                "open-ext2",
                "回到今天。无限信息流、15 秒钩子、红点通知——五色五音的数字化。你刷到凌晨，不是收获多，是目盲耳聋：对真实生活失去细腻触觉。",
            ),
            (
                "s-ext2",
                "消费主义让你为目而活：买给别人看、晒给别人看。为腹，是问：我真正需要的是什么？去彼取此，是主动卸载一层展示型欲望。",
            ),
            (
                "open-close",
                "四条认知补丁：第一，减刺激：别用更多输入修复空虚。第二，养腹：满足根本，不追逐表象。第三，去彼取此：卸载表演型欲望。第四，守感知：保护眼耳口的分辨力。下一章，「宠辱若惊」——ego 为何总被牵动。",
            ),
        ],
    },
    13: {
        "title_short": "宠辱若惊",
        "yt_tag": "宠辱若惊",
        "bili_dynamic": "你怕失去评价，是因为把「身」当成了全部。",
        "desc_intro": "观念黑盒：《道德经》第十三章精解——贵大患若身。",
        "sections": {
            "plain": "宠辱若惊；贵大患若身；及吾无身；贵身寄天下。",
            "east_west": "斯多葛控制二分；庄子齐物。",
            "modern": "社交评价焦虑、人设、职场荣辱。",
            "closing": "看淡宠辱、识身患、可寄天下、爱而不执。",
        },
        "chapters": [
            ("承上：荣辱", "过渡 · 承上启下"),
            ("五段破译", "五段破译"),
            ("东西方互证", "东西方互证"),
            ("评价焦虑", "宠辱"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [
            (
                "intro-bridge",
                "第十二章讲减刺激、为腹不为目。第十三章，老子戳最痛的点：「宠辱若惊，贵大患若身。」得宠惊慌，失宠也惊慌——因为你把「身」——自我、面子、肉身身份——放在了宇宙中心。",
            ),
            ("open-1", "我们逐段破译。"),
            (
                "s1",
                "第一段：「宠辱若惊。」受宠时惊，失宠时也惊。惊，不是兴奋，是系统不稳：你的价值感绑在外部反馈上，一有波动就报警。",
            ),
            (
                "s2",
                "第二段：「何谓宠辱若惊？宠为下，得之若惊，失之若惊，是谓宠辱若惊。」宠，在下位才受宠；得失都惊，说明你在下位却想要上位确认。荣辱都是他人定义的升降梯。",
            ),
            (
                "s3",
                "第三段：「何谓贵大患若身？吾所以有大患者，为吾有身，及吾无身，吾有何患？」大患，就是太把「身」当回事——身体、自我、人设、利益边界。若能不把身当作唯一实体，许多患就失去抓手。",
            ),
            (
                "s4",
                "第四段：「故贵以身为天下，若可寄天下；爱以身为天下，若可托天下。」把身看得与天下一样重，才能托付天下；爱惜身而不执，才能承载责任。不是轻贱自己，是不让 ego 劫持系统。",
            ),
            (
                "s5",
                "全章落点：能寄能托者，必先不被宠辱牵着走。领导力、创造力、关系，都怕一个人整天在「我有没有被看见」里震荡。",
            ),
            (
                "open-ext1",
                "斯多葛学派：分清你能控制的与不能控制的，荣辱属后者。庄子齐物：荣辱本是一体两面。老子更狠：问题不在荣辱大小，在你把「身」贵过了头。",
            ),
            (
                "open-ext2",
                "回到今天。一条差评失眠、一条点赞亢奋——宠辱若惊的社交版。人设就是「身」的延长线：它碎，你就惊。",
            ),
            (
                "s-ext2",
                "职场亦如此：被表扬就过度承诺，被批评就防御性甩锅。贵大患若身——你把职位、头衔、面子当成了存在的全部。",
            ),
            (
                "open-close",
                "四条认知补丁：第一，看淡宠辱：反馈是数据，不是判决书。第二，识身患：ego 过大，系统必惊。第三，可寄天下：责任来自稳态，不来自表演。第四，爱而不执：护住身，别膨胀身。下一章，「视之不见」——道的不可见维度。",
            ),
        ],
    },
    14: {
        "title_short": "视之不见名曰夷",
        "yt_tag": "视之不见名曰夷",
        "bili_dynamic": "最高级的底层，往往看不见、摸不着，却托住一切。",
        "desc_intro": "观念黑盒：《道德经》第十四章精解——执古之道以御今之有。",
        "sections": {
            "plain": "夷希微；混一；惚恍；无状之象；执古御今；道纪。",
            "east_west": "康德物自体；柏拉图理念。",
            "modern": "基础设施、协议、文化底层、暗数据。",
            "closing": "认夷希微、信惚恍、执古之道、知古始。",
        },
        "chapters": [
            ("承上：道体", "过渡 · 承上启下"),
            ("五段破译", "五段破译"),
            ("东西方互证", "东西方互证"),
            ("暗层基础", "不可见"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [
            (
                "intro-bridge",
                "第十三章讲宠辱与「身」。第十四章，老子描述道的感官属性：「视之不见名曰夷，听之不闻名曰希，搏之不得名曰微。」看不见、听不见、摸不到——却混而为一，托住万物。这是「不可见基础设施」的哲学版。",
            ),
            ("open-1", "我们逐段破译。"),
            (
                "s1",
                "第一段：夷、希、微——三种不可把握。不是不存在，是超出感官分辨率。你越想用眼睛抓住道，越抓不住。",
            ),
            (
                "s2",
                "第二段：「此三者不可致诘，故混而为一。」追问到底，只能承认：它们不是三个东西，是一个底层。分析到尽头，要回到整体。",
            ),
            (
                "s3",
                "第三段：「绳绳不可名，复归于无物，是谓无状之状，无物之象，是谓惚恍。」连绵无法命名，像回到无物——无固定形状的形状，无固定形象的形象。惚恍，不是模糊，是高于清晰的那一层。",
            ),
            (
                "s4",
                "第四段：「迎之不见其首，随之不见其后。」迎上去没有头，跟上去没有尾。道不是线性事件，不是你可以追赶的对象。",
            ),
            (
                "s5",
                "全章落点：「执古之道，以御今之有。能知古始，是谓道纪。」握住亘古不变之道，来驾驭当下之有。知古始，就是知系统底层规律——道纪。",
            ),
            (
                "open-ext1",
                "康德「物自体」不可被感性直观；柏拉图「理念」超越个别事物。老子不用抽象名词堆叠，直接说：道在你感官之外，却在万物运行之内。",
            ),
            (
                "open-ext2",
                "回到今天。互联网协议、电网、法律框架、组织文化——都是夷希微：平时看不见，一断就全乱。执古之道，是维护底层，不是追逐表层热点。",
            ),
            (
                "s-ext2",
                "个人成长亦然：价值观、睡眠、关系信任——惚恍的底层。你只优化可见的简历，却不修不可见的根，遇变就崩。",
            ),
            (
                "open-close",
                "四条认知补丁：第一，认夷希微：尊重不可见层。第二，信惚恍：别强求一切清晰可拍。第三，执古御今：用恒定规律驾驭变化。第四，知道纪：知古始，才知今之所系。下一章，「古之善为士者」——高手为何看起来钝。",
            ),
        ],
    },
    15: {
        "title_short": "古之善为士者",
        "yt_tag": "古之善为士者",
        "bili_dynamic": "真正的高手，像冬天过河、像冰将释——慎而徐清。",
        "desc_intro": "观念黑盒：《道德经》第十五章精解——浊以静之徐清。",
        "sections": {
            "plain": "豫犹俨涣敦旷混；浊静徐清；安动徐生；不欲盈；蔽不新成。",
            "east_west": "论语讷言敏行；禅宗慢工。",
            "modern": "急躁决策、表演型专业、慢系统。",
            "closing": "冬涉、畏邻、徐清徐生、不盈故成。",
        },
        "chapters": [
            ("承上：善士", "过渡 · 承上启下"),
            ("七容破译", "七容破译"),
            ("东西方互证", "东西方互证"),
            ("徐清徐生", "慢系统"),
            ("认知补丁", "认知补丁"),
        ],
        "scenes": [
            (
                "intro-bridge",
                "第十四章讲「夷希微」与道纪。第十五章，老子刻画「古之善为士者」：微妙玄通，深不可识——所以只能勉强形容其容：像冬天过河般谨慎，像怕四邻般警觉，像冰将释般放松。这一章，是高手的行为画像。",
            ),
            ("open-1", "我们逐段破译。"),
            (
                "s1",
                "第一段：「豫焉若冬涉川。」豫，是谨慎预备。冬天过河，步步试探——不是胆小，是对复杂系统的敬畏。",
            ),
            (
                "s2",
                "第二段：「犹兮若畏四邻；俨兮其若客；涣兮若冰之将释。」警觉如畏邻，庄重如作客，涣散如冰将融——紧而不僵，松而不散。",
            ),
            (
                "s3",
                "第三段：「敦兮其若朴；旷兮其若谷；混兮其若浊。」敦厚像未雕之木，空旷像山谷，混混沌沌像浊水——不急着把自己抛光成完美人设。",
            ),
            (
                "s4",
                "第四段：「孰能浊以静之徐清？孰能安以久动之徐生？」谁能浊中慢慢澄清？谁能安守很久而后缓缓生发？高手靠徐，不靠猛。",
            ),
            (
                "s5",
                "全章落点：「保此道者不欲盈。夫唯不盈，故能蔽不新成。」守此道的人不求满溢。正因为不满，所以能守旧功而不妄自翻新——可持续，不折腾。",
            ),
            (
                "open-ext1",
                "《论语》「讷于言而敏于行」，重内敛。禅宗强调慢参、渐悟。老子用七个比喻叠出：善士不是锋芒毕露，是冬涉、畏邻、若客、若谷——把速度降下来。",
            ),
            (
                "open-ext2",
                "回到今天。会议要立刻结论、平台要立刻爆款——人人追「新成」，不愿「徐清」。浊以静之：团队混乱时，先别加动作，先让系统沉淀。",
            ),
            (
                "s-ext2",
                "领导者若凡事表现「精明锐利」，往往不如敦朴若谷。混兮若浊，是允许阶段性的乱——给澄清留出时间。",
            ),
            (
                "open-close",
                "四条认知补丁：第一，冬涉：重大决策，步步试探。第二，徐清徐生：用慢变量解决浊与躁。第三，不欲盈：高光时不加满。第四，蔽不新成：守成，不瞎翻新。下一章，「致虚极」——观复与知常。",
            ),
        ],
    },
}


def used_images() -> set[str]:
    used: set[str] = set()
    for ch in range(1, 11):
        path = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"
        if not path.is_file():
            continue
        sb = json.loads(path.read_text(encoding="utf-8"))
        for s in sb.get("scenes", []):
            img = s.get("image")
            if img and "avatar" not in img:
                used.add(img)
    return used


def pick_images(ch: int) -> list[str]:
    used = used_images()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    avail = [img["file"] for img in catalog["images"] if img["file"] not in used]
    start = (ch - 11) * 11
    chunk = avail[start : start + 11]
    if len(chunk) < 11:
        raise SystemExit(f"第 {ch} 章可用配图不足 11 张（剩余 {len(avail)}，需从 {start} 起 11 张）")
    return chunk


_CN_NUM = (
    "",
    "一",
    "二",
    "三",
    "四",
    "五",
    "六",
    "七",
    "八",
    "九",
    "十",
    "十一",
    "十二",
    "十三",
    "十四",
    "十五",
)


def build_storyboard(ch: int, meta: dict) -> dict:
    imgs = pick_images(ch)
    scene_ids = [
        "intro-bridge",
        "open-1",
        "s1",
        "s2",
        "s3",
        "s4",
        "s5",
        "open-ext1",
        "open-ext2",
        "s-ext2",
        "open-close",
    ]
    scenes = []
    for i, (sid, narr) in enumerate(meta["scenes"]):
        scenes.append(
            {
                "id": sid,
                "narration": narr,
                "image": imgs[i],
                "pause_after_sec": 0.45
                if sid == "intro-bridge"
                else (0.4 if sid == "open-close" else 0.35),
            }
        )
    ch_labels = meta["chapters"]
    return {
        "title": f"观念黑盒：《道德经》第{_CN_NUM[ch]}章精解",
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
                for i, sid in enumerate(
                    ["intro-bridge", "open-1", "open-ext1", "open-ext2", "open-close"]
                )
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

    commentary_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Updated {commentary_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
