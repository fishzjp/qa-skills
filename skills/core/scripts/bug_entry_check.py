#!/usr/bin/env python3
"""Bug 条目校验器（bug-analysis 产出）——把 Bug 条目的字段与定级纪律变成可判定的门。

背景：`core/report-template.md` §3 规定 Bug 条目 13 个字段（8 基础 + 5 扩展=bug-analysis
的填写范围），`bug-analysis/SKILL.md` 另有硬纪律：根因必须标 status（Inference / Verified，
不得把推断当事实）、严重程度用 S0/S1/S2（P 系是用例优先级，不得混用）、证据标 E0–E4。
此前**没有任何脚本校验**这些——人读时"看起来专业"，机器侧无从判定。

用法：
    python3 bug_entry_check.py Bug条目_2026-11-09.md [--json]

检查项（E = 错误，阻断定稿；W = 告警，需人工确认）：
    E1  缺必填字段（8 基础 + 5 扩展，见 REPORT_FIELDS）
    E2  严重程度未用 S0/S1/S2，或混入 P0/P1/P2（两套体系必须分离）
    E3  根因分析未标 status: Inference / Verified（推断当事实是本 skill 头号红线）
    W1  证据或根因分析里没有 E0–E4 证据等级
    W2  根因分析没有 `文件:行` 定位（只给现象不给分叉点）
    W3  修复建议写成完整补丁（≥3 行代码围栏 or 出现 def/class/函数体块）——越界替开发写代码
    W4  回归建议既无 TC 编号也无场景描述

退出码：0 = 无错误（告警不算失败）；1 = 有错误。
"""
import argparse
import json
import re
import sys
from pathlib import Path

# 8 基础 + 5 扩展（report-template §3）
BASE_FIELDS = ["严重程度", "状态", "发现方式", "复现步骤", "预期行为", "实际行为", "证据", "环境"]
EXT_FIELDS = ["根因分析", "影响范围", "Severity 依据", "修复建议", "回归建议"]
REPORT_FIELDS = BASE_FIELDS + EXT_FIELDS

# 字段名后可能带括注（真实产物：`- **修复建议**（方向，不写补丁）：`）——
# 第一版要求 name 后直接冒号，对真实产物误报 E1（新闸门必须先用真实产物自测）
FIELD_RE = re.compile(r"^[ \t]*[-*][ \t]*\*\*([^*\n]+?)\*\*[ \t]*(?:[（(][^）)\n]*[）)])?[ \t]*[:：]", re.M)
S_LEVEL_RE = re.compile(r"\bS[0-2]\b")
P_LEVEL_RE = re.compile(r"\bP[0-2]\b")
STATUS_RE = re.compile(r"status\s*[:：]\s*(Inference|Verified)", re.I)
EVID_RE = re.compile(r"\bE[0-4]\b")
FILE_LINE_RE = re.compile(r"[\w./-]+\.(?:py|js|ts|tsx|jsx|go|java|rb|php|sql|yaml|yml|json):\d+")
CODE_FENCE_RE = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.S)
CODE_DEF_RE = re.compile(r"(?m)^\s*(?:def|class|function|public|private|impl|func)\s+\w+")


def _field_text(text, name):
    """取某字段的值：到**同级或更浅缩进**的下一个字段行为止。

    真实产物的扩展字段是嵌套列表（`- **根因分析**：\n  - **Root Cause**（status: …）…`），
    第一版"遇到任何加粗字段就截断"会把子条目当新字段，导致根因内容为空 → E3/W1/W2 全误报
    （新闸门必须用真实产物自测——本轮实测教训）。
    """
    lines = text.split("\n")
    for i, line in enumerate(lines):
        m = re.match(rf"^([ \t]*)[-*][ \t]*\*\*{re.escape(name)}\*\*[ \t]*(?:[（(][^）)]*[）)])?[ \t]*[:：][ \t]*(.*)$", line)
        if not m:
            continue
        indent = len(m.group(1).expandtabs(4))
        body = [m.group(2)]
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                body.append("")
                continue
            cur_indent = len(nxt) - len(nxt.lstrip())
            is_field = re.match(r"^[ \t]*[-*][ \t]*\*\*[^*\n]+\*\*[ \t]*(?:[（(][^）)]*[）)])?[ \t]*[:：]", nxt)
            if is_field and cur_indent <= indent:
                break
            if re.match(r"^#{1,6}\s", nxt) and cur_indent <= indent:
                break
            body.append(nxt)
        return "\n".join(body)
    return None


def check(text):
    errors, warnings = [], []
    present = set(FIELD_RE.findall(text))
    missing = [f for f in REPORT_FIELDS if f not in present]
    if missing:
        errors.append("E1 Bug 条目缺字段：" + "、".join(missing) +
                      f"（共 {len(REPORT_FIELDS)} 项：8 基础 + 5 扩展，见 core/report-template.md §3）")

    sev = _field_text(text, "严重程度") or ""
    if sev.strip():
        if not S_LEVEL_RE.search(sev):
            errors.append(f"E2 严重程度未用 S0/S1/S2：{sev.strip()[:50]}")
        elif P_LEVEL_RE.search(sev) and not re.search(r"P[0-2]\s*是.*用例优先级|口径消歧|不混用", sev):
            warnings.append("E2 严重程度里同时出现 P 系字样——注意 S 系（缺陷）与 P 系（用例优先级）"
                            "是两套体系，混写易被误读")

    root = _field_text(text, "根因分析")
    if root is not None:
        # 只在 Root Cause 行本身认 status 标注：字段内别处出现"可升级为 Verified"这类
        # 散文提及不算标注（实测漏洞：删掉标注后仍因散文里的 Verified 判通过）
        # 优先找 Root Cause 行（status 标注应挂在那里）；没有该行时才回退到"根因："
        root_cause_line = ""
        for ln in root.split("\n"):
            if re.search(r"Root\s*Cause", ln, re.I):
                root_cause_line = ln
                break
        if not root_cause_line:
            for ln in root.split("\n"):
                if re.search(r"根因\s*[:：]", ln):
                    root_cause_line = ln
                    break
        if not STATUS_RE.search(root_cause_line):
            errors.append("E3 根因分析未标 status: Inference / Verified——"
                          "读代码推断与已复现验证必须区分，不得把推断当事实")
        if not EVID_RE.search(root):
            warnings.append("W1 根因分析里没有 E0–E4 证据等级（证据分级见 core/evidence.md）")
        ev = _field_text(text, "证据") or ""
        if not EVID_RE.search(ev):
            warnings.append("W1 「证据」字段没有 E0–E4 证据等级")
        if not FILE_LINE_RE.search(root):
            warnings.append("W2 根因分析没有 `文件:行` 定位——追到行为与预期的分叉点是本 skill 的交付判据")

    fix = _field_text(text, "修复建议")
    if fix is not None and fix.strip():
        heavy = [b for b in CODE_FENCE_RE.findall(fix) if len(b.strip().splitlines()) >= 3]
        if heavy or CODE_DEF_RE.search(fix):
            warnings.append("W3 修复建议出现成段代码/函数定义——本 skill 只给修复方向，"
                            "不越界替开发写补丁")

    reg = _field_text(text, "回归建议")
    if reg is not None and reg.strip():
        if not (re.search(r"TC-\d+-\d+", reg) or re.search(r"场景|路径|用例", reg)):
            warnings.append("W4 回归建议既无 TC 编号也无场景描述——修复后无法落地验证")
    return errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Bug 条目校验（bug-analysis 产出）")
    ap.add_argument("entry", help="Bug 条目 markdown")
    ap.add_argument("--json", action="store_true", help="机读输出")
    args = ap.parse_args(argv)
    p = Path(args.entry)
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
        print(f"Bug 条目检查 — {p}")
        for w in warnings:
            print(f"  W  {w}")
        for e in errors:
            print(f"  E  {e}")
        print(("✅ Bug 条目字段与纪律通过" if not errors else
               f"✗ {len(errors)} 个错误（补字段/改定级后才能定稿）") + f": {p.name}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
