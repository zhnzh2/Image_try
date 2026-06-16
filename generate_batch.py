"""批量生成 JR 线路拟人角色图鉴。

用法：
  1. 在 .env 文件中填入 OPENAI_API_KEY。
  2. 在 prompts.json 中编辑线路任务清单。
  3. 运行：python generate_batch.py
"""

import base64
import json
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)
from PIL import Image


# ====== 可调参数 ======

MODEL = "gpt-image-2"

# 1080 不是 16 的倍数，API 先生成 1088×1920，再居中裁切为 1080×1920。
API_SIZE = "1088x1920"
FINAL_SIZE = (1080, 1920)

# 草稿 / 快速迭代用 "low"，最终成品改成 "high"。
QUALITY = "low"

PROMPTS_PATH = Path("lines/prompts.json")
OUTPUT_DIR = Path("output")
RAW_DIR = OUTPUT_DIR / "raw"
FINAL_DIR = OUTPUT_DIR / "final"
MANIFEST_PATH = OUTPUT_DIR / "manifest.jsonl"

MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 10

# =========================


def load_client() -> OpenAI:
    """读取 .env 中的 API Key 并初始化 OpenAI 客户端。"""
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "在这里填入你的API_Key":
        raise RuntimeError(
            "请先在项目根目录的 .env 文件中填入真实 OpenAI API Key。"
        )

    return OpenAI(
        api_key=api_key,
        timeout=300.0,
    )


def load_tasks() -> list[dict[str, str]]:
    """从 prompts.json 读取并校验任务清单。"""
    if not PROMPTS_PATH.is_file():
        raise FileNotFoundError(f"任务文件不存在：{PROMPTS_PATH.resolve()}")

    with PROMPTS_PATH.open("r", encoding="utf-8") as file:
        tasks = json.load(file)

    if not isinstance(tasks, list):
        raise ValueError("prompts.json 顶层必须是 JSON 数组。")

    required_keys = {"id", "name", "prompt"}

    for index, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            raise ValueError(f"第 {index} 项必须是 JSON 对象。")

        missing_keys = required_keys - task.keys()
        if missing_keys:
            missing = ", ".join(sorted(missing_keys))
            raise ValueError(f"第 {index} 项缺少字段：{missing}")

        for key in required_keys:
            if not isinstance(task[key], str) or not task[key].strip():
                raise ValueError(f"第 {index} 项的 {key} 必须是非空字符串。")

    return tasks


def append_manifest(record: dict) -> None:
    """追加一条记录到 manifest.jsonl。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with MANIFEST_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
        file.flush()


def crop_to_final_size(raw_path: Path, final_path: Path) -> None:
    """将 API 原图居中裁切为 FINAL_SIZE。"""
    with Image.open(raw_path) as image:
        image = image.convert("RGB")

        source_width, source_height = image.size
        target_width, target_height = FINAL_SIZE

        if source_width < target_width or source_height < target_height:
            raise ValueError(
                f"原图尺寸 {image.size} 小于目标尺寸 {FINAL_SIZE}，无法裁切。"
            )

        left = (source_width - target_width) // 2
        top = (source_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        cropped = image.crop((left, top, right, bottom))
        cropped.save(final_path, format="PNG")


def generate_one(
    client: OpenAI,
    task: dict[str, str],
    raw_path: Path,
) -> None:
    """调用 API 生成一张图片并保存 raw 文件。"""
    result = client.images.generate(
        model=MODEL,
        prompt=task["prompt"],
        size=API_SIZE,
        quality=QUALITY,
    )

    if not result.data:
        raise RuntimeError("API 返回的数据列表为空。")

    image_base64 = result.data[0].b64_json
    if not image_base64:
        raise RuntimeError("API 响应中没有 b64_json 图片数据。")

    raw_path.write_bytes(base64.b64decode(image_base64))


def main() -> None:
    client = load_client()
    tasks = load_tasks()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    total = len(tasks)
    succeeded = 0
    skipped = 0
    failed = 0

    print(f"共读取到 {total} 个任务。")
    print(f"模型：{MODEL}")
    print(f"API 尺寸：{API_SIZE}")
    print(f"最终尺寸：{FINAL_SIZE[0]}x{FINAL_SIZE[1]}")
    print(f"质量：{QUALITY}")
    print()

    for index, task in enumerate(tasks, start=1):
        task_id = task["id"]
        task_name = task["name"]

        raw_path = RAW_DIR / f"{task_id}.png"
        final_path = FINAL_DIR / f"{task_id}.png"

        print(f"[{index}/{total}] {task_name}")

        # 已有最终结果的直接跳过，避免重复收费。
        if final_path.is_file():
            print(f"  跳过：最终文件已存在 → {final_path}")
            skipped += 1
            continue

        started_at = datetime.now().astimezone().isoformat()
        start_time = time.monotonic()
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"  正在请求生成，第 {attempt}/{MAX_RETRIES} 次……")

                generate_one(
                    client=client,
                    task=task,
                    raw_path=raw_path,
                )

                crop_to_final_size(
                    raw_path=raw_path,
                    final_path=final_path,
                )

                elapsed_seconds = round(time.monotonic() - start_time, 2)

                append_manifest(
                    {
                        "id": task_id,
                        "name": task_name,
                        "status": "success",
                        "model": MODEL,
                        "api_size": API_SIZE,
                        "final_size": f"{FINAL_SIZE[0]}x{FINAL_SIZE[1]}",
                        "quality": QUALITY,
                        "raw_path": str(raw_path),
                        "final_path": str(final_path),
                        "started_at": started_at,
                        "elapsed_seconds": elapsed_seconds,
                    }
                )

                print(f"  完成 → {final_path}")
                print(f"  用时：{elapsed_seconds} 秒")
                succeeded += 1
                break

            except (
                RateLimitError,
                APITimeoutError,
                APIConnectionError,
                APIStatusError,
            ) as error:
                last_error = error
                print(f"  API 请求失败：{type(error).__name__}: {error}")

                if attempt < MAX_RETRIES:
                    print(f"  {RETRY_WAIT_SECONDS} 秒后重试……")
                    time.sleep(RETRY_WAIT_SECONDS)

            except Exception as error:
                last_error = error
                print(f"  任务失败：{type(error).__name__}: {error}")
                break

        # 所有重试后仍未成功，记录失败。
        if not final_path.is_file():
            elapsed_seconds = round(time.monotonic() - start_time, 2)

            append_manifest(
                {
                    "id": task_id,
                    "name": task_name,
                    "status": "failed",
                    "model": MODEL,
                    "api_size": API_SIZE,
                    "final_size": f"{FINAL_SIZE[0]}x{FINAL_SIZE[1]}",
                    "quality": QUALITY,
                    "started_at": started_at,
                    "elapsed_seconds": elapsed_seconds,
                    "error_type": (
                        type(last_error).__name__
                        if last_error is not None
                        else "UnknownError"
                    ),
                    "error_message": (
                        str(last_error)
                        if last_error is not None
                        else "没有获得明确错误信息。"
                    ),
                }
            )

            failed += 1

        print()

    print("========== 批次完成 ==========")
    print(f"成功：{succeeded}")
    print(f"跳过：{skipped}")
    print(f"失败：{failed}")
    print(f"总数：{total}")
    print(f"成品目录：{FINAL_DIR.resolve()}")
    print(f"运行记录：{MANIFEST_PATH.resolve()}")


if __name__ == "__main__":
    main()
