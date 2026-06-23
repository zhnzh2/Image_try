"""校验 & 预览工具：扫描 lines/ 下所有线路文件夹，检查格式并展示各线路的完整 prompt。

用法：
  python merge_prompts.py

会自动跳过 _template 文件夹。
"""

import json
from pathlib import Path


LINES_DIR = Path("lines")
CONFIG_PATH = LINES_DIR / "prompts.json"


def main() -> None:
    # 读取综述
    if not CONFIG_PATH.is_file():
        print(f"✗ 综述文件不存在：{CONFIG_PATH.resolve()}")
        return

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)

    common_prompt = config.get("common_prompt", "")
    print(f"项目：{config.get('project', '（未命名）')}")
    print(f"综述 prompt 长度：{len(common_prompt)} 字符")
    print()

    has_poster = config.get("poster", {}).get("prompt_template")

    # 扫描子文件夹
    found = 0
    for subdir in sorted(LINES_DIR.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue

        prompt_file = subdir / "prompts.json"
        if not prompt_file.is_file():
            print(f"⚠ {subdir.name}/ ：缺少 prompts.json")
            continue

        try:
            with prompt_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"✗ {subdir.name}/ ：JSON 解析失败 → {e}")
            continue

        if not isinstance(data, dict):
            print(f"✗ {subdir.name}/ ：不是 JSON 对象")
            continue

        line_id = data.get("id", "")
        line_name = data.get("name", "")
        line_specific = data.get("line_specific", "")
        poster_vars = data.get("poster_vars")

        missing = []
        if not line_id:
            missing.append("id")
        if not line_name:
            missing.append("name")
        if not line_specific.strip():
            missing.append("line_specific")
        if has_poster and not poster_vars:
            missing.append("poster_vars（海报模式需要）")

        if missing:
            print(f"✗ {subdir.name}/ ：缺少字段 {missing}")
            continue

        full_prompt = common_prompt + "\n" + line_specific.strip()
        found += 1

        print(f"✓ [{line_id}] {line_name}")
        print(f"  character_only prompt：{len(full_prompt)} 字符")

        if has_poster and poster_vars:
            poster_prompt = config["poster"]["prompt_template"]
            for k, v in poster_vars.items():
                poster_prompt = poster_prompt.replace("{{" + k + "}}", str(v))
            print(f"  poster prompt：{len(poster_prompt)} 字符")
            print(f"  poster_vars 字段：{list(poster_vars.keys())}")

        print()

    print(f"共扫描到 {found} 条有效线路。")
    if has_poster:
        print("海报模板已配置 ✓")


if __name__ == "__main__":
    main()
