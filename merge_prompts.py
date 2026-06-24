"""校验 & 预览工具：扫描 lines/ 下所有线路文件夹，检查 character_only 和 poster 两套模板的变量完整性。

用法：python merge_prompts.py
"""

import json
from pathlib import Path


LINES_DIR = Path("lines")
CONFIG_PATH = LINES_DIR / "prompts.json"


def main() -> None:
    if not CONFIG_PATH.is_file():
        print(f"✗ 配置文件不存在：{CONFIG_PATH.resolve()}")
        return

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)

    project = config.get("project", "（未命名）")
    has_poster = bool(config.get("poster", {}).get("prompt_template"))
    has_character_only = bool(config.get("character_only", {}).get("prompt_template"))
    has_common = bool(config.get("common_prompt"))

    print(f"项目：{project}")
    print(f"poster 模板：{'✓' if has_poster else '✗ 未配置'}")
    print(f"character_only 模板：{'✓' if has_character_only else '✗ 未配置（fallback 到 common_prompt + line_specific）'}")
    print(f"common_prompt（legacy）：{'✓' if has_common else '✗ 未配置'}")
    print()

    # 模板变量名收集
    poster_vars_needed = set()
    char_vars_needed = set()
    if has_poster:
        t = config["poster"]["prompt_template"]
        poster_vars_needed = {w.split("}}")[0] for w in t.split("{{") if "}}" in w}
    if has_character_only:
        t = config["character_only"]["prompt_template"]
        char_vars_needed = {w.split("}}")[0] for w in t.split("{{") if "}}" in w}

    if poster_vars_needed:
        print(f"poster 模板变量（{len(poster_vars_needed)} 个）：{sorted(poster_vars_needed)}")
    if char_vars_needed:
        print(f"character_only 模板变量（{len(char_vars_needed)} 个）：{sorted(char_vars_needed)}")
    all_needed = poster_vars_needed | char_vars_needed
    if all_needed:
        print(f"合并去重（{len(all_needed)} 个）：{sorted(all_needed)}")
    print()

    # 扫描线路
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
        poster_vars = data.get("poster_vars", {})

        missing = []
        if not line_id:
            missing.append("id")
        if not line_name:
            missing.append("name")

        # 检查 poster_vars 是否覆盖所有模板变量
        if poster_vars and all_needed:
            missing_vars = all_needed - set(poster_vars.keys())
            if missing_vars:
                missing.append(f"poster_vars 缺少字段：{sorted(missing_vars)}")

        # 如果没有 poster_vars 也没有 line_specific，警告
        if not poster_vars and not data.get("line_specific"):
            missing.append("poster_vars 或 line_specific（至少需要一个）")

        if missing:
            print(f"✗ {subdir.name}/ ：{'; '.join(missing)}")
            continue

        found += 1

        print(f"✓ [{line_id}] {line_name}")
        if poster_vars:
            print(f"  poster_vars：{len(poster_vars)} 个字段，覆盖 {len(poster_vars.keys() & all_needed)}/{len(all_needed)} 个所需变量")
        if data.get("line_specific"):
            print(f"  line_specific：{len(data['line_specific'])} 字符（legacy）")
        print()

    print(f"共扫描到 {found} 条有效线路。")


if __name__ == "__main__":
    main()
