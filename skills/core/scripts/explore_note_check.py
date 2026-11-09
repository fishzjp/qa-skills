#!/usr/bin/env python3
"""探索笔记校验器（exploratory-testing 产出）——把探索笔记的结构与证据纪律变成可判定的门。

背景：`exploratory-testing/SKILL.md` 定义了六节结构与风险条目的五要素
（level / evidence / verification / confidence / status），但此前**没有任何脚本校验**。
实测代价（2026-11-09，两份同一任务的真实产物）：
- Round 17 之前：10 条风险里 **0 条**带 `verification`（该字段只写在散文里）
- Round 17 之后：10/10 —— 说明字段确实会被写，但**只靠指令、没有机器门**，
  换模型/旧产物就会漏（与 core 其它"结构化才写"的实测规律一致）

用法：
    python3 explore_note_check.py 探索笔记_主题.md [--json]

检查项（E = 错误，阻断定稿；W = 告警，需人工确认）：
    E1  六节齐备：Charter / 系统理解 / 风险清单 / 测试想法 / 发现的 Bug / 未解之谜
    E2  Charter 三要素：目标 / 范围 / 停点（或时长、时间盒）
    E3  风险清单里**没有任何**带 level 的条目（等于整份笔记没评级）
    W1  单条风险缺 verification（验证强度）——计数合并输出，避免逐条刷屏
    W2  单条风险缺 confidence 或 status
    W3  单条风险的 evidence 里没有 E0–E4 等级
    W4  测试想法为空，或条目未标归属（可直接转用例 / 需先澄清 / 需专项环境）
    W5  「发现的 Bug」节有条目但全无 Hypothesis / 未定性 / 待定性标注

退出码：0 = 无错误（告警不算失败）；1 = 有错误。
"""
import argparse
import json
import re
import sys
from pathlib import Path

SECTIONS = [
    ("Charter", ("## Charter", "## 1. Charter", "本轮探索的使命")),
    ("系统理解", ("## 系统理解",)),
    ("风险清单", ("## 风险清单",)),
    ("测试想法", ("## 测试想法",)),
    ("发现的 Bug", ("## 发现的 Bug", "## 发现的Bug")),
    ("未解之谜", ("## 未解之谜",)),
]
# 标签在粗体内可组合（实测真实产物写的是 `**时长 / 停点**：`、`**时长/停点**：`），
# 故按"该行是列表项 + 标签含关键词 + 后随冒号"判定，而不是要求标签以关键词开头——
# 第一版按开头匹配，对两份真实产物全部误报（新闸门必须先用真实产物自测）。
def _label(*keywords):
    kw = "|".join(keywords)
    return (r"[-*]\s+(?:\*\*)?[^\n:：]{0,24}?(?:" + kw + r")[^\n:：]{0,24}?(?:\*\*)?\s*[:：]")


CHARTER_PARTS = [("目标", _label("目标")),
                 ("范围", _label("范围")),
                 ("停点", _label("停点", "时长", "时间盒", "停止条件", "停点条件"))]
RISK_LINE_RE = re.compile(r"^\s*[-*]\s*\*{0,2}\s*R\d+")
EVIDENCE_LEVEL_RE = re.compile(r"\bE[0-4]\b")
INSIGHT_OWNER_RE = re.compile(r"转用例|可直接转|需先澄清|需专项|归属|建议归属")
UNSETTLED_MARK_RE = re.compile(r"Hypothesis|未定性|待定性|hypothesis|待裁决", re.I)


def _section_body(text, markers):
    """取某节正文（到下一个同级或更高级标题为止）。"""
    for mk in markers:
        i = text.find(mk)
        if i < 0:
            continue
        rest = text[i:]
        m = re.search(r"(?m)^##\s+\S", rest[len(mk):])
        return rest if not m else rest[: len(mk) + m.start()]
    return None


def check(text):
    errors, warnings = [], []

    # E1 六节
    missing = [name for name, marks in SECTIONS if _section_body(text, marks) is None]
    if missing:
        errors.append("E1 缺节：" + "、".join(missing) +
                      "（探索笔记六节结构见 exploratory-testing SKILL.md 的 Schema）")

    # E2 Charter 三要素
    charter = _section_body(text, ("Charter",)) or ""
    lack = [name for name, pat in CHARTER_PARTS if not re.search(pat, charter)]
    if not charter:
        pass  # 已由 E1 报
    elif lack:
        errors.append("E2 Charter 缺要素：" + "、".join(lack) +
                      "（三要素：目标 / 范围 / 停点或时间盒）")

    # 风险条目
    risks = [ln for ln in text.split("\n") if RISK_LINE_RE.match(ln)]
    if risks:
        if not any(re.search(r"level\s*[:：]", ln, re.I) for ln in risks):
            errors.append(f"E3 风险清单 {len(risks)} 条，全部缺 level——整份笔记等于未评级")

        no_ver = [ln for ln in risks if not re.search(r"verification\s*[:：]", ln, re.I)]
        no_conf = [ln for ln in risks if not re.search(r"confidence\s*[:：]", ln, re.I)]
        no_stat = [ln for ln in risks if not re.search(r"status\s*[:：]", ln, re.I)]
        no_ev = [ln for ln in risks if not EVIDENCE_LEVEL_RE.search(ln)]

        if no_ver:
            warnings.append(f"W1 {len(no_ver)}/{len(risks)} 条风险缺 verification（验证强度："
                            "已交叉验证 / 单次样本 / 未重试 / 未换身份·浏览器核实）")
        if no_conf or no_stat:
            warnings.append(f"W2 风险条目缺字段：confidence {len(no_conf)} 条、status {len(no_stat)} 条")
        if no_ev:
            warnings.append(f"W3 {len(no_ev)}/{len(risks)} 条风险的 evidence 无 E0–E4 等级")

    # W4 测试想法
    ideas = _section_body(text, ("## 测试想法",))
    if ideas is not None:
        bullets = [ln for ln in ideas.split("\n") if re.match(r"^\s*[-*]\s+\S", ln)]
        if not bullets:
            warnings.append("W4 测试想法节为空——探索至少应留下可转化的候选")
        elif not any(INSIGHT_OWNER_RE.search(ln) for ln in bullets):
            warnings.append("W4 测试想法未标归属（可直接转用例 / 需先澄清 / 需专项环境）")

    # W5 发现的 Bug 定性
    bugs = _section_body(text, ("## 发现的 Bug", "## 发现的Bug"))
    if bugs is not None:
        items = [ln for ln in bugs.split("\n") if re.match(r"^\s*[-*]\s+\S", ln)]
        if items and not any(UNSETTLED_MARK_RE.search(ln) for ln in items):
            warnings.append("W5 「发现的 Bug」有条目但全无 Hypothesis / 未定性标注"
                            "——未定性缺陷不得写成已确认结论")
    return errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="探索笔记校验（exploratory-testing 产出）")
    ap.add_argument("note", help="探索笔记 markdown")
    ap.add_argument("--json", action="store_true", help="机读输出")
    args = ap.parse_args(argv)
    p = Path(args.note)
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
        print(f"探索笔记检查 — {p}")
        for w in warnings:
            print(f"  W  {w}")
        for e in errors:
            print(f"  E  {e}")
        print(("✅ 探索笔记结构通过" if not errors else
               f"✗ {len(errors)} 个错误（结构不完整，定稿前须补齐）") + f": {p.name}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
