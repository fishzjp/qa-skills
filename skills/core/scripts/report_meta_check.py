#!/usr/bin/env python3
"""测试报告「机读摘要」块校验器——把聚合契约变成可机器判定的门。

背景：`core/report-template.md` 第 7 节规定报告末节追加固定的 yaml「机读摘要片段」，
并写明"流水线聚合与质量门禁**只解析此节**"。生产方有四个（qa 收尾 / api-testing /
automated-e2e-testing / test-reliability），而此前**没有任何脚本校验这个块**——
块写坏（缺 total、exit_code_hint 写成字符串、triage 冒出未定义分类）时，
人读内容照常可看、仓库侧没有红灯，聚合侧才炸。

用法：
    python3 report_meta_check.py 测试报告_20261109.md [--json]

检查项（E = 错误，阻断；W = 告警，人工确认）：
    E1  未找到机读摘要块（含 meta: + summary: + exit_code_hint: 的 yaml 围栏），或出现多个
    E2  必填字段缺失：meta.project / meta.date / meta.source_run /
        summary.total / summary.passed / summary.failed / summary.blocked /
        exit_code_hint / open_items / bugs
    E3  枚举越界：source_run ∈ {pr-smoke, nightly-full, release-gate}；
        exit_code_hint ∈ {0,1,2,3}；triage_distribution 的键 ⊆ {A,B1,B2,C,D,U}
    E4  计数自洽：summary 各值为非负整数；passed+failed+blocked > total 报错
    E5  bugs 条目：每条须含 id / severity（S0|S1|S2）/ status（新建|已修复待验证|已验证关闭|不予修复）
    W1  已执行数（passed+failed+blocked）< total——报告正文须说明未执行原因（§2 未执行列）

退出码：0 = 无错误（告警不算失败）；1 = 有错误。
"""
import argparse
import json
import re
import sys
from pathlib import Path

FENCE_RE = re.compile(r"```ya?ml\n(.*?)```", re.S)
META_MARKERS = ("meta:", "summary:", "exit_code_hint")
SOURCE_RUNS = {"pr-smoke", "nightly-full", "release-gate"}
EXIT_CODES = {0, 1, 2, 3}
TRIAGE_KEYS = {"A", "B1", "B2", "C", "D", "U"}
SEVERITIES = {"S0", "S1", "S2"}
BUG_STATUSES = {"新建", "已修复待验证", "已验证关闭", "不予修复"}


def find_meta_block(text):
    """返回 (块文本, 块数)。块数 >1 属歧义。"""
    blocks = [b for b in FENCE_RE.findall(text)
              if all(mk in b for mk in META_MARKERS)]
    return (blocks[0] if blocks else None), len(blocks)


def _strip_comment(value):
    """去掉行尾 `# 注释`（引号内的 # 不算注释）。

    模板与真实产物普遍带行尾注释（`summary:   # ← §2 执行统计`、`exit_code_hint: 0  # ← 对照…`），
    而 Agent 会照抄模板——不剥注释会把 `0  # ← …` 整串当枚举值，反而对合规产物误报。
    """
    out, quote = [], None
    for ch in value:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            out.append(ch)
            continue
        if ch == "#":
            break
        out.append(ch)
    return "".join(out).strip()


def _scalar(block, key):
    m = re.search(rf"(?m)^[ \t]*{key}[ \t]*:[ \t]*(.+?)[ \t]*$", block)
    if not m:
        return None
    return _strip_comment(m.group(1)).strip("\"'")


_OPEN_PARENT_RE = r"(?m)^([ \t]*){parent}[ \t]*:[ \t]*(?:#[^\n]*)?$\n(.*?)(?=^\1\w|\Z)"


def _nested(block, parent):
    """取 parent: 之下缩进块的文本（父键行允许带行尾注释；到同缩进的下一个键为止）。"""
    m = re.search(_OPEN_PARENT_RE.format(parent=parent), block, re.S)
    return m.group(2) if m else None


def _int(val):
    try:
        return int(str(val).strip())
    except (TypeError, ValueError):
        return None


def check(text):
    errors, warnings = [], []
    block, n = find_meta_block(text)
    if block is None:
        errors.append("E1 未找到机读摘要块（需含 meta: / summary: / exit_code_hint 的 yaml 围栏）"
                      "——report-template.md 第 7 节要求报告末节固定追加该节")
        return errors, warnings
    if n > 1:
        errors.append(f"E1 出现 {n} 个机读摘要块——聚合方只解析一个，必须唯一")

    meta = _nested(block, "meta") or ""
    missing = []
    for k in ("project", "date", "source_run"):
        if not (_scalar(meta, k) or "").strip():
            missing.append(f"meta.{k}")
    summary = _nested(block, "summary") or ""
    counts = {}
    for k in ("total", "passed", "failed", "blocked"):
        v = _scalar(summary, k)
        iv = _int(v)
        counts[k] = iv
        if v is None:
            missing.append(f"summary.{k}")
        elif iv is None:
            if "{" in v or v.startswith("<"):
                errors.append(f"E4 summary.{k} 仍是模板占位符 {v}——须替换为实际统计数字")
            else:
                errors.append(f"E4 summary.{k}='{v}' 不是整数")
    for k in ("exit_code_hint", "open_items"):
        if _scalar(block, k) is None:
            missing.append(k)
    if not re.search(r"(?m)^[ \t]*bugs[ \t]*:", block):
        missing.append("bugs")
    if missing:
        errors.append("E2 机读摘要缺必填字段：" + "、".join(missing))

    src = (_scalar(meta, "source_run") or "").strip()
    if src and src not in SOURCE_RUNS:
        hint = ("——仍是模板占位符，须替换为 pr-smoke / nightly-full / release-gate 之一"
                if "{" in src or "|" in src else
                "（触发分层口径见 pipeline-integration 第 1 节）")
        errors.append(f"E3 meta.source_run='{src}' 不在 {sorted(SOURCE_RUNS)}{hint}")
    ec = _scalar(block, "exit_code_hint")
    if ec is not None and ec != "" and _int(ec) not in EXIT_CODES:
        errors.append(f"E3 exit_code_hint='{ec}' 不在 0/1/2/3（语义见 pipeline-integration 约定三）")

    triage = _nested(block, "triage_distribution")
    if triage is not None:
        keys = re.findall(r"(?m)^[ \t]+([A-Z]\d?)[ \t]*:", triage)
        bad = [k for k in keys if k not in TRIAGE_KEYS]
        if bad:
            errors.append(f"E3 triage_distribution 含未定义分类 {bad}（合法：{sorted(TRIAGE_KEYS)}）")

    if all(v is not None for v in counts.values()) and None not in counts.values():
        done = counts["passed"] + counts["failed"] + counts["blocked"]
        if any(v < 0 for v in counts.values()):
            errors.append("E4 summary 计数不得为负")
        if done > counts["total"]:
            errors.append(f"E4 passed+failed+blocked={done} 大于 total={counts['total']}")
        elif done < counts["total"]:
            warnings.append(f"W1 已执行 {done} 条 < total {counts['total']} 条——正文 §2 须说明未执行原因")

    for m in re.finditer(r"(?m)^[ \t]*-[ \t]*\{?(.+)$", block):
        item = m.group(1)
        if not re.search(r"id[ \t]*:", item):
            continue  # 非 bug 条目（如梯形列表）不参与
        miss = [k for k, pat in (("severity", r"severity[ \t]*:"),
                                 ("status", r"status[ \t]*:")) if not re.search(pat, item)]
        if miss:
            errors.append(f"E5 bug 条目缺字段 {miss}：{item.strip()[:60]}")
            continue
        sev = re.search(r"severity[ \t]*:[ \t]*([A-Z]\d)", item)
        st = re.search(r"status[ \t]*:[ \t]*([^,}\s]+)", item)
        if sev and sev.group(1) not in SEVERITIES:
            errors.append(f"E5 severity='{sev.group(1)}' 不在 S0/S1/S2（用例优先级 P 系不用于缺陷定级）")
        if st and st.group(1) not in BUG_STATUSES:
            errors.append(f"E5 status='{st.group(1)}' 不在 {sorted(BUG_STATUSES)}")
    return errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="测试报告机读摘要块校验")
    ap.add_argument("report", help="测试报告 markdown")
    ap.add_argument("--json", action="store_true", help="机读输出")
    args = ap.parse_args(argv)
    p = Path(args.report)
    if not p.exists():
        print(f"错误: 文件不存在 {p}", file=sys.stderr)
        return 1
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"错误: 报告非 UTF-8 编码（{p}）", file=sys.stderr)
        return 1
    errors, warnings = check(text)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings},
                         ensure_ascii=False, indent=1))
    else:
        print(f"机读摘要检查 — {p}")
        for w in warnings:
            print(f"  W  {w}")
        for e in errors:
            print(f"  E  {e}")
        print(("✅ 机读摘要通过（聚合契约合规）" if not errors
               else f"✗ {len(errors)} 个错误（聚合方将无法可靠解析）") + f": {p.name}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
