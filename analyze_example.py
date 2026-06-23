"""分析 example.png：调用 GPT 视觉模型，输出全部特征到 output/example_analysis.txt。"""

import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key or api_key == "在这里填入你的API_Key":
    raise RuntimeError("请先在 .env 中填入 OPENAI_API_KEY。")

client = OpenAI(api_key=api_key)

# 读取示例图片并编码为 base64
image_path = Path("output/example.png")
if not image_path.is_file():
    raise FileNotFoundError(f"示例图片不存在：{image_path.resolve()}")

image_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")

prompt = """你是一位专业的插画与视觉设计分析师。请客观、技术性地分析所附图片的设计特征。

请严格按以下结构输出，用中文：

## 一、整体概览
- 尺寸比例与格式
- 整体风格类型（如日系赛璐璐、写实、平面设计等）
- 整体氛围和第一印象

## 二、人物设计
- 性别、年龄段、体型
- 发型发色、瞳色、面部特征
- 服装款式、配色、装饰细节、材质感
- 姿势、体态、表情
- 人物在画面中的位置和占比

## 三、背景设计
- 场景类型与环境元素
- 背景与人物的空间关系
- 景深处理

## 四、色彩设计
- 主色调与辅助色（尽可能给出具体色值范围）
- 饱和度与明度倾向
- 冷暖调比例
- 光影与明暗处理方式

## 五、构图与空间布局
- 构图方式
- 视觉重心位置
- 留白区域分布
- 是否有隐形的排版网格结构

## 六、文字与图形元素
- 画面中所有文字内容、字体风格、位置
- Logo、标志、符号、水印

## 七、绘画技法
- 线条特征（粗细、均匀性、手绘感）
- 上色技法（平涂/厚涂/渐变）
- 特效与滤镜感

## 八、批量化参考总结
- 哪些特征是这一系列图鉴必须保持一致的
- 哪些特征可以随线路变化

请直接开始分析，不要输出"无法分析"之类的开场白。"""

print("正在上传图片并分析……")

response = client.chat.completions.create(
    model="gpt-5.5",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}",
                        "detail": "high",
                    },
                },
            ],
        }
    ],
    max_completion_tokens=4096,
)

analysis = response.choices[0].message.content

output_path = Path("output/example_analysis.txt")
output_path.write_text(analysis, encoding="utf-8")

print(f"分析完成，结果已保存到：{output_path.resolve()}")
print(f"共 {len(analysis)} 字符")
