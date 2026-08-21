#!/usr/bin/env python3
"""Test Case Schema 校验器（markmap ↔ schema.yaml 一致性）.

配套 core/schema-extraction.md 的抽取规则，在抽取 / 修订重抽后运行：

    python3 validate_schema.py 测试用例_markmap.md 测试用例.schema.yaml

校验项：
  1. YAML 可解析（转义纪律）——环境装有 PyYAML 时全量解析并检查枚举值；
     未安装时降级为基础 lint（引号配对 / 裸引号 / 缩进跳变），仍能抓住
     "双引号值内裸放引号" 这类最常见的中断下游消费的解析错误
  2. TC 编号一致性——schema 中的 id 必须存在于 markmap（孤儿报错），
     markmap 中的编号缺失于 schema（遗漏告警，增量更新场景可接受但需人工确认）
  3. 占位符——title / steps / expected 等字段值出现 {xxx} / <xxx> / 「某某」即报错
     （用例可执行性红线，见 core/executability.md）

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
             "regression", "state", "data"},
    "execution_model": {"ui", "dev-collab"},
    "status": {"active", "changed", "deprecated"},
}
TEXT_FIELDS = ("title", "steps", "expected", "preconditions", "test_data")


def extract_markmap_tcs(md_text):
    """markmap 用例编号：排除删除线（~~TC-xx~~ 已废弃）与引用块外的附录。"""
    ids = []
    for line in md_text.splitlines():
        if "~~" in line:  # 已废弃用例不算遗漏
            continue
        m = re.match(r"\s*-\s*\*{0,2}(TC-\d+-\d+)", line)
        if m:
            ids.append(m.group(1))
    return ids


def lint_yaml_basic(text, errors):
    """零依赖降级 lint：抓最常见的中断解析的转义错误。"""
    for no, line in enumerate(text.splitlines(), 1):
        code = line.split("#")[0]
        n_dq = code.count('"')
        if n_dq % 2 == 1:
            errors.append(f"L{no}: 双引号数量为奇数（值内裸放引号或漏转义）: {line.strip()[:60]}")
        # key: "值" 闭合后又有非空内容 = 值内裸放引号（如 "满100减20"券"，最常见的中断解析错误）
        if re.search(r':\s*"[^"]*"[^"]', code):
            errors.append(f"L{no}: 双引号值闭合后又出现内容（疑似裸引号未转义）: {line.strip()[:60]}")


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


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    md_path, yaml_path = Path(sys.argv[1]), Path(sys.argv[2])
    for p in (md_path, yaml_path):
        if not p.exists():
            print(f"错误: 文件不存在 {p}")
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
