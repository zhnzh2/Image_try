"""合并工具：扫描 lines/ 下所有子文件夹的 prompts.json，合并到 lines/prompts.json。

用法：
  python merge_prompts.py

会自动跳过 _template 文件夹和无效文件。
"""

import json
from pathlib import Path


LINES_DIR = Path("lines")
OUTPUT_PATH = LINES_DIR / "prompts.json"


def merge() -> None:
    if not LINES_DIR.is_dir():
        raise FileNotFoundError(f"lines/ 目录不存在：{LINES_DIR.resolve()}")

    all_tasks: list[dict] = []

    for subdir in sorted(LINES_DIR.iterdir()):
        # 只处理文件夹，跳过 _template
        if not subdir.is_dir():
            continue
        if subdir.name.startswith("_"):
            continue

        prompt_file = subdir / "prompts.json"
        if not prompt_file.is_file():
            print(f"⚠ 跳过：{subdir.name}/ 中没有 prompts.json")
            continue

        try:
            with prompt_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"✗ JSON 解析失败：{prompt_file} → {e}")
            continue

        # 支持单对象或数组
        if isinstance(data, list):
            tasks = data
        elif isinstance(data, dict):
            tasks = [data]
        else:
            print(f"✗ 格式错误（需为对象或数组）：{prompt_file}")
            continue

        for task in tasks:
            # 精简输出：只保留 generate_batch.py 需要的三个字段
            cleaned = {
                "id": task.get("id", subdir.name),
                "name": task.get("name", subdir.name),
                "prompt": task.get("prompt", ""),
            }
            all_tasks.append(cleaned)

        print(f"✓ {subdir.name}")

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(all_tasks, f, ensure_ascii=False, indent=2)

    print(f"\n合并完成，共 {len(all_tasks)} 条线路 → {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    merge()
