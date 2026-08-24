#!/usr/bin/env python3
"""Test Case Schema 校验器（markmap ↔ schema.yaml 一致性）+ 测试策略类型域校验（V1–V5）.

模式一（用例 Schema，配套 core/schema-extraction.md，抽取 / 修订重抽后运行）：

    python3 validate_schema.py 测试用例_markmap.md 测试用例.schema.yaml

  1. YAML 可解析（转义纪律）——环境装有 PyYAML 时全量解析并检查枚举值；
     未安装时降级为基础 lint（引号配对 / 裸引号），仍能抓住
     "双引号值内裸放引号" 这类最常见的中断下游消费的解析错误
  2. TC 编号一致性——schema 中的 id 必须存在于 markmap（孤儿报错），
     markmap 中的编号缺失于 schema（遗漏告警，增量更新场景可接受但需人工确认）
  3. 占位符——title / steps / expected 等字段值出现 {xxx} / <xxx> / 「某某」即报错
     （用例可执行性红线，见 core/executability.md）

模式二（测试策略类型域决策，配套 core/test-type-matrix.md，test-strategy 落盘后运行）：

    python3 validate_schema.py 测试策略.md

  V1 全轴必答——十轴齐全且 decision ∈ include/exclude/handoff（每轴单行 flow 风格）；
     depth ∈ full/standard/light（"不测"是范围决策不是深度值：功能域 include: false，
     类型域 decision: exclude/handoff）
  V2 include 挂证据——signals 或 risk_refs 非空（无证据纳入 = 过测）
  V3 exclude 挂理由——rationale 非空 + scanned 含 G 级与 S 级双记录（无理由排除 = 漏测；
     无代码仓库场景豁免 S 级）
  V4 full 有预算——depth=full 轴必须挂 risk_refs；full 总数（两域合并）≤3，
     超限须有 budget_review（预算裁决记录，R6>R1）；depth_budget.full_axes 与实际一致。
     两域 scope 可写在同一或不同 yaml 代码块，均纳入统计
  V5 移交不断链——execution_status=blocked 必带 todo；executor 非空且非 agent 时
     （含 handoff）必带 handoff_ref

退出码：0 通过（含告警）/ 1 有错误
"""
import re
import sys
from pathlib import Path

TC_RE = re.compile(r"TC-\d+-\d+")
PLACEHOLDER_RE = re.compile(r"\{[^}\n]{1,40}\}|<[^>\n]{1,40}>|某[某数据个账号]")
ENUMS = {
    "priority": {"P0", "P1", "P2"},
    "type": {"functional", "boundary", "exception", "permission",
             "regression", "state", "data", "reliability", "concurrency",
             "security", "compatibility"},
    "execution_model": {"ui", "dev-collab"},
    "status": {"active", "changed", "deprecated"},
}
TEXT_FIELDS = ("title", "steps", "expected", "preconditions", "test_data")


def extract_markmap_tcs(md_text):
    """markmap 用例编号：剔除删除线段（~~TC-xx~~ 已废弃，同行的存活编号保留）与引用块外的附录。"""
    ids = []
    for line in md_text.splitlines():
        line = re.sub(r"~~[^~]+~~", "", line)  # 删除线段不算遗漏，整行丢弃会漏提同行存活编号
        m = re.match(r"\s*-\s*\*{0,2}(TC-\d+-\d+)", line)
        if m:
            ids.append(m.group(1))
    return ids


def lint_yaml_basic(text, errors):
    """零依赖降级 lint：抓最常见的中断解析的转义错误（引号配对 / 裸引号）。"""
    for no, line in enumerate(text.splitlines(), 1):
        code = _strip_yaml_comment(line)
        n_dq = code.count('"')
        if n_dq % 2 == 1:
            errors.append(f"L{no}: 双引号数量为奇数（值内裸放引号或漏转义）: {line.strip()[:60]}")
        # key: "值" 闭合后又有非分隔符内容 = 值内裸放引号（如 "满100减20"券"，最常见的中断解析错误）；
        # 逗号/右花括号除外（flow 映射中为合法分隔）
        if re.search(r':\s*"(?:[^"\\]|\\.)*"[ \t]*[^\s#,}]', code):
            errors.append(f"L{no}: 双引号值闭合后又出现内容（疑似裸引号未转义）: {line.strip()[:60]}")


def _strip_yaml_comment(line):
    """去掉双引号外首个 # 及其后内容（引号内的 # 是值的一部分，不截断）。"""
    in_q = False
    for i, c in enumerate(line):
        if c == '"':
            in_q = not in_q
        elif c == "#" and not in_q:
            return line[:i]
    return line


def walk_cases(node, out):
    """递归收集含 TC 编号 id 的映射节点。"""
    if isinstance(node, dict):
        vid = node.get("id")
        if isinstance(vid, str) and TC_RE.fullmatch(vid):
            out.append(node)
        for v in node.values():
            walk_cases(v, out)
    elif isinstance(node, list):
        for v in node:
            walk_cases(v, out)


def check_case(case, errors, warnings):
    cid = case.get("id", "?")
    for field, allowed in ENUMS.items():
        val = case.get(field)
        if val is not None and val not in allowed:
            errors.append(f"{cid}: {field}='{val}' 不在枚举 {sorted(allowed)}")
    for field in TEXT_FIELDS:
        val = case.get(field)
        blobs = val if isinstance(val, list) else [val]
        for blob in blobs:
            if isinstance(blob, str):
                m = PLACEHOLDER_RE.search(blob)
                if m:
                    errors.append(f"{cid}: {field} 含占位符 '{m.group(0)}'（可执行性红线）")


# ---------- 模式二：测试策略类型域校验（V1–V5，配套 core/test-type-matrix.md） ----------

TYPE_AXES = ["performance", "security_business", "reliability", "concurrency",
             "compatibility", "accessibility", "visual", "i18n", "migration",
             "contract_integration"]
FULL_MAX = 3
DEPTHS = {"full", "standard", "light"}
AXIS_LINE_RE = {axis: re.compile(rf"^[ \t]*{axis}:[ \t]*\{{(.+)\}}[ \t]*$", re.M)
                for axis in TYPE_AXES}
FLOW_LINE_RE = re.compile(r"^[ \t]*(\w+):[ \t]*\{(.+)\}[ \t]*$", re.M)


def parse_flow_map(inner):
    """解析单行 flow 映射 {k: v, ...}；值保留原文，列表保留 [ ] 内文本。"""
    kv = {}
    for m in re.finditer(r"(\w+)\s*:\s*(\[[^\]]*\]|\"[^\"]*\"|'[^']*'|[^,{}]+)", inner):
        kv[m.group(1)] = m.group(2).strip()
    return kv


def list_items(val):
    if not val or not val.startswith("["):
        return []
    return [x.strip().strip("\"'") for x in val[1:-1].split(",") if x.strip()]


def scalar(kv, key):
    """取标量值并剥引号。"""
    return kv.get(key, "").strip().strip("\"'").strip()


def extract_scope_blocks(text):
    """合并所有含 functional_scope:/type_scope:/depth_budget: 的 yaml 块。

    两域 scope 与 depth_budget（含 budget_review）可写进同一或不同代码块，均纳入检查；
    注意 full_axes 声明须用行内数组写法（与 test-strategy SKILL.md 示例一致），多行展开式不校验。
    """
    parts = [b for b in re.findall(r"```yaml\n(.*?)```", text, re.S)
             if "type_scope:" in b or "functional_scope:" in b or "depth_budget:" in b]
    return "\n".join(parts) if parts else None


def validate_strategy(path):
    errors, warnings = [], []
    # 统一换行（Windows 宿主产物的 CRLF 会让行锚定正则全部失配）
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    block = extract_scope_blocks(text)
    if block is None:
        errors.append("未找到含 type_scope:/functional_scope: 的 yaml 代码块——测试策略必须包含类型域十轴决策（V1）")
        return errors, warnings

    def has_mark(items, marks):
        return any(mk in s for s in items for mk in marks)

    for axis in TYPE_AXES:
        matches = list(AXIS_LINE_RE[axis].finditer(block))
        if not matches:
            errors.append(f"V1 轴缺失或非单行 flow 风格: {axis}"
                          f"（应形如 {axis}: {{ decision: include, depth: standard, signals: [...] }}）")
            continue
        if len(matches) > 1:
            errors.append(f"V1 {axis}: 出现 {len(matches)} 次——每轴只允许一行决策，重复轴请合并")
        m = matches[0]
        kv = parse_flow_map(m.group(1))
        decision = kv.get("decision", "")
        if decision not in ("include", "exclude", "handoff"):
            errors.append(f"V1 {axis}: decision='{decision or '(缺)'}' 不在 include/exclude/handoff")
            continue

        if decision == "include":
            if not (list_items(kv.get("signals")) or list_items(kv.get("risk_refs"))):
                errors.append(f"V2 {axis}: include 但 signals / risk_refs 均为空（无证据纳入 = 过测）")
        elif decision == "exclude":
            rationale = scalar(kv, "rationale")
            if not rationale:
                errors.append(f"V3 {axis}: exclude 缺 rationale（无理由排除 = 漏测）")
            scanned = list_items(kv.get("scanned"))
            if not scanned:
                errors.append(f"V3 {axis}: exclude 缺 scanned 清单（G 级 + S 级双记录）")
            else:
                if not has_mark(scanned, ("(G)", "G级", "G 级", "G:")):
                    errors.append(f"V3 {axis}: scanned 无 G 级扫描记录（G+S 双确认，缺 G 级 = 扫描未执行）")
                if "无代码" not in rationale and not has_mark(scanned, ("(S)", "S级", "S 级", "S:")):
                    errors.append(f"V3 {axis}: scanned 无 S 级复核记录（exclude 须 G+S 双确认，"
                                  "防脚本盲区制度化；无代码仓库场景须在 rationale 注明）")
        else:  # handoff
            if not scalar(kv, "executor"):
                errors.append(f"V5 {axis}: handoff 缺 executor")
            if not scalar(kv, "handoff_ref"):
                errors.append(f"V5 {axis}: handoff 缺 handoff_ref（移交包文件，防移交即消失）")

        if scalar(kv, "execution_status") == "blocked" and not scalar(kv, "todo"):
            errors.append(f"V5 {axis}: execution_status=blocked 缺 todo（向谁索取什么）")
        executor = scalar(kv, "executor")
        if decision == "include" and executor and executor != "agent" and not scalar(kv, "handoff_ref"):
            errors.append(f"V5 {axis}: include + 外部执行器({executor}) 缺 handoff_ref")

    # V4：depth 枚举 + full 档逐行统计（functional_scope + type_scope 两域合并）
    full_axes = []
    seen_names = set()
    for m in FLOW_LINE_RE.finditer(block):
        name, inner = m.group(1), m.group(2)
        if name in seen_names:
            continue  # 重复轴已由 V1 报错；统计以首处为准
        seen_names.add(name)
        kv = parse_flow_map(inner)
        depth = scalar(kv, "depth")
        if depth and depth not in DEPTHS:
            errors.append(f"V4 {name}: depth='{depth}' 不在 full/standard/light（'不测'是范围决策："
                          "功能域 include: false，类型域 decision: exclude/handoff，均须挂理由）")
        if depth == "full":
            full_axes.append(name)
            if not list_items(kv.get("risk_refs")):
                errors.append(f"V4 {name}: depth=full 但 risk_refs 为空（须挂风险编号作升档依据）")
    m_budget = re.search(r"full_axes:\s*\[([^\]]*)\]", block)
    if m_budget:
        declared = [x.strip() for x in m_budget.group(1).split(",") if x.strip()]
        if sorted(declared) != sorted(full_axes):
            errors.append(f"V4 depth_budget.full_axes {declared} 与实际 full 轴 {full_axes} 不一致")
    if len(full_axes) > FULL_MAX and not re.search(r"^[ \t]*budget_review:", block, re.M):
        errors.append(f"V4 full 轴 {len(full_axes)} 个 > {FULL_MAX}（两域合并）："
                      "须触发预算裁决检查点并记录 budget_review（R6 > R1）")
    return errors, warnings


def main():
    if len(sys.argv) == 2:  # 模式二：测试策略类型域校验
        p = Path(sys.argv[1])
        if not p.is_file():
            print(f"错误: 文件不存在或不是普通文件 {p}")
            return 1
        errors, warnings = validate_strategy(p)
        for e in errors:
            print(f"  ✗ {e}")
        for w in warnings:
            print(f"  ⚠ {w}")
        verdict = "✅ 类型域决策校验通过（V1–V5）" if not errors else f"✗ {len(errors)} 个错误"
        print(f"{verdict}: {p.name}")
        return 1 if errors else 0

    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    md_path, yaml_path = Path(sys.argv[1]), Path(sys.argv[2])
    for p in (md_path, yaml_path):
        if not p.is_file():
            print(f"错误: 文件不存在或不是普通文件 {p}")
            return 1

    errors, warnings = [], []
    yaml_text = yaml_path.read_text(encoding="utf-8")
    md_text = md_path.read_text(encoding="utf-8")

    cases = []
    try:
        import yaml  # type: ignore
        docs = [d for d in yaml.safe_load_all(yaml_text) if d is not None]
        for doc in docs:
            walk_cases(doc, cases)
    except ImportError:
        warnings.append("未安装 PyYAML，降级为基础 lint（引号配对 / 裸引号），建议 pip install pyyaml")
        lint_yaml_basic(yaml_text, errors)
    except Exception as e:  # yaml.YAMLError 等
        errors.append(f"YAML 解析失败（检查转义纪律，见 core/schema-extraction.md）: {e}")

    for case in cases:
        check_case(case, errors, warnings)

    if cases:
        yaml_ids = [c["id"] for c in cases]
        md_ids = extract_markmap_tcs(md_text)
        orphans = sorted(set(yaml_ids) - set(md_ids))
        missing = sorted(set(md_ids) - set(yaml_ids))
        for tc in orphans:
            errors.append(f"{tc}: schema 中存在但 markmap 无此用例（孤儿条目）")
        for tc in missing:
            warnings.append(f"{tc}: markmap 中存在但 schema 未抽取（遗漏，确认是否应抽取）")
        if len(yaml_ids) != len(set(yaml_ids)):
            dupes = sorted({t for t in yaml_ids if yaml_ids.count(t) > 1})
            errors.append(f"schema 中 id 重复: {', '.join(dupes)}")

    for e in errors:
        print(f"  ✗ {e}")
    for w in warnings:
        print(f"  ⚠ {w}")
    n_ok = len(cases) if cases else "-"
    verdict = "✅ 校验通过" if not errors else f"✗ {len(errors)} 个错误"
    print(f"{verdict}（用例 {n_ok} 条，错误 {len(errors)}，告警 {len(warnings)}）: {yaml_path.name}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
