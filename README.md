# JR 东日本线路拟人角色图鉴批量生成项目

将 JR 东日本全部线路拟人化为动漫角色，通过 OpenAI 图像生成 API 批量产出统一风格的图鉴海报。

## 项目结构

```
JR/
├── build_all_lines.py            # 从角色设定文件自动生成 lines/<线路>/prompts.json
├── generate_batch.py             # 批量调用 API 生成图片
├── merge_prompts.py              # 校验所有 prompts.json 的模板变量完整性
├── .env                          # OPENAI_API_KEY（需自行创建）
├── lines/
│   ├── prompts.json              # 项目综述 + poster/character_only 两套 Prompt 模板
│   ├── _template/                # 单条线路 prompts.json 的字段参考模板
│   ├── 01_东北新干线/             # 每条线路一个文件夹
│   │   └── prompts.json          #   线路元数据 + 角色设定（V2 格式）
│   ├── ...
│   └── 64_石卷线/
│       └── prompts.json
└── output/
    ├── raw/                      # API 返回的原图（1088×1920）
    ├── final/                    # 裁切后的成品（1080×1920）
    ├── manifest.jsonl            # 每次运行的生成记录
    ├── jr_east_character_profiles.txt   # 全局角色设定原文（63 条线路）
    └── jr_east_lines_detail.txt         # 线路技术数据（23 条线路）
```

## 快速开始

### 1. 配置 API Key

在项目根目录创建 `.env` 文件：

```
OPENAI_API_KEY=sk-your-key-here
```

### 2. 校验数据完整性

```bash
python merge_prompts.py
```

确保输出 `共扫描到 64 条有效线路`，且每条线路 `覆盖 19/19 个所需变量`。

### 3. 生成图片

编辑 `generate_batch.py` 顶部的可调参数：

```python
MODE = "poster"          # poster（完整图鉴海报）或 character_only（仅角色立绘）
MODEL = "gpt-image-2"    # 模型
QUALITY = "low"          # low（快速测试）或 high（最终成品）
```

然后运行：

```bash
python generate_batch.py
```

成品图片输出到 `output/final/`，生成记录写入 `output/manifest.jsonl`。

## 三条核心脚本

| 脚本 | 用途 | 何时使用 |
|------|------|----------|
| `build_all_lines.py` | 解析 `output/jr_east_character_profiles.txt`，自动为每条线路生成 `lines/<id>/prompts.json` | 角色设定文件有更新时 |
| `generate_batch.py` | 读取所有线路的 `prompts.json`，逐条调用 OpenAI 图像生成 API | 每次生成图片时 |
| `merge_prompts.py` | 扫描 `lines/` 下所有文件夹，检查每个 `prompts.json` 是否覆盖模板所需全部变量 | 修改模板或线路数据后验证 |

## prompts.json 数据格式（V2）

每条线路的 `prompts.json` 包含：

```json
{
  "id": "06_山手线",
  "name": "山手线",
  "name_ja": "山手線",
  "line_specific": "JR东日本山手线。主色黄绿（#9ACD32）。全长34.5 km。源流1885年。",
  "poster_vars": {
    "line_name_zh": "山手线",
    "line_name_en": "Yamanote Line",
    "line_code": "JY",
    "operator": "JR东日本",
    "line_color": "黄绿",
    "line_color_hex": "#9ACD32",
    "character_gender": "female",
    "character_personality": "自信, 忙碌, 信息量巨大, 可靠, 时尚, 永远不停歇",
    "character_personality_tags": ["自信", "忙碌", "信息量巨大", "可靠", "时尚", "永远不停歇"],
    "character_catchphrase": "东京不是一座城市，是一圈循环。",
    ...
  }
}
```

### V2 格式规范

- `character_personality`：逗号分隔的纯关键词，禁止长句叙事
- `character_personality_tags`：同内容的数组格式，供程序消费
- `line_color`：单一主色名（如 `黄绿`、`橙`），非描述性短语
- 空值字段统一使用 `null`，不使用空字符串 `""`
- `line_specific`：纯事实摘要，不含散文叙事
- `character_gender`：`male` / `female`

## 线路覆盖

共 **64 条线路**，编号 01–64 连续，涵盖：

- 新干线（5 条）：东北、上越、北陆、山形、秋田
- 首都圈核心干线（~25 条）：山手线、中央线、京滨东北线、东海道线、常磐线 等
- 首都圈外围线路（~10 条）：青梅线、南武线、鹤见线、横滨线 等
- 北关东地方线路（~7 条）：两毛线、日光线、水户线 等
- 上越·信越·东北地方干线（~12 条）：信越本线、羽越本线、奥羽本线 等
- 地方交通线（~8 条）：只见线、五能线、小海线 等
- BRT（2 条）：气仙沼线 BRT、大船渡线 BRT

## 更新角色数据

1. 编辑 `output/jr_east_character_profiles.txt`
2. 删除要更新的线路文件夹（或全部删除重来）
3. 运行 `python build_all_lines.py`
4. 运行 `python merge_prompts.py` 校验

已有手工维护数据的线路（山手线、中央快速线、京滨东北线）会在 `build_all_lines.py` 中自动跳过，不会被覆盖。如需强制覆盖，编辑脚本中的 `EXISTING_KEEPERS` 字典。

## Prompt 模板设计

模板位于 `lines/prompts.json`，包含两套：

| 模式 | 用途 | 特点 |
|------|------|------|
| `poster` | 完整图鉴海报 | 含 12 个信息面板（路线图、车型卡、趣事等），带 GLOBAL_STYLE_LOCK 和 PANEL_ISOLATION_RULE |
| `character_only` | 仅角色立绘 | 纯角色，无文字面板，适合作为素材二次排版 |

模板使用 `{{variable}}` 占位符，运行时由 `generate_batch.py` 从每条线路的 `poster_vars` 中填入实际值。

### 工业级锁定规则

- **GLOBAL_STYLE_LOCK**：所有角色强制共享相同的赛璐璐渲染风格、三点式电影光照、统一线宽和色彩系统，禁止风格漂移
- **PANEL_ISOLATION_RULE**：每个信息面板独立卡片，4–8px 间隔，禁止重叠、禁止透明背景、禁止浮动文字。画布分为 6 个非重叠布局区域
