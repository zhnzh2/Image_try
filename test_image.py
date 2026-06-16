"""单张图片测试脚本 —— 确认 API Key、提示词和裁切流程是否正常。"""

import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key or api_key == "在这里填入你的API_Key":
    raise RuntimeError(
        "请先在项目根目录的 .env 文件中填入真实 OpenAI API Key。"
    )

client = OpenAI(api_key=api_key)

output_dir = Path("output")
output_dir.mkdir(parents=True, exist_ok=True)

prompt = """
生成一张竖版动漫角色图鉴插画。

主题：JR东日本山手线拟人角色。
角色：成年女性，沉稳、自信、可靠，具有东京核心环线的都市感。
主色调：山手线黄绿色。
构图：角色全身立绘，站在现代东京车站环境中。
画面比例：9:16竖版。
画面中不要出现任何文字、标志、水印或边框。
"""

print("正在请求生成图片……")

result = client.images.generate(
    model="gpt-image-2",
    prompt=prompt,
    size="1088x1920",
    quality="low",
)

image_base64 = result.data[0].b64_json
image_bytes = base64.b64decode(image_base64)

output_path = output_dir / "test_yamanote_raw.png"
output_path.write_bytes(image_bytes)

print(f"生成完成：{output_path.resolve()}")
