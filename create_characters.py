"""为每条 JR 东日本线路撰写详细角色设定文案 → output/jr_east_character_profiles.txt"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key or "在这里填入" in api_key:
    raise RuntimeError("请先在 .env 中填入 DEEPSEEK_API_KEY。")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
    timeout=600.0,
)

# 读取调研资料作为参考
research = Path("output/jr_east_lines_detail.txt").read_text(encoding="utf-8")
style_ref = Path("output/reference1.txt").read_text(encoding="utf-8")[:6000]

# 线路批次（比调研时更多批，因为每条线角色设定更长）
BATCHES = [
    {
        "title": "新干线",
        "lines": "东北新干线、上越新干线、北陆新干线、山形新干线、秋田新干线",
    },
    {
        "title": "首都圈核心干线（环线与南北轴）",
        "lines": "山手线、京滨东北线·根岸线、中央快速线、中央·总武缓行线",
    },
    {
        "title": "首都圈核心干线（东西轴与放射线）",
        "lines": "常磐线（快速/缓行）、总武本线/总武快速线、东海道线（首都圈段）、横须贺线",
    },
    {
        "title": "首都圈核心干线（北关东方向）",
        "lines": "宇都宫线/东北本线（首都圈段）、高崎线、埼京线、川越线",
    },
    {
        "title": "首都圈贯通系统与外环",
        "lines": "湘南新宿线、上野东京线、京叶线、武藏野线",
    },
    {
        "title": "首都圈外围线路",
        "lines": "南武线、横滨线、青梅线、五日市线、鹤见线、相模线、八高线、成田线",
    },
    {
        "title": "首都圈房总方向",
        "lines": "东金线、内房线、外房线、久留里线、鹿岛线",
    },
    {
        "title": "北关东地方线路",
        "lines": "乌山线、日光线、水郡线、水户线、两毛线、吾妻线、伊东线",
    },
    {
        "title": "上越·信越地方干线",
        "lines": "上越线、信越本线、篠之井线、羽越本线、白新线",
    },
    {
        "title": "东北地方干线",
        "lines": "磐越西线、仙山线、仙石线、奥羽本线/山形线、田泽湖线、左泽线",
    },
    {
        "title": "地方交通线（甲信越）",
        "lines": "小海线、饭山线、大糸线（JR东日本段）、越后线、弥彦线、米坂线",
    },
    {
        "title": "地方交通线（东北·太平洋侧）",
        "lines": "只见线、磐越东线、石卷线、陆羽东线、陆羽西线",
    },
    {
        "title": "地方交通线（东北·日本海侧与内陆）",
        "lines": "北上线、釜石线、山田线、花轮线、八户线、大凑线、津轻线、男鹿线、五能线",
    },
    {
        "title": "BRT线路",
        "lines": "气仙沼线BRT、大船渡线BRT",
    },
]

SYSTEM_PROMPT = f"""你是 JR 东日本铁路文化专家和角色设计师。请根据调研资料，为指定线路撰写详细的"线路拟人角色设定"。

## 风格要求

每条线路的设定不是单纯的"萌妹化"，而是把线路的历史、职能、经由地、车型、客流气质、趣事全部转化成有血有肉的人设。参考以下范例格式和深度：

{style_ref}

## 每条线路用以下模板

### [序号]. [中文线名] / [日文线名] [线路编号]

**拟人名**：[日式风格的角色名，与线路气质匹配]

**源流年份**：[首段开通年份]
**年龄设定**：[基于开通年份在JR东日本家族中的辈分描述，如"元祖级大姐""明治老牌姐姐""平成新生代"等]

**基本信息**：
[用一段话概括线路的核心信息——起终点、经由地、里程、地位、主力车型和编组。用自然段落叙述，不是列表。包含：
- 线路连接的城市/区域
- 在首都圈/JR东日本网络中的角色
- 主力车型、编组辆数、是否有绿色车、特色车辆
- 与其他线路的直通关系]

**角色设定**：
[详细的外观设定——主色调取自线路代表色，服装设计融合线路途经地的地理/文化/历史元素，发型发色、配饰与线路特色呼应。道具可以体现线路特点（如环线地图、特急标识、工业元素等）。用生动的文学性语言描述。]

**性格**：
[性格特征从线路职能和客流气质中提炼——通勤线则干练/守时，观光线则悠闲/浪漫，工业线则务实/低调，机场线则国际化/时髦。包含：
- 核心性格特质及其与线路的对应关系
- 一句口头禅/经典台词
- 与其他线路角色的关系（兄弟姐妹/搭档/对手等）]

**人设关键词**：
[5-7个关键词，提炼核心元素]

---

## 参考调研资料
{research}

## 规则
- 用中文撰写，日语线名和角色名保留日文汉字
- 按开通年份从早到晚排列
- 年龄感：1870s-1890s=元祖级，1900s-1920s=大正·昭和初期，1930s-1960s=昭和中期，1970s-1990s=昭和末·平成初，2000s+=平成·令和新世代
- 直接输出，不要开场白和结尾总结"""


def ask_batch(title: str, lines: str, batch_num: int, total: int) -> str:
    user_prompt = f"请为以下 JR 东日本 {title} 撰写详细的角色设定：\n\n{lines}"

    print(f"\n[批次 {batch_num}/{total}] {title}", flush=True)
    print(f"  请求中……", flush=True)

    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=8000,
            )
            result = response.choices[0].message.content
            print(f"  ✓ 完成，{len(result)} 字符", flush=True)
            return result
        except Exception as e:
            print(f"  ✗ 第 {attempt} 次失败：{type(e).__name__}: {e}", flush=True)
            if attempt < 3:
                wait = 15 * attempt
                print(f"  等待 {wait} 秒……", flush=True)
                time.sleep(wait)
            else:
                print(f"  批次放弃", flush=True)
                return f"\n\n## {title}\n\n（此批次未能完成，请稍后重试）\n"


def main():
    all_results = []
    total = len(BATCHES)

    print("=" * 60, flush=True)
    print("JR 东日本全线路角色设定生成（DeepSeek V4 Pro）", flush=True)
    print(f"共 {total} 个批次", flush=True)
    print("=" * 60, flush=True)

    for i, batch in enumerate(BATCHES, 1):
        result = ask_batch(batch["title"], batch["lines"], i, total)
        all_results.append(f"## {batch['title']}\n\n{result}")
        if i < total:
            time.sleep(1)

    # 合并输出
    output_path = Path("output/jr_east_character_profiles.txt")
    full_output = "\n\n".join(all_results)
    output_path.write_text(full_output, encoding="utf-8")

    print(f"\n{'=' * 60}", flush=True)
    print(f"全部完成！", flush=True)
    print(f"结果：{output_path.resolve()}", flush=True)
    print(f"总长度：{len(full_output)} 字符", flush=True)


if __name__ == "__main__":
    main()
