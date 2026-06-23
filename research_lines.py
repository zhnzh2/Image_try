"""分批调查 JR 东日本全部线路 → output/jr_east_lines_detail.txt（使用 DeepSeek）。"""

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

# 6 批线路分组
BATCHES = [
    {
        "title": "新干线",
        "lines": "东北新干线、上越新干线、北陆新干线、山形新干线、秋田新干线",
    },
    {
        "title": "首都圈主要干线（东京核心区）",
        "lines": "山手线、京滨东北线·根岸线、中央快速线、中央·总武缓行线、常磐线（快速/缓行）、总武本线/总武快速线、东海道线（首都圈段）、宇都宫线/东北本线（首都圈段）、高崎线、横须贺线",
    },
    {
        "title": "首都圈主要干线（外围与贯通系统）",
        "lines": "埼京线、湘南新宿线、上野东京线、京叶线、武藏野线、南武线、横滨线、青梅线、五日市线、鹤见线、川越线、相模线、八高线、成田线",
    },
    {
        "title": "首都圈其他线路与地方干线",
        "lines": "东金线、内房线、外房线、久留里线、鹿岛线、乌山线、日光线、水郡线、水户线、两毛线、吾妻线、伊东线、上越线、信越本线、篠之井线、羽越本线、白新线、磐越西线、仙山线、仙石线、奥羽本线/山形线、田泽湖线、左泽线、大糸线（JR东日本段）、八户线、大凑线、津轻线",
    },
    {
        "title": "地方交通线（一）",
        "lines": "小海线、饭山线、越后线、弥彦线、米坂线、只见线、磐越东线、石卷线、陆羽东线、陆羽西线、北上线、釜石线、山田线、花轮线、男鹿线、五能线",
    },
    {
        "title": "地方交通线（二）与 BRT",
        "lines": "气仙沼线BRT、大船渡线BRT。最后附上一个按开通年份排序的 JR 东日本全线路年表（包含以上所有线路，格式：年份 - 线名 - 首段区间）。",
    },
]

SYSTEM_PROMPT = """你是 JR 东日本铁路研究专家。请整理指定线路的详细信息。

每条线路必须包含以下字段（确实不知道则标注"暂缺"）：

- 中文线名 / 日文线名
- 线路编号/爱称（如 JY、JK、JC 等）
- 首段开通年份
- 起终点及主要经由地
- 营业里程（公里）
- 线路地位与角色（核心动脉/通勤干线/观光/地方支线等）
- 使用车型（型号、编组辆数、是否有绿色车）
- 直通运行关系
- 代表色/线路色
- 趣事/特色（历史趣事、著名车站、独特运行方式等）
- 拟人设定建议（一句话概括角色气质）

风格参考（项目是"JR东日本线路拟人角色图鉴"）：
- 山手线：东京心脏的环形女王，黄绿色，E235系，都市偶像风
- 东海道线：元祖大姐，湘南橙绿，沉稳可靠，日本铁路起点
- 中央快速线：橙色疾风，急性子特快少女，E233系
- 京滨东北线：天空蓝通勤班长，守时严谨
- 鹤见线：工业区幽灵姬，海芝浦隐藏名所

要求：
- 用中文输出
- 同一批内按开通年份从早到晚排列
- 直接开始，不要开场白"""


def ask_batch(title: str, lines: str, batch_num: int) -> str:
    """向 DeepSeek 请求一批线路的详细信息。"""
    user_prompt = f"请整理以下 JR 东日本 {title} 的详细信息：\n\n{lines}"

    print(f"\n[批次 {batch_num}/6] {title}", flush=True)
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
            print(f"  ✗ 第 {attempt} 次失败：{type(e).__name__}: {e}")
            if attempt < 3:
                wait = 15 * attempt
                print(f"  等待 {wait} 秒……")
                time.sleep(wait)
            else:
                print(f"  批次放弃")
                return f"\n\n## {title}\n\n（此批次因网络问题未能完成，请稍后重试）\n"


def main():
    all_results = []

    print("=" * 50)
    print("JR 东日本全线路调研（DeepSeek 分批模式）")
    print(f"共 {len(BATCHES)} 个批次")
    print("=" * 50)

    for i, batch in enumerate(BATCHES, 1):
        result = ask_batch(batch["title"], batch["lines"], i)
        all_results.append(f"## {batch['title']}\n\n{result}")
        if i < len(BATCHES):
            time.sleep(1)

    # 合并输出
    output_path = Path("output/jr_east_lines_detail.txt")
    full_output = "\n\n".join(all_results)
    output_path.write_text(full_output, encoding="utf-8")

    print(f"\n{'=' * 50}")
    print(f"全部完成！")
    print(f"结果：{output_path.resolve()}")
    print(f"总长度：{len(full_output)} 字符")


if __name__ == "__main__":
    main()
