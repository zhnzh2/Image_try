"""单张图片测试脚本 —— 读取综述 + 山手线 prompt，生成一张测试图。

前提：.env 中已填入 OPENAI_API_KEY。
"""

import base64
import json
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

# 读取综述
config_path = Path("lines/prompts.json")
with config_path.open("r", encoding="utf-8") as f:
    config = json.load(f)
common_prompt = config["common_prompt"]

# 读取山手线特征
line_path = Path("lines/01_yamanote/prompts.json")
with line_path.open("r", encoding="utf-8") as f:
    line_data = json.load(f)

full_prompt = common_prompt + "\n" + line_data["line_specific"].strip()

output_dir = Path("output")
output_dir.mkdir(parents=True, exist_ok=True)

print(f"线路：{line_data['name']}")
print(f"完整 prompt 长度：{len(full_prompt)} 字符")
print("正在请求生成图片……")

result = client.images.generate(
    model="gpt-image-2",
    prompt=full_prompt,
    size="1088x1920",
    quality="low",
)

image_base64 = result.data[0].b64_json
image_bytes = base64.b64decode(image_base64)

output_path = output_dir / "test_yamanote_raw.png"
output_path.write_bytes(image_bytes)

print(f"生成完成：{output_path.resolve()}")
