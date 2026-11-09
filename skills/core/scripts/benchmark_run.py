#!/usr/bin/env python3
"""Benchmark 确定性模式运行器——不依赖外部模型通道。

接受"已有产物文件"作为输入，运行全部适用的确定性校验器，输出多维评分。
外部模型通道恢复后可扩展 generate 模式。

用法：
    # 对单份产物评分
    python3 benchmark_run.py --file 测试策略.md --type strategy
    
    # 对目录中的全部产物评分（自动识别类型）
    python3 benchmark_run.py --dir eval/results/runs/20260919_*/outputs/
    
    # 对比两个版本的评分
    python3 benchmark_run.py --dir out_main/ --label master
    python3 benchmark_run.py --dir out_rsi/  --label experiment
    python3 benchmark_run.py --compare results/master.json results/experiment.json

输出：JSON 格式的多维评分结果（stdout）或对比表（--compare）。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

# ---- 类型识别 ----
TYPE_PATTERNS = [
    ("strategy",   r"test_strategy|type_scope|Risk Map",            re.I),
    ("cases",      r"TC-\d+-\d+|markmap|测试用例",                    0),
    ("explore",    r"探索笔记|Charter|发现的 Bug|未解之谜",             0),
    ("bug_entry",  r"BUG-\d+|根因分析|严重程度.*S[0-2]",              re.I),
    ("regression", r"回归清单|必须回归|建议回归|无影响确认",              0),
    ("report",     r"exit_code_hint|机读摘要|测试报告",               re.I),
]


def detect_type(text):
    """按特征模式识别产物类型。"""
    import re as _re
    for type_name, pat, flags in TYPE_PATTERNS:
        if flags:
            if _re.search(pat, text, flags):
                return type_name
        elif _re.search(pat, text):
            return type_name
    return "unknown"


# ---- 校验器注册表 ----
# (checker_module, check_function_or_script, applies_to_types)
GATES = {
    "strategy":   [("validate_schema.py",  None, "strategy_gate")],
    "cases":      [("case_lint.py",        None, "lint"),
                   ("validate_schema.py",  None, "schema_dual")],
    "explore":    [("explore_note_check.py", "check", "note_check")],
    "bug_entry":  [("bug_entry_check.py",    "check", "bug_check")],
    "regression": [("regression_checklist_check.py", "check", "regression_check")],
    "report":     [("report_meta_check.py",  "check", "report_check")],
}


def run_gate(script, func, mode, file_path):
    """运行单个校验器，返回 (exit_code, errors, warnings) 或 None。"""
    script_path = SCRIPTS / script
    if not script_path.is_file():
        return None
    try:
        if func:
            # 直接 import 并调用 check 函数
            import importlib
            spec = importlib.util.spec_from_file_location(script.replace(".py", ""), script_path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[script.replace(".py", "")] = mod
            spec.loader.exec_module(mod)
            check_fn = getattr(mod, func, None)
            if check_fn is None:
                return None
            text = Path(file_path).read_text(encoding="utf-8", errors="replace")
            errors, warnings = check_fn(text)
            return (0 if not errors else 1, errors, warnings)
        else:
            # subprocess 调用 CLI
            r = subprocess.run(
                [sys.executable, str(script_path), str(file_path)],
                capture_output=True, text=True, timeout=30)
            errors = [ln.strip()[2:] for ln in r.stdout.splitlines()
                      if ln.strip().startswith("E ")]
            warnings = [ln.strip()[2:] for ln in r.stdout.splitlines()
                        if ln.strip().startswith("W ")]
            return (r.returncode, errors, warnings)
    except Exception as exc:
        return (1, [f"校验器异常: {exc}"], [])


def score_file(file_path):
    """对单份产物运行全部适用校验器，返回评分结果。"""
    p = Path(file_path)
    if not p.is_file():
        return {"error": f"文件不存在: {p}"}
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"error": str(e)}

    file_type = detect_type(text)
    if file_type == "unknown":
        return {"file": str(p), "type": "unknown", "skipped": True}

    gates = GATES.get(file_type, [])
    results = {}
    total_errors = 0
    total_warnings = 0
    gates_run = 0
    gates_passed = 0

    for script, func, mode in gates:
        r = run_gate(script, func, mode, p)
        if r is None:
            continue
        code, errors, warnings = r
        gates_run += 1
        gates_passed += (1 if code == 0 else 0)
        total_errors += len(errors)
        total_warnings += len(warnings)
        results[script] = {"exit_code": code, "errors": errors, "warnings": warnings}

    if gates_run == 0:
        return {"file": str(p), "type": file_type, "skipped": True, "reason": "无适用校验器"}

    return {
        "file": str(p),
        "type": file_type,
        "gates_run": gates_run,
        "gates_passed": gates_passed,
        "gate_pass_rate": round(gates_passed / gates_run, 3) if gates_run else 0,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "clean": total_errors == 0,
        "gate_results": results,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Benchmark 确定性模式运行器")
    ap.add_argument("--file", help="单份产物文件")
    ap.add_argument("--dir", help="产物目录（递归扫描 .md/.yaml）")
    ap.add_argument("--label", default="", help="版本标签（用于对比）")
    ap.add_argument("--compare", nargs=2, metavar=("FILE_A", "FILE_B"),
                    help="对比两个评分结果 JSON")
    ap.add_argument("--output", help="输出文件（默认 stdout）")
    args = ap.parse_args(argv)

    if args.compare:
        a = json.loads(Path(args.compare[0]).read_text())
        b = json.loads(Path(args.compare[1]).read_text())
        la = a.get("label", "A"); lb = b.get("label", "B")
        sa = a.get("summary", {}); sb = b.get("summary", {})
        print(f"\n{'指标':24s} {la:>12s} {lb:>12s} {'变化':>8s}")
        print("-" * 60)
        for key in ("files_scored", "clean_count", "clean_rate", "total_errors", "total_warnings"):
            va, vb = sa.get(key, 0), sb.get(key, 0)
            delta = vb - va
            marker = "" if delta == 0 else (" ↑" if delta > 0 else " ↓")
            fmt = ".1%" if "rate" in key else "d"
            print(f"{key:24s} {va:>12} {vb:>12} {delta:>+8}{marker}")
        return 0

    files = []
    if args.file:
        files = [args.file]
    elif args.dir:
        d = Path(args.dir)
        files = sorted(set(
            str(f) for f in list(d.rglob("*.md")) + list(d.rglob("*.yaml"))
            if "skills/" not in str(f) and "__pycache__" not in str(f)
        ))
    else:
        print("错误: 需要 --file 或 --dir", file=sys.stderr)
        return 1

    results = [score_file(f) for f in files]
    scored = [r for r in results if "error" not in r and not r.get("skipped")]
    clean = sum(1 for r in scored if r.get("clean"))
    total_err = sum(r.get("total_errors", 0) for r in scored)
    total_warn = sum(r.get("total_warnings", 0) for r in scored)

    summary = {
        "label": args.label,
        "files_scored": len(scored),
        "files_skipped": len(results) - len(scored),
        "clean_count": clean,
        "clean_rate": round(clean / len(scored), 3) if scored else 0,
        "total_errors": total_err,
        "total_warnings": total_warn,
        "by_type": {},
    }
    for r in scored:
        t = r["type"]
        if t not in summary["by_type"]:
            summary["by_type"][t] = {"total": 0, "clean": 0, "errors": 0}
        summary["by_type"][t]["total"] += 1
        summary["by_type"][t]["clean"] += (1 if r.get("clean") else 0)
        summary["by_type"][t]["errors"] += r.get("total_errors", 0)

    output = {"label": args.label, "summary": summary, "results": results}
    out_json = json.dumps(output, ensure_ascii=False, indent=1)
    if args.output:
        Path(args.output).write_text(out_json, encoding="utf-8")
        print(f"结果已写入 {args.output}")
    else:
        print(out_json)
        print(f"\n📊 汇总: {len(scored)} 份产物 | 清洁率 {summary['clean_rate']:.1%} "
              f"| 错误 {total_err} | 告警 {total_warn}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
