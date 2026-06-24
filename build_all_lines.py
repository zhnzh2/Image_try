"""
V2：解析 profiles.txt，生成结构干净的 prompts.json。

修复（相比 V1）：
  1. character_personality ← 使用人设关键词（纯标签，无长句）
  2. line_color ← 精简为单一主色名 + hex
  3. 空值字段使用 null（而非空字符串）
  4. line_specific ← 只保留事实摘要
"""

import json
import re
from pathlib import Path


LINES_DIR = Path("lines")
PROFILES_PATH = Path("output/jr_east_character_profiles.txt")

# ── 精简版对照表（只保留单一主色名）──
LINE_META = {
    "东北新干线":   ("#008000", "深绿",   "Tohoku Shinkansen"),
    "上越新干线":   ("#006400", "深绿",   "Joetsu Shinkansen"),
    "北陆新干线":   ("#00A7E1", "浅蓝",   "Hokuriku Shinkansen"),
    "山形新干线":   ("#4B573D", "银绿",   "Yamagata Shinkansen"),
    "秋田新干线":   ("#D93A39", "茜红",   "Akita Shinkansen"),
    "山手线":       ("#9ACD32", "黄绿",   "Yamanote Line"),
    "中央快速线":   ("#FF6600", "橙",     "Chuo Line Rapid"),
    "中央·总武缓行": ("#FFCC00", "黄蓝",   "Chuo-Sobu Local Line"),
    "京滨东北线":   ("#00BFFF", "天蓝",   "Keihin-Tohoku Line"),
    "东海道线":     ("#FF6600", "橙",     "Tokaido Line"),
    "常磐线":       ("#00A86B", "青绿",   "Joban Line"),
    "总武本线":     ("#0066CC", "蓝",     "Sobu Main Line"),
    "总武快速线":   ("#0066CC", "蓝",     "Sobu Rapid Line"),
    "横须贺线":     ("#003399", "深蓝",   "Yokosuka Line"),
    "高崎线":       ("#FF8C00", "橙",     "Takasaki Line"),
    "宇都宫线":     ("#FF8C00", "橙",     "Utsunomiya Line"),
    "川越线":       ("#2E8B57", "深绿",   "Kawagoe Line"),
    "埼京线":       ("#2E8B57", "深绿",   "Saikyo Line"),
    "湘南新宿":     ("#FF8C00", "橙",     "Shonan-Shinjuku Line"),
    "上野东京线":   ("#9966CC", "紫",     "Ueno-Tokyo Line"),
    "京叶线":       ("#CC0000", "红",     "Keiyo Line"),
    "武藏野线":     ("#FF8C00", "橙",     "Musashino Line"),
    "青梅线":       ("#FF6600", "橙",     "Ome Line"),
    "南武线":       ("#FFCC00", "黄",     "Nambu Line"),
    "五日市线":     ("#FF6600", "橙",     "Itsukaichi Line"),
    "鹤见线":       ("#FFCC00", "黄",     "Tsurumi Line"),
    "横滨线":       ("#7CFC00", "莺绿",   "Yokohama Line"),
    "相模线":       ("#00A86B", "青绿",   "Sagami Line"),
    "八高线":       ("#808080", "灰",     "Hachiko Line"),
    "成田线":       ("#0066CC", "蓝",     "Narita Line"),
    "外房线":       ("#0066CC", "蔚蓝",   "Sotobo Line"),
    "东金线":       ("#FFCC00", "黄",     "Togane Line"),
    "内房线":       ("#003366", "深蓝",   "Uchibo Line"),
    "久留里线":     ("#808080", "灰",     "Kururi Line"),
    "鹿岛线":       ("#CC0000", "红",     "Kashima Line"),
    "两毛线":       ("#003399", "深蓝",   "Ryomo Line"),
    "日光线":       ("#CC0000", "红",     "Nikko Line"),
    "水户线":       ("#87CEEB", "淡蓝",   "Mito Line"),
    "水郡线":       ("#00A86B", "青绿",   "Suigun Line"),
    "吾妻线":       ("#8B4513", "棕",     "Agatsuma Line"),
    "乌山线":       ("#F5F5DC", "米白",   "Karasuyama Line"),
    "伊东线":       ("#0066CC", "蓝",     "Ito Line"),
    "信越本线":     ("#2E8B57", "绿",     "Shinetsu Main Line"),
    "白新线":       ("#90EE90", "绿",     "Hakushin Line"),
    "上越线":       ("#006400", "深绿",   "Joetsu Line"),
    "羽越本线":     ("#FF6600", "橙",     "Uetsu Main Line"),
    "奥羽本线":     ("#4B573D", "银绿",   "Ou Main Line"),
    "仙石线":       ("#CC0000", "红",     "Senseki Line"),
    "左泽线":       ("#90EE90", "淡绿",   "Aterazawa Line"),
    "磐越西线":     ("#1B315E", "深蓝",   "Banetsu West Line"),
    "仙山线":       ("#00552E", "绿",     "Senzan Line"),
    "田泽湖线":     ("#1E4F84", "钴蓝",   "Tazawako Line"),
    "越后线":       ("#2E8B57", "绿",     "Echigo Line"),
    "米坂线":       ("#003366", "深蓝",   "Yonesaka Line"),
    "大糸线":       ("#808080", "灰绿",   "Oito Line"),
    "饭山线":       ("#FFFFFF", "白",     "Iiyama Line"),
    "小海线":       ("#00A86B", "青绿",   "Koumi Line"),
    "弥彦线":       ("#90EE90", "绿",     "Yahiko Line"),
    "只见线":       ("#0066CC", "蓝",     "Tadami Line"),
    "八户线":       ("#003399", "靛蓝",   "Hachinohe Line"),
    "五能线":       ("#0066CC", "蓝",     "Gono Line"),
    "男鹿线":       ("#CC0000", "红",     "Oga Line"),
    "北上线":       ("#003399", "靛蓝",   "Kitakami Line"),
    "釜石线":       ("#8B4513", "棕",     "Kamaishi Line"),
    "花轮线":       ("#F5F5DC", "白",     "Hanawa Line"),
    "山田线":       ("#0066CC", "蓝",     "Yamada Line"),
    "大凑线":       ("#FFFFFF", "白",     "Ominato Line"),
    "津轻线":       ("#FFFFFF", "白",     "Tsugaru Line"),
    "气仙沼":       ("#CC0000", "红",     "Kesennuma Line BRT"),
    "大船渡":       ("#0066CC", "蓝",     "Ofunato Line BRT"),
}

# ── 线路代码对照（不在标题中的线路，手工补充）──
LINE_CODES = {
    "山手线": "JY", "中央快速线": "JC", "中央·总武缓行": "JB",
    "京滨东北线": "JK", "东海道线": "JT", "常磐线": "JJ",
    "总武本线": "JO", "总武快速线": "JO", "横须贺线": "JO",
    "高崎线": "JU", "宇都宫线": "JU", "埼京线": "JA",
    "湘南新宿": "JS", "上野东京线": "JU", "京叶线": "JE",
    "武藏野线": "JM", "青梅线": "JC", "南武线": "JN",
    "五日市线": "JC", "鹤见线": "JI", "横滨线": "JH",
    "成田线": "JO", "伊东线": "JT",
}


def load_profiles_text() -> str:
    with PROFILES_PATH.open("r", encoding="utf-8") as f:
        return f.read()


def split_sections(text: str) -> list[dict]:
    pattern = re.compile(r'^###\s+\d+\.\s*(.+)$', re.MULTILINE)
    matches = list(pattern.finditer(text))
    sections = []
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append({"title": title, "body": body})
    return sections


def extract_field(body: str, field_name: str) -> str:
    pattern = rf'\*\*{re.escape(field_name)}\*\*\s*[：:]\s*(.+?)(?=\n\*\*|\n###|\n---|\Z)'
    m = re.search(pattern, body, re.DOTALL)
    if m:
        return m.group(1).strip().replace('\n', ' ').replace('  ', ' ')
    return ""


def extract_color_hex(body: str) -> str:
    m = re.search(r'#[0-9A-Fa-f]{6}', body)
    return m.group(0) if m else ""


def clean_text(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def find_line_meta(line_name: str) -> tuple:
    """(hex, color_name, name_en)"""
    for key, meta in LINE_META.items():
        if key in line_name or line_name in key:
            return meta
    for key, meta in LINE_META.items():
        if len(key) >= 2 and key[:2] in line_name:
            return meta
        if len(line_name) >= 2 and line_name[:2] in key:
            return meta
    return ("#888888", "灰", line_name)


def find_line_code(line_name: str, title: str) -> str:
    """从标题或对照表中提取线路代码。"""
    # 先从标题中找 "JY" 等双字母代码
    m = re.search(r'\b([A-Z]{2})\b', title)
    if m:
        return m.group(1)
    # 从对照表找
    for key, code in LINE_CODES.items():
        if key in line_name or line_name in key:
            return code
    return None  # 无代码用 null


def parse_length_stations(body: str) -> tuple:
    length = None
    stations = None
    m = re.search(r'全长[约]?\s*([\d.,]+\s*公?里|[\d.,]+\s*km)', body, re.IGNORECASE)
    if m:
        length = clean_text(m.group(1))
    m = re.search(r'(\d+)\s*个?(?:核心)?(?:车)?站', body)
    if m:
        stations = int(m.group(1))
    return length, stations


def extract_catchphrase(personality: str, character_design: str) -> str | None:
    """从性格段落中提取口头禅。"""
    for pat in [
        r'口头禅[是为说]{0,2}[：:]\s*“(.+?)”',
        r'口头禅[是为说]{0,2}[：:]\s*「(.+?)」',
        r'口头禅[是为说]{0,2}[：:]\s*"(.+?)"',
        r'口头禅[是为说]{0,2}[：:]\s*(.+?)(?:[。；;]|\n\n|\Z)',
    ]:
        m = re.search(pat, personality, re.DOTALL)
        if m:
            raw = m.group(1).strip()
            raw = re.sub(r'[。！!？?，,、\s]+$', '', raw)
            if 4 <= len(raw) <= 100:
                return raw

    combined = personality + "\n" + character_design
    for pat in [
        r'“([^”]{6,60})”',
        r'「([^」]{4,40})」',
        r'"([^"]{6,60})"',
    ]:
        matches = re.findall(pat, combined)
        for mc in matches:
            mc = mc.strip()
            mc = re.sub(r'[。！!？?，,、\s]+$', '', mc)
            if 4 <= len(mc) <= 80 and not re.search(r'(年|公里|km|编成|辆|系|站|开通|运营|列车)', mc):
                return mc
    return None


def parse_keywords(keywords_text: str) -> list[str]:
    """将人设关键词文本解析为干净标签列表。"""
    if not keywords_text:
        return []
    # 按常见分隔符拆分
    parts = re.split(r'[，,、#\s]+', keywords_text)
    result = []
    for p in parts:
        p = p.strip()
        # 过滤太短、太长、纯数字、纯符号
        if not p or len(p) < 2 or len(p) > 20:
            continue
        if re.match(r'^[\d\.\-\+#]+$', p):
            continue
        result.append(p)
    return result


def build_entry(section: dict, idx: int) -> dict | None:
    title = section["title"]
    body = section["body"]

    # ── 线路名 ──
    parts = re.split(r'\s*/\s*', title)
    line_name_zh = parts[0].strip()
    line_name_zh = re.sub(r'[（(][^)）]*[)）]', '', line_name_zh).strip()
    line_name_ja = parts[1].strip() if len(parts) > 1 else ""

    # ── 提取各字段 ──
    char_name = extract_field(body, "拟人名")
    founding_year = extract_field(body, "源流年份")
    age_setting = extract_field(body, "年龄设定")
    basic_info = extract_field(body, "基本信息")
    character_design = extract_field(body, "角色设定")
    personality_narrative = extract_field(body, "性格")
    keywords_text = extract_field(body, "人设关键词")

    # ── 修正1: character_personality ← 人设关键词（纯标签）──
    personality_tags = parse_keywords(keywords_text)
    # 补充从角色设定中提取的身份标签
    role_tag = ""
    m = re.search(r'身份[是为]\s*「(.+?)」', character_design)
    if m:
        role_tag = m.group(1)

    # ── 颜色 ──
    color_hex_from_body = extract_color_hex(body)
    color_hex, color_name, name_en = find_line_meta(line_name_zh)
    if color_hex_from_body:
        color_hex = color_hex_from_body

    # ── 线路代码 ──
    line_code = find_line_code(line_name_zh, title)

    # ── 长度/车站 ──
    length_str, stations_int = parse_length_stations(basic_info)

    # ── 口头禅 ──
    catchphrase = extract_catchphrase(personality_narrative, character_design)

    # ── 性别 ──
    gender = "female"
    male_kw = ["男性", "剑士", "骑士", "大叔", "职人", "船头", "腰带职人"]
    if any(kw in body[:600] for kw in male_kw):
        gender = "male"
    if "八高" in line_name_zh:
        gender = "male"

    # ── 角色名 ──
    role = char_name if char_name else line_name_zh

    # ── 车型 ──
    rolling_stock = None
    m = re.search(r'主力车型[为是]?\s*(.+?)[，。,.\n]', basic_info)
    if m:
        rs = clean_text(m.group(1))
        if rs:
            rolling_stock = rs[:120]

    # ── 编成 ──
    formation = None
    m = re.search(r'(\d+辆编[成组])', basic_info)
    if m:
        formation = m.group(1)

    # ── route_type ──
    route_type = None
    m = re.search(r'(?:是|为)\s*(.{4,30}?(?:干线|动脉|通道|支线|环线|系统|走廊|新干线))', basic_info[:300])
    if m:
        route_type = m.group(1).strip()

    # ── 开通年份 ──
    year_match = re.search(r'(\d{4})\s*年', founding_year)
    year_str = founding_year if founding_year else None

    # ── 修正4: line_specific ← 纯事实摘要 ──
    operator = "JR东日本"
    line_specific = f"{operator}{line_name_zh}。主色{color_name}（{color_hex}）。"
    if length_str:
        line_specific += f"全长{length_str}。"
    if founding_year:
        line_specific += f"源流{founding_year}。"

    # ── fun_facts ──
    fun_facts = " | ".join(personality_tags) if personality_tags else keywords_text

    # ── ID ──
    line_id = f"{idx:02d}_" + re.sub(r'[^\w]', '_', line_name_zh.lower()).strip('_')[:30]

    # ── 构建 poster_vars（修正3: 空值用 null）──
    poster_vars = {
        "line_name_zh": line_name_zh,
        "line_name_en": name_en,
        "line_code": line_code,
        "operator": operator,
        "line_color": color_name,
        "line_color_hex": color_hex,
        "route_type": route_type,
        "length": length_str,
        "stations": stations_int,
        "loop_time": None,
        "service_pattern": None,
        "rolling_stock": rolling_stock,
        "formation": formation,
        "main_stations": None,
        "related_lines": None,
        "character_gender": gender,
        "character_personality": ", ".join(personality_tags) if personality_tags else role,
        "character_personality_tags": personality_tags,
        "character_role": role[:80] if role else char_name,
        "character_age": (age_setting[:100] if age_setting else founding_year),
        "character_catchphrase": catchphrase,
        "fun_facts": fun_facts[:300] if fun_facts else None,
        "opening_year": year_str,
        "key_milestone": year_str,
    }

    return {
        "id": line_id,
        "name": line_name_zh,
        "name_ja": line_name_ja,
        "line_specific": line_specific,
        "poster_vars": poster_vars,
    }


def json_null_handler(obj):
    """None → null 的 JSON 序列化。"""
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def write_prompts_json(entry: dict) -> None:
    line_id = entry["id"]
    folder = LINES_DIR / line_id
    folder.mkdir(parents=True, exist_ok=True)

    output = {
        "id": line_id,
        "name": entry["name"],
        "name_ja": entry["name_ja"],
        "line_specific": entry["line_specific"],
        "poster_vars": entry["poster_vars"],
    }

    out_path = folder / "prompts.json"
    with out_path.open("w", encoding="utf-8") as f:
        f.write(json_null_handler(output))
    print(f"  OK [{line_id}] {entry['name']}")


def fuzzy_match(name1: str, name2: str) -> bool:
    clean = lambda s: re.sub(r'[\s·/／\-]', '', s)
    c1, c2 = clean(name1), clean(name2)
    if c1 == c2 or c1 in c2 or c2 in c1:
        return True
    set1, set2 = set(c1), set(c2)
    return len(set1 & set2) >= min(len(set1), len(set2)) * 0.8


EXISTING_KEEPERS = {
    "06_山手线": "山手线",
    "07_中央快速线": "中央快速线",
    "09_京滨东北线": "京滨东北线",
}


def main():
    print("V2: 读取 profiles.txt ...")
    text = load_profiles_text()

    sections = split_sections(text)
    print(f"解析到 {len(sections)} 个线路段落\n")

    created = 0
    skipped = 0

    for idx, section in enumerate(sections):
        entry = build_entry(section, idx + 1)
        if entry is None:
            continue

        matched = None
        for eid, ename in EXISTING_KEEPERS.items():
            if fuzzy_match(entry["name"], ename):
                matched = eid
                break

        if matched:
            print(f"  SKIP [{matched}] {entry['name']}")
            skipped += 1
            continue

        write_prompts_json(entry)
        created += 1

    print(f"\n========== V2 完成 ==========")
    print(f"新创建：{created} 条")
    print(f"已跳过：{skipped} 条")
    print(f"总计：{len(sections)}")


if __name__ == "__main__":
    main()
