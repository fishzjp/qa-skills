#!/usr/bin/env python3
"""回归清单校验器（regression-testing 产出）——三级分级与显式排除的结构闸门。

背景：`regression-testing/SKILL.md` 定义了回归清单的五节结构
（必须回归 P0 / 建议回归 P1 / 可选回归 P2 / 影响不明 / 无影响确认显式排除），
且要求"逐条给依据""排除给模块级/字段级理由"（Round 29 补的成因面相关性规则）。
此前**没有任何脚本校验**——清单缺节、缺排除、缺依据时人读照常、仓库侧零红灯。

用法：
    python3 regression_checklist_check.py 回归清单_20261109.md [--json]

检查项（E = 错误，阻断定稿；W = 告警，需人工确认）：
    E1  缺节（五节：必须回归 P0 / 建议回归 P1 / 可选回归 P2 / 影响不明 / 无影响确认）
    E2  缺变更基线行（无 `base...head` 或 `对比基线` 线索）
    W1  显式排除节有条目但缺理由（模块级/字段级/无依赖说明）
    W2  必须回归 P0 档有条目但缺依据（code_refs/风险锚点/模块映射）
    W3  影响不明节有条目但缺 evidence/status 标注

退出码：0 = 无错误（告警不算失败）；1 = 有错误。
"""
import argparse
import json
import re
import sys
from pathlib import Path

TIER_PATTERNS = [
    ("必须回归", r"(?:必须回归|P0)"),
    ("建议回归", r"(?:建议回归|P1)"),
    ("可选回归", r"(?:可选回归|P2)"),
    ("影响不明", r"(?:影响不明|影响不明确|建议人工判断|人工判断)"),
    ("无影响确认", r"(?:无影响确认|显式排除|排除)"),
]
BASELINE_RE = re.compile(
    r"(?:变更基线|对比基线|base\s*[.…/]|base\s*分支|base\s*commit)", re.I)
RATIONALE_HINTS = re.compile(
    r"模块级|字段级|成因|无共享|不消费|code_refs|直连|无改动|不涉|无依赖|无队列|无缓存"
    r"|未触及|无关联", re.I)
RATIONALE_P0 = re.compile(
    r"code_refs|直连|锚点|命中|risk_ref|模块映射|改动文件|邻近行|执行路径", re.I)


def _section(text, heading_pattern):
    m = re.search(rf"(?m)^#+\s[^#\n]*{heading_pattern}[^#\n]*$", text, re.M | re.I)
    if not m:
        return None
    start = m.end()
    nxt = re.search(r"(?m)^#{1,3}\s", text[start:])
    return text[start: start + nxt.start()] if nxt else text[start:]


def check(text):
    errors, warnings = [], []

    # E1 五节齐备
    missing_tiers = []
    for name, pat in TIER_PATTERNS:
        if _section(text, pat) is None:
            missing_tiers.append(name)
    if missing_tiers:
        errors.append("E1 缺节：" + "、".join(missing_tiers) +
                      "（五节结构见 regression-testing SKILL.md 产出结构）")

    # E2 变更基线
    if not BASELINE_RE.search(text):
        errors.append("E2 缺变更基线行（`base...head` / 对比基线）——回归范围凭基线划界，"
                      "缺失则清单不可追溯")

    # W1 排除缺理由
    excl = _section(text, TIER_PATTERNS[4][1])
    if excl:
        no_reason = [ln for ln in excl.split("\n")
                     if re.search(r"TC-\d+-\d+", ln) and not RATIONALE_HINTS.search(ln)]
        if no_reason:
            warnings.append(
                f"W1 显式排除 {len(no_reason)} 条缺理由（模块级/字段级/无依赖说明）——"
                "排除须可复核，否则等于'没说不测什么'")

    # W2 P0 条目缺依据
    must = _section(text, TIER_PATTERNS[0][1])
    if must:
        rows = [ln for ln in must.split("\n") if re.match(r"^\s*[-|]\s*\S", ln)]
        items = [ln for ln in rows if re.search(r"TC-\d+-\d+", ln)]
        no_rat = [ln for ln in items if not RATIONALE_P0.search(ln)]
        if no_rat:
            warnings.append(
                f"W2 必须回归 {len(no_rat)} 条缺依据（code_refs 命中 / 风险锚点 / 模块映射）——"
                "每条须可追溯")
        if not items:
            pass  # P0 空是正常的（无变更或全排除）
        elif items and not RATIONALE_P0.search(must):
            pass  # 已在逐条判

    # W3 影响不明缺 evidence/status
    unclear = _section(text, TIER_PATTERNS[3][1])
    if unclear:
        rows = [ln for ln in unclear.split("\n") if re.search(r"TC-\d|影响|不明", ln)
                and not re.match(r"^#", ln)]
        no_mark = [ln for ln in rows if not re.search(r"evidence|E[0-4]|status", ln, re.I)]
        if no_mark:
            warnings.append(
                f"W3 影响不明 {len(no_mark)} 条缺 evidence/status 标注"
                "（按 core/evidence.md 证据分级）")

    return errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="回归清单校验（regression-testing 产出）")
    ap.add_argument("checklist", help="回归清单 markdown")
    ap.add_argument("--json", action="store_true", help="机读输出")
    args = ap.parse_args(argv)
    p = Path(args.checklist)
    if not p.is_file():
        print(f"错误: 文件不存在 {p}", file=sys.stderr)
        return 1
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"错误: 非 UTF-8 编码（{p}）", file=sys.stderr)
        return 1
    errors, warnings = check(text)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings},
                         ensure_ascii=False, indent=1))
    else:
        print(f"回归清单检查 — {p}")
        for w in warnings:
            print(f"  W  {w}")
        for e in errors:
            print(f"  E  {e}")
        print(("✅ 回归清单结构通过（三级分级 + 显式排除齐备）" if not errors else
               f"✗ {len(errors)} 个错误（结构不完整，定稿前须补齐）") + f": {p.name}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
