"""批量生成 JR 线路拟人角色图鉴。

工作流：
  1. 在 .env 文件中填入 OPENAI_API_KEY。
  2. 编辑 lines/prompts.json —— 项目综述 + 海报模板（poster 模式）。
  3. 在 lines/<线路名>/prompts.json 中编辑每条线路的角色特征和海报变量。
  4. 切换模式：修改顶部 MODE = "character_only" 或 "poster"
  5. 运行：python generate_batch.py

模式说明：
  character_only —— 仅生成角色立绘（无文字排版）
  poster         —— 生成完整图鉴海报（含信息面板、路线图、小剧场等）
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

# 生成模式：character_only（仅角色立绘） 或 poster（完整图鉴海报）
MODE = "poster"

MODEL = "gpt-image-2"

# 1080 不是 16 的倍数，API 先生成 1088×1920，再居中裁切为 1080×1920。
API_SIZE = "1088x1920"
FINAL_SIZE = (1080, 1920)

# 草稿 / 快速迭代用 "low"，最终成品改成 "high"。
QUALITY = "low"

LINES_DIR = Path("lines")
CONFIG_PATH = LINES_DIR / "prompts.json"
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


def load_project_config() -> dict:
    """读取 lines/prompts.json 中的项目综述。"""
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"项目配置文件不存在：{CONFIG_PATH.resolve()}")

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)

    if not isinstance(config, dict):
        raise ValueError("lines/prompts.json 顶层必须是 JSON 对象。")

    if "common_prompt" not in config:
        raise ValueError("lines/prompts.json 中缺少 common_prompt 字段。")

    return config


def build_poster_prompt(poster_config: dict, poster_vars: dict) -> str:
    """将海报模板中的 {{变量}} 替换为线路实际值。"""
    template = poster_config["prompt_template"]
    for key, value in poster_vars.items():
        template = template.replace("{{" + key + "}}", str(value))
    # 追加防翻车补充
    anti_failure = poster_config.get("anti_failure", "")
    if anti_failure:
        template = template + "\n\n" + anti_failure
    return template


def load_tasks(config: dict, mode: str) -> list[dict[str, str]]:
    """扫描 lines/ 下各子文件夹，根据 mode 构建不同 prompt。

    mode = character_only: 综述 common_prompt + line_specific
    mode = poster:         海报模板 + poster_vars 替换
    """
    if not LINES_DIR.is_dir():
        raise FileNotFoundError(f"lines/ 目录不存在：{LINES_DIR.resolve()}")

    tasks: list[dict[str, str]] = []
    common_prompt = config.get("common_prompt", "")
    poster_config = config.get("poster", {})

    for subdir in sorted(LINES_DIR.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue

        prompt_file = subdir / "prompts.json"
        if not prompt_file.is_file():
            print(f"⚠ 跳过 {subdir.name}/：没有 prompts.json")
            continue

        try:
            with prompt_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"✗ {subdir.name}/prompts.json JSON 解析失败：{e}")
            continue

        if not isinstance(data, dict):
            print(f"✗ {subdir.name}/prompts.json 必须是 JSON 对象，跳过")
            continue

        task_id = data.get("id", subdir.name)
        task_name = data.get("name", subdir.name)

        if mode == "poster":
            poster_vars = data.get("poster_vars")
            if not poster_vars or not isinstance(poster_vars, dict):
                print(f"✗ {subdir.name}/ 缺少 poster_vars，跳过")
                continue
            if not poster_config or not poster_config.get("prompt_template"):
                raise RuntimeError(
                    "lines/prompts.json 中缺少 poster.prompt_template。"
                    "请确认 poster 模式的模板已配置。"
                )
            full_prompt = build_poster_prompt(poster_config, poster_vars)
        else:
            # character_only（默认）
            line_specific = data.get("line_specific", "")
            if not line_specific.strip():
                print(f"✗ {subdir.name}/ 缺少 line_specific，跳过")
                continue
            full_prompt = common_prompt + "\n" + line_specific.strip()

        tasks.append({
            "id": task_id,
            "name": task_name,
            "prompt": full_prompt,
        })

    if not tasks:
        raise RuntimeError(
            "没有找到任何有效线路。请在 lines/ 下为每条线路创建子文件夹，"
            "并在其中放入 prompts.json（参考 lines/_template/prompts.json）。"
        )

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
    config = load_project_config()
    tasks = load_tasks(config, MODE)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    total = len(tasks)
    succeeded = 0
    skipped = 0
    failed = 0

    print(f"项目：{config.get('project', '（未命名）')}")
    print(f"模式：{MODE}")
    print(f"共扫描到 {total} 条线路。")
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
