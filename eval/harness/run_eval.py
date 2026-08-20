#!/usr/bin/env python3
"""qa-skills Benchmark harness v2（科学评估体系重构版）.

用法：
  python3 eval/harness/run_eval.py setup-e2e           # 安装编译+执行检查依赖（一次性）
  python3 eval/harness/run_eval.py audit-annotations   # GT 标注独立审计（异角色评审，记录一致性）
  python3 eval/harness/run_eval.py generate --samples 3 # 生成：每任务×模式 n 个采样
  python3 eval/harness/run_eval.py score               # 评分：逐采样 judge + 成对评审 + 真实执行 + 统计推断 + 冻结门判定

方法学（v2，对齐行业主流）：
  - 多样本生成：每任务×模式 n≥3 次独立采样，任务指标 = 均值 ± SD（量化生成方差）
  - 统计推断：On/Off 差值在任务层做配对 bootstrap（10k 次）报 95% CI；成对胜率报 Wilson 95% CI
  - 成对评审（pairwise）：On vs Off 同任务并排 + 位置互换，消除绝对打分的刻度校准噪声（MT-Bench/AlpacaEval 范式）
  - LLM judge：3 采样多数表决 + JSON Schema 约束 + 固定 rubric；与被评同模型（当前 plan 仅此一个可用模型，
    为已声明的限制，缓解 = pairwise + 位置互换 + 多数表决 + 标注独立审计）
  - 真实执行：E2E 产物跑真实浏览器（mock 被测应用 + chromium），API 产物跑真实 HTTP 服务（mock API + pytest），
    报 Execution Success Rate 与重跑稳定性（SWE-bench 式执行验证）
  - 标注独立审计：GT 可测点由"未参与编写 skill 的独立评审角色"审计范围/歧义/遗漏，一致性落盘
  - 门冻结：GATES 在 EXPECTED.md 声明冻结版本与阈值来源；验证轮为冻结后的独立新采样数据
"""
import argparse
import concurrent.futures
import json
import math
import os
import random
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "eval" / "golden"
RESULTS = REPO / "eval" / "results"

# .env（不入 git）加载：OPENCODE_GO_KEY 等
_env_file = REPO / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import requests as _requests  # noqa: E402

OPENCODE_BASE = os.environ.get("OPENCODE_BASE", "https://opencode.ai/zen/go/v1")

GEN_MODEL = os.environ.get("EVAL_GEN_MODEL", "glm-5-2-260617")
JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", "oc:deepseek-v4-flash")
PAIR_JUDGE_MODEL = os.environ.get("EVAL_PAIR_JUDGE_MODEL", "oc:kimi-k3")
AUDIT_MODEL = os.environ.get("EVAL_AUDIT_MODEL", "oc:kimi-k3")
GENERATE_TIMEOUT = int(os.environ.get("EVAL_GEN_TIMEOUT", "900"))
JUDGE_TIMEOUT = int(os.environ.get("EVAL_JUDGE_TIMEOUT", "600"))
MAX_OUTPUT_TOKENS = 32768
WORKERS = int(os.environ.get("EVAL_WORKERS", "4"))
JUDGE_SAMPLES = int(os.environ.get("EVAL_JUDGE_SAMPLES", "3"))
BOOTSTRAP_N = 10000

DETECTION_KEYS = ["known_bugs", "planted_violations", "expected_issues", "expected_risks",
                  "expected_findings", "expected_selections"]
TCW_PREFIXES = ("tcw-", "rev-")

PERSONA_OFF = (
    "你是一名资深软件测试工程师。请阅读用户提供的任务与材料，完成任务的最终产出。"
    "直接输出产出文件的完整内容，不要输出与产出无关的解释。"
)

EVAL_PREAMBLE = """【交付约定（评测模式）】
- 单轮交付：输入材料即全部已知信息；需要澄清的问题不要停下来等待答复，以「待澄清」清单并入交付文件末尾后继续完成交付。
- 只输出任务要求的那一份交付文件本身的完整内容；任务未明确要求的附加产物（如 Schema 抽取文件、独立审查报告）不要输出。
- 不要输出工作流过程叙述、阶段说明、与用户的对话或元评论——文件内容之外一个字都不要有。
"""

# ---------------------------------------------------------------- 门定义（v1.0 冻结，见 eval/EXPECTED.md）
GATES = {
    "G1_tcw_cov_mean": {"desc": "tcw 类有效覆盖均值差 ≥ +5pp 且 bootstrap 95%CI 下界 > 0", "min_diff": 0.05},
    "G1_state_cov": {"desc": "状态机任务有效覆盖差 ≥ +20pp", "min_diff": 0.20},
    "G2_exec": {"desc": "tcw 类 On 可执行性均值 ≥ 0.85", "min": 0.85},
    "G3_bug": {"desc": "代码任务 bug 检出 On ≥ 75%", "min": 0.75},
    "G4_compile": {"desc": "代码类任务 On 编译通过率 100%", "min": 1.0},
    "G5_quality": {"desc": "质量均分 On ≥ 0.80 且 > Off", "min": 0.80},
    "G6_no_regression": {"desc": "On 在 ≥ 2/3 可比任务上不劣于 Off（-10pp 容差）", "min_ratio": 2 / 3},
}
OBSERVATIONAL = ["G-X1 执行成功率(E2E/API 真实执行)", "G-X2 成对胜率(pairwise)",
                 "G-X3 生成方差(SD)", "G-X4 Efficiency(用例数/重复率/tokens)"]


# ---------------------------------------------------------------- 基础设施
def sh(cmd, timeout=None, cwd=None, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env)


def load_task(task_dir: Path):
    ann = json.loads((task_dir / "annotation.json").read_text())
    task_md = (task_dir / "task.md").read_text()
    return ann, task_md


def call_model(prompt, instructions=None, model=None, timeout=900, max_tokens=MAX_OUTPUT_TOKENS,
               schema_path=None, temperature=None, thinking=None, retries=2):
    """模型路由：`oc:NAME` 走 opencode Zen（OpenAI 兼容），其余走 arkcli +chat。"""
    model = model or GEN_MODEL
    if model.startswith("oc:"):
        return _call_opencode(prompt, instructions, model[3:], timeout, max_tokens,
                              schema_path, temperature, retries)
    cmd = ["arkcli", "+chat", prompt, "--model", model, "--no-progress",
           "--max-output-tokens", str(max_tokens)]
    if instructions:
        cmd += ["--instructions", instructions]
    if schema_path:
        cmd += ["--text-format", "json_schema", "--text-schema", schema_path, "--text-strict"]
    if temperature:
        cmd += ["--temperature", temperature]
    if thinking:
        cmd += ["--thinking", thinking]
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = sh(cmd, timeout=timeout)
            if r.returncode != 0:
                last_err = f"exit={r.returncode} stderr={r.stderr[:300]}"
            else:
                data = json.loads(r.stdout)
                content = data.get("content") or ""
                if content.strip():
                    return {"ok": True, "content": content, "usage": data.get("usage", {}),
                            "resp_id": data.get("id", "")}
                last_err = "empty content"
        except Exception as e:  # noqa: BLE001
            last_err = repr(e)[:300]
        time.sleep(5 * (attempt + 1))
    return {"ok": False, "error": last_err}


def _call_opencode(prompt, instructions, model, timeout, max_tokens, schema_path, temperature, retries):
    key = os.environ.get("OPENCODE_GO_KEY", "")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    messages = []
    if instructions:
        messages.append({"role": "system", "content": instructions})
    user_prompt = prompt
    if schema_path:  # OpenAI 兼容层不保证 response_format 支持，schema 进 prompt + 宽松解析
        schema = Path(schema_path).read_text()
        user_prompt += ("\n\n【输出要求】只输出一个符合以下 JSON Schema 的 JSON 对象，"
                        "不要输出 JSON 之外的任何内容（包括 markdown 围栏）：\n" + schema)
    messages.append({"role": "user", "content": user_prompt})
    body = {"model": model, "messages": messages, "max_tokens": max_tokens}
    # opencode 上游对部分模型仅允许 temperature=1，统一不传（方差靠多采样表决吸收）
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = _requests.post(f"{OPENCODE_BASE}/chat/completions", headers=headers,
                               json=body, timeout=timeout)
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}: {r.text[:300]}"
                if r.status_code == 429:  # 限流：等窗口，退避加长
                    time.sleep(120 * (attempt + 1))
                    continue
            else:
                data = r.json()
                content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
                if content.strip():
                    u = data.get("usage", {})
                    return {"ok": True, "content": content,
                            "usage": {"prompt_tokens": u.get("prompt_tokens"),
                                      "completion_tokens": u.get("completion_tokens"),
                                      "total_tokens": u.get("total_tokens")},
                            "resp_id": data.get("id", "")}
                last_err = f"empty content (usage={data.get('usage')})"
        except Exception as e:  # noqa: BLE001
            last_err = repr(e)[:300]
        time.sleep(5 * (attempt + 1))
    return {"ok": False, "error": last_err}


def build_on_instructions(skill_files):
    parts = ["你将执行一套 Agent Skill 定义的工作流。以下是该 skill 的指令文件，"
             "请严格遵循其中的工作流步骤与全部硬约束（被引用的检查清单视为必须逐项执行）完成任务。"]
    for f in skill_files:
        p = REPO / f
        if not p.exists():
            raise FileNotFoundError(f)
        parts.append(f"\n===== 文件: {f} =====\n\n{p.read_text()}")
    return "\n".join(parts)


# ---------------------------------------------------------------- 标注独立审计
AUDIT_SCHEMA = REPO / "eval/harness/audit_schema.json"

AUDIT_PROMPT = """你是独立的测试评估标注审计员。你没有参与以下任务材料与标注的编写。
请逐条审计「可测点清单」与「检出项清单」：

1. scope：该点是否属于本任务被测功能的合理测试范围（任务目标见材料）？范围外的标 remove 并给理由
2. ambiguity：该点表述是否无歧义、可客观判定覆盖与否？有歧义标 revise 并给出更清晰表述
3. 过严/过宽：判定标准是否对一个合格产出不公平（例如要求了材料未定义的行为）？
4. missing：材料中重要且可测、但清单遗漏的点（最多补 5 条，每条给依据）

只输出 JSON。kept 表示无异议。"""


def phase_audit(run_dir: Path):
    audit_dir = run_dir / "annotation_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    task_names = sorted(d.name for d in GOLDEN.iterdir() if d.is_dir())
    stats_all = {}
    for t in task_names:
        out_f = audit_dir / f"{t}.json"
        if out_f.exists():
            data = json.loads(out_f.read_text())
            if data.get("ok"):
                stats_all[t] = data["summary"]
                continue
        ann, task_md = load_task(GOLDEN / t)
        items = []
        for k in ("testable_points", *DETECTION_KEYS):
            for p in ann.get(k, []):
                items.append({"id": p["id"], "kind": k, "point": p.get("point") or p.get("case") or p.get("desc", "")})
        payload = {"task_material": task_md[:20000], "items": items}
        prompt = AUDIT_PROMPT + "\n\n```json\n" + json.dumps(payload, ensure_ascii=False, indent=1) + "\n```"
        res = call_model(prompt, model=AUDIT_MODEL, timeout=JUDGE_TIMEOUT, max_tokens=16384,
                         schema_path=str(AUDIT_SCHEMA), temperature="0.2", thinking="disabled")
        data = normalize_audit(res.get("content", "")) if res["ok"] else None
        if data is None or not data.get("audit_results"):
            out_f.write_text(json.dumps({"ok": False, "error": res.get("error")}, ensure_ascii=False))
            print(f"  audit {t} FAIL: {res.get('error')}")
            continue
        verdicts = [v for v in data.get("audit_results", []) if v.get("verdict")]
        unparsed = len(items) - len(verdicts)
        n_kept = sum(1 for v in verdicts if v.get("verdict") == "kept")
        summary = {"n_items": len(items), "n_kept": n_kept, "n_unparsed": unparsed,
                   "agreement": round(n_kept / len(items), 4) if items and not unparsed else
                   (round(n_kept / len(verdicts), 4) if verdicts else None),
                   "flagged": [(v["id"], v.get("verdict"), v.get("reason", "")) for v in verdicts
                               if v.get("verdict") != "kept"],
                   "missing": data.get("missing_points", [])}
        out_f.write_text(json.dumps({"ok": True, "summary": summary}, ensure_ascii=False, indent=2))
        stats_all[t] = summary
        print(f"  audit {t}: {summary['n_kept']}/{summary['n_items']} kept, "
              f"{len(summary['flagged'])} flagged, {len(summary['missing'])} missing")
    agree = [s["agreement"] for s in stats_all.values() if s["agreement"] is not None]
    (run_dir / "annotation_audit_summary.json").write_text(json.dumps(stats_all, ensure_ascii=False, indent=2))
    if agree:
        print(f"[audit] 总体标注一致率: {statistics.mean(agree):.3f}（人工复核 flagged 项后写入 annotation.json 的 audit 字段）")
    else:
        print("[audit] 无成功审计（限流/网络），稍后重跑同命令可续")


def normalize_json(content):
    text = (content or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except Exception:  # noqa: BLE001
        return None
    return data if isinstance(data, dict) else None


VERDICT_ALIAS = {"kept": "kept", "keep": "kept", "保留": "kept", "无异议": "kept",
                 "revise": "revise", "修改": "revise", "需修改": "revise", "歧义": "revise",
                 "remove": "remove", "删除": "remove", "范围外": "remove", "移除": "remove"}


def normalize_audit(content):
    data = normalize_json(content)
    if data is None:
        return None
    results = []
    for k in ("audit_results", "audit_result", "audit", "results", "audits", "items"):
        v = data.get(k)
        if isinstance(v, list):
            for it in v:
                if not isinstance(it, dict):
                    continue
                raw = it.get("verdict") or it.get("decision") or it.get("result") or it.get("action")
                verdict = VERDICT_ALIAS.get(str(raw).strip().lower().rstrip(".")) if raw else None
                results.append({"id": it.get("id"), "verdict": verdict,
                                "reason": str(it.get("reason") or it.get("comment") or it.get("suggestion") or "")[:200]})
            break
    if not results:  # 紧凑映射形态：{"F1": "kept", "P2": "revise", ..., "missing": []}
        for k, v in data.items():
            if k in ("missing", "missing_points", "notes") or not isinstance(v, (str, dict)):
                continue
            raw = v.get("verdict") if isinstance(v, dict) else v
            reason = v.get("reason", "") if isinstance(v, dict) else ""
            verdict = VERDICT_ALIAS.get(str(raw).strip().lower().rstrip("."))
            if verdict:
                results.append({"id": k, "verdict": verdict, "reason": str(reason)[:200]})
    missing = next((data[k] for k in ("missing_points", "missing")
                    if isinstance(data.get(k), list)), [])
    return {"audit_results": results, "missing_points": missing}


# ---------------------------------------------------------------- 生成（多样本）
def model_tag(model):
    """非主生成模型的产物文件带标签（多模型泛化分组用）。"""
    return "" if model == GEN_MODEL else "__" + re.sub(r"[^\w.-]", "-", model)


def gen_one(task_name, mode, sample, run_dir, model):
    ann, task_md = load_task(GOLDEN / task_name)
    tag = model_tag(model)
    base = run_dir / "outputs" / f"{task_name}__{mode}__s{sample}{tag}"
    out_file, meta_file = Path(str(base) + ".md"), Path(str(base) + ".meta.json")
    if out_file.exists() and json.loads(meta_file.read_text()).get("ok"):
        return task_name, mode, sample, "cached"
    instr = build_on_instructions(ann["skill_files_on"]) if mode == "on" else PERSONA_OFF
    res = call_model(EVAL_PREAMBLE + task_md, instructions=instr, model=model,
                     timeout=GENERATE_TIMEOUT, max_tokens=MAX_OUTPUT_TOKENS)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    meta = {"task": task_name, "mode": mode, "sample": sample, "ok": res["ok"],
            "error": res.get("error"), "usage": res.get("usage", {}), "model": model,
            "ts": datetime.now().isoformat(timespec="seconds")}
    if res["ok"]:
        out_file.write_text(res["content"])
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    return task_name, mode, sample, ("ok" if res["ok"] else f"FAIL: {res.get('error')}")


def phase_generate(run_dir, only_tasks=None, modes=("on", "off"), samples=3, model=None):
    model = model or GEN_MODEL
    tasks = sorted(d.name for d in GOLDEN.iterdir() if d.is_dir())
    if only_tasks:
        tasks = [t for t in tasks if any(p in t for p in only_tasks)]
    jobs = [(t, m, s) for t in tasks for m in modes for s in range(samples)]
    print(f"[generate] {len(jobs)} runs (samples={samples}), model={model}, workers={WORKERS}")
    fails = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(gen_one, t, m, s, run_dir, model): (t, m, s) for t, m, s in jobs}
        for fut in concurrent.futures.as_completed(futs):
            _, _, _, status = fut.result()
            if status.startswith("FAIL"):
                fails += 1
                print(f"  {futs[fut]} -> {status}")
    print(f"[generate] done, {fails} failures（重跑同命令可续跑）")
    return fails == 0


# ---------------------------------------------------------------- 客观检查（可执行性 / 编译）
CASE_START = re.compile(r"^\s*-\s+\*{0,2}TC-\d+-\d+", re.M)
PLACEHOLDER = re.compile(r"\{[A-Za-z_\u4e00-\u9fff][^{}\n]{0,30}\}")
FUZZ_WORDS = re.compile(r"某某|xxx|XXX")
CODE_LOC = re.compile(r"[A-Za-z0-9_]+\.(py|go|ts|tsx|js|java|sql|rb|rs):\d+")
VAGUE = re.compile(r"功能正常|正常显示|运行正常|系统正常|工作正常")
TIME_UNITS = re.compile(r"\d+\s*(秒|分钟|小时|天)|秒内|分钟内|小时内|天内")


def split_cases(body):
    starts = [m.start() for m in CASE_START.finditer(body)]
    cases = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(body)
        cases.append(body[s:e])
    return cases


def case_violations(case):
    v = []
    if PLACEHOLDER.search(case) or FUZZ_WORDS.search(case):
        v.append("placeholder")
    for line in case.splitlines():
        if "预期" in line and VAGUE.search(line) and len(line.strip()) < 30:
            v.append("vague")
            break
    if CODE_LOC.search(case):
        v.append("code_leak")
    if any(("自动" in l or "异步" in l or "稍后" in l) and "预期" in l and not TIME_UNITS.search(l)
           for l in case.splitlines()):
        v.append("no_time_limit")
    if re.search(r"全局唯一|绝对唯一", case) and "查库" not in case and "协作" not in case:
        v.append("overclaim")
    return v


def check_executability(text):
    body = text
    cases = split_cases(body)
    titles = [re.search(r"TC-\d+-\d+\s*(.+?)(?:\*\*)?\[", c) for c in cases]
    titles = [m.group(1).strip() if m else "" for m in titles]
    dup = len(titles) - len(set(t for t in titles if t)) if titles else 0
    dirty = sum(1 for c in cases if case_violations(c))
    guide = {
        "intro_role": bool(re.search(r"功能简介|角色[:：]|角色表", text)),
        "env_account": bool(re.search(r"环境与账号|测试账号|后台入口", text)),
        "glossary": bool(re.search(r"术语表", text)),
        "legend": bool(re.search(r"图例", text)),
    }
    guide_score = sum(guide.values()) / 4
    clean_ratio = (len(cases) - dirty) / len(cases) if cases else 1.0
    exec_score = round(0.5 * clean_ratio + 0.5 * guide_score, 4) if cases else None
    return {"n_cases": len(cases), "n_dirty": dirty, "clean_ratio": round(clean_ratio, 4),
            "guide_score": round(guide_score, 4), "exec_score": exec_score,
            "veto": bool(cases and clean_ratio < 0.5),
            "dup_titles": dup, "dup_rate": round(dup / len(cases), 4) if cases else 0.0}


CODE_BLOCK = re.compile(r"^```(\w*)\s*$", re.M)
FILE_HINT = re.compile(r"([\w./-]+\.(?:py|ts|tsx|js))")


def extract_code_blocks(text, lang):
    blocks = []
    lines = text.splitlines()
    pending_file = None
    i = 0
    while i < len(lines):
        m = re.match(r"^```(\w*)\s*$", lines[i])
        if m and m.group(1) == lang:
            j, buf = i + 1, []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j])
                j += 1
            code = "\n".join(buf)
            first = code.splitlines()[0] if code.splitlines() else ""
            inner = FILE_HINT.search(first)
            blocks.append({"file": pending_file or (inner.group(1) if inner else None), "code": code})
            i = j + 1
            pending_file = None
        else:
            hint = FILE_HINT.search(lines[i])
            if hint and len(lines[i]) < 120:
                pending_file = hint.group(1)
            i += 1
    return blocks


def check_python_compile(text):
    blocks = extract_code_blocks(text, "python")
    if not blocks:
        return {"compile_pass": False, "n_blocks": 0, "errors": ["no python code blocks"]}
    errors = []
    for b in blocks:
        try:
            compile(b["code"], b["file"] or "<block>", "exec")
        except SyntaxError as e:
            errors.append(f"{b['file']}: {e}")
    return {"compile_pass": not errors, "n_blocks": len(blocks), "errors": errors,
            "env_injected": ("os.environ" in text or "getenv" in text),
            "assert_depth": bool(re.search(r"\.json\(\)", text))}


SCAFFOLD = REPO / "eval/harness" / "fixtures" / "playwright_scaffold"
EXEC_LOCK = threading.Lock()
E2E_PORT = int(os.environ.get("EVAL_E2E_PORT", "8931"))
API_PORT = int(os.environ.get("EVAL_API_PORT", "8932"))


def write_ts_project(text):
    """把输出中的 ts 代码块写入临时工程；返回 (proj_dir, spec_text)。"""
    blocks = extract_code_blocks(text, "typescript") or extract_code_blocks(text, "ts")
    if not blocks:
        return None, ""
    td = Path(tempfile.mkdtemp(prefix="e2e_exec_"))
    shutil.copytree(SCAFFOLD, td / "proj", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("node_modules", "mock_app"))
    proj = td / "proj"
    (proj / "node_modules").symlink_to(SCAFFOLD / "node_modules")
    spec_text = ""
    written = []
    for b in blocks:
        name = (b["file"] or f"gen_{abs(hash(b['code'])) % 9999}.spec.ts").lstrip("/")
        if "tests/" in name:
            name = name[name.index("tests/"):]
        target = proj / name if name.startswith("tests/") else proj / "tests" / Path(name).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(b["code"])
        written.append(target)
        if ".spec." in name:
            spec_text += b["code"] + "\n"
    for imp in set(re.findall(r"from\s+'(\./pages/[\w.-]+)'", spec_text)):
        base = imp.replace("./", "")
        for cand in (base + ".ts", base + ".tsx", base):
            wanted = proj / "tests" / cand
            if wanted.exists():
                break
        else:
            for t in written:
                if t.name in (Path(base).name + ".ts", Path(base).name + ".tsx"):
                    dst = proj / "tests" / (base + t.suffix)
                    if not dst.exists():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        dst.write_text(t.read_text())
                        t.unlink()
                    break
    return proj, spec_text


def check_ts_compile(text):
    proj, spec_text = write_ts_project(text)
    if proj is None:
        return {"compile_pass": False, "n_blocks": 0, "errors": ["no ts code blocks"]}
    try:
        if not (SCAFFOLD / "node_modules").exists():
            return {"compile_pass": None, "errors": ["scaffold not installed — run setup-e2e"]}
        r = sh(["./node_modules/.bin/tsc", "--noEmit", "-p", "tsconfig.json"], timeout=180, cwd=proj)
        errors = [l for l in r.stdout.splitlines() if "error TS" in l][:10]
        spec_checks = {
            "tc_naming": bool(re.search(r"test\(\s*['\"`][^'\"`]*TC-\d+-\d+", spec_text)),
            "no_fixed_wait": "waitForTimeout" not in spec_text,
            "po_usage": len(re.findall(r"page\.(locator|getByRole|getByTestId)\(", spec_text)) <= 2,
            "assert_persist": bool(re.search(r"reload|refresh", spec_text, re.I)),
            "assert_present": spec_text.count("expect(") >= 3,
        }
        return {"compile_pass": r.returncode == 0, "errors": errors, "spec_checks": spec_checks}
    finally:
        shutil.rmtree(proj.parent, ignore_errors=True)


def exec_e2e(text, runs=2):
    """真实执行：起 mock 应用 + chromium 跑生成的 spec，返回通过率与重跑稳定性。"""
    proj, spec_text = write_ts_project(text)
    if proj is None:
        return {"exec_ok": False, "detail": "no ts code blocks"}
    server = None
    try:
        if not (SCAFFOLD / "node_modules" / ".browser-installed").exists():
            return {"exec_ok": False, "detail": "chromium not installed — run setup-e2e"}
        with EXEC_LOCK:
            server = subprocess.Popen(["node", "mock_app/server.js"], cwd=SCAFFOLD,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      env={**os.environ, "E2E_PORT": str(E2E_PORT)})
            time.sleep(1.2)
            results = []
            for _ in range(runs):
                r = sh(["./node_modules/.bin/playwright", "test", "--reporter=json"],
                       timeout=300, cwd=proj,
                       env={**os.environ, "TEST_BASE_URL": f"http://127.0.0.1:{E2E_PORT}",
                            "ADMIN_USER": "admin", "ADMIN_PASS": "pass"})
                m = re.search(r'\{.*\}', r.stdout, re.S)
                passed = failed = 0
                if m:
                    try:
                        rep = json.loads(m.group(0))
                        s = rep.get("stats", {})
                        # playwright JSON: expected=通过 unexpected=失败 flaky=最终通过
                        passed = int(s.get("expected", 0)) + int(s.get("flaky", 0))
                        failed = int(s.get("unexpected", 0))
                    except Exception:  # noqa: BLE001
                        pass
                if passed + failed == 0 and r.returncode != 0:
                    failed = 1
                results.append({"passed": passed, "failed": failed,
                                "total": passed + failed})
            total = sum(s["total"] for s in results)
            passed = sum(s["passed"] for s in results)
            stable = len({(s["passed"], s["failed"]) for s in results}) == 1
            return {"exec_ok": True, "pass_rate": round(passed / total, 4) if total else 0.0,
                    "n_tests_total": total, "stable_across_runs": stable,
                    "runs": results,
                    "raw_fail_tail": r.stdout[-400:] if total and passed < total else ""}
    finally:
        if server:
            server.terminate()
            try:
                server.wait(timeout=5)
            except Exception:  # noqa: BLE001
                server.kill()
        shutil.rmtree(proj.parent, ignore_errors=True)


def exec_api(text, runs=1):
    """真实执行：起 mock API 服务跑生成的 pytest。"""
    proj_dir = Path(tempfile.mkdtemp(prefix="api_exec_"))
    server = None
    try:
        blocks = extract_code_blocks(text, "python")
        if not blocks:
            return {"exec_ok": False, "detail": "no python code blocks"}
        for b in blocks:
            name = (b["file"] or f"test_gen_{abs(hash(b['code'])) % 9999}.py").lstrip("/").lstrip("./")
            # 归一化工程前缀并保留包目录结构（common/ 等子包依赖相对布局）
            for prefix in ("api-tests/", "api_tests/", "tests/"):
                if name.startswith(prefix):
                    name = name[len(prefix):]
                    break
            target = proj_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(b["code"])
        pytest_ini = proj_dir / "pytest.ini"
        pytest_ini.write_text("[pytest]\nasyncio_mode = auto\n")
        with EXEC_LOCK:
            server = subprocess.Popen([sys.executable, str(REPO / "eval/harness/fixtures/mock_api/server.py")],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      env={**os.environ, "API_PORT": str(API_PORT)})
            time.sleep(1.0)
            r = sh([sys.executable, "-m", "pytest", "-q", "--junitxml=junit.xml", "-p", "no:cacheprovider"],
                   timeout=600, cwd=proj_dir,
                   env={**os.environ, "API_BASE_URL": f"http://127.0.0.1:{API_PORT}",
                        "API_USER": "admin", "API_PASSWORD": "pass",
                        "PYTHONPATH": str(proj_dir)})
            junit = proj_dir / "junit.xml"
            total = failed = 0
            if junit.exists():
                x = junit.read_text()
                m_total = re.search(r'tests="(\d+)"', x)
                m_fail = re.search(r'failures="(\d+)"', x)
                m_err = re.search(r'errors="(\d+)"', x)
                if m_total:
                    total = int(m_total.group(1))
                    failed = int(m_fail.group(1) if m_fail else 0) + int(m_err.group(1) if m_err else 0)
            passed = total - failed
            return {"exec_ok": True, "pass_rate": round(passed / total, 4) if total else 0.0,
                    "n_tests": total, "n_failed": failed,
                    "raw_tail": (r.stdout or r.stderr)[-500:] if failed else ""}
    finally:
        if server:
            server.terminate()
            try:
                server.wait(timeout=5)
            except Exception:  # noqa: BLE001
                server.kill()
        shutil.rmtree(proj_dir, ignore_errors=True)


def objective_checks(task_id, text):
    fam = task_id.split("-")[0]
    out = {}
    if fam == "tcw" or task_id.startswith("rev-"):
        out["executability"] = check_executability(text)
    if fam == "api":
        out.update(check_python_compile(text))
    if fam == "e2e":
        out.update(check_ts_compile(text))
    return out


# ---------------------------------------------------------------- judge（逐采样 3 表决）
JUDGE_SCHEMA_PATH = REPO / "eval/harness/judge_schema.json"

JUDGE_PROMPT = """你是严格的测试产物评审官。对照给定的黄金标准，评审一份测试产出。

## 评审规则
1. 逐条核对「可测点清单」：产出中存在一条用例/内容实质覆盖该点即 covered=true（同一条用例可覆盖多个点；仅在提及概念而无验证动作时算 false）。evidence 填产出中的 TC 编号或原文短语（≤40 字）。
2. 逐条核对「检出项清单」：产出中实质发现/完成了该项即 detected=true（evidence 填产出原文短语，≤40 字）。要求的是实质命中，不是关键词碰巧出现。缺陷/风险记录常以**表格行**呈现（如 `| C2 | 现象 | 证据 |`），表格行同样算检出，逐行读。带 bucket 字段的项（回归清单类）：detected=true 要求该项出现在对应分桶——must=必须回归区、should=建议回归区、suggest_new=产出中有对应的新增用例建议、excluded=产出将其显式排除（排除清单）。
3. quality 三项各 0–5 分：
   - correctness：预期结果/结论与黄金标准规则一致，无错误断言或错误结论
   - specificity：数据/入口/判定具体（占位符、模糊判定扣分）
   - actionability：零上下文执行者能否直接按产出开工
4. notes 一句话总结最大缺陷。只输出 JSON。"""

POINT_KEYS = ("point_results", "points", "points_review", "coverage", "points_evaluation")
DETECT_KEYS = ("detection_results", "detections", "detections_review", "violations")


def normalize_judge_json(content):
    data = normalize_json(content)
    if data is None:
        return None
    pts = dts = None
    for k in (*POINT_KEYS, *DETECT_KEYS):
        v = data.get(k)
        if isinstance(v, list) and v and isinstance(v[0], dict):
            if pts is None and all("covered" in i for i in v):
                pts = v
            elif dts is None and all("detected" in i for i in v):
                dts = v
    for k, v in data.items():
        if not (isinstance(v, list) and v and isinstance(v[0], dict)):
            continue
        if pts is None and all("covered" in i for i in v):
            pts = v
        elif dts is None and all("detected" in i for i in v):
            dts = v
    return {"point_results": pts or [], "detection_results": dts or [],
            "quality": data.get("quality") or {}, "notes": data.get("notes", "")}


def merge_judge_samples(samples):
    pts, dts = {}, {}
    for s in samples:
        for p in s.get("point_results", []):
            pts.setdefault(p.get("id"), []).append(bool(p.get("covered")))
        for d in s.get("detection_results", []):
            dts.setdefault(d.get("id"), []).append(bool(d.get("detected")))
    majority = lambda xs: (sum(xs) * 2 > len(xs)) if xs else False  # noqa: E731
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else 0          # noqa: E731
    quality = {}
    for k in ("correctness", "specificity", "actionability"):
        vals = [s.get("quality", {}).get(k) for s in samples
                if isinstance(s.get("quality", {}).get(k), (int, float))]
        quality[k] = med(vals) if vals else 0
    return {"point_results": [{"id": i, "covered": majority(v)} for i, v in pts.items()],
            "detection_results": [{"id": i, "detected": majority(v)} for i, v in dts.items()],
            "quality": quality, "notes": samples[0].get("notes", "") if samples else ""}


def judge_sample(task_name, mode, sample, run_dir, tag=""):
    ann, _ = load_task(GOLDEN / task_name)
    out_file = run_dir / "outputs" / f"{task_name}__{mode}__s{sample}{tag}.md"
    jf = run_dir / "judge" / f"{task_name}__{mode}__s{sample}{tag}.json"
    if not out_file.exists():
        return (task_name, mode, sample, "missing-output")
    if jf.exists() and json.loads(jf.read_text()).get("ok"):
        return (task_name, mode, sample, "cached")
    gt_points = ann.get("testable_points", [])
    detections = [item for k in DETECTION_KEYS for item in ann.get(k, [])]
    payload = {
        "task": ann.get("description", task_name),
        "expected_output": ann.get("expected_output", ""),
        "points": [{"id": p["id"], "point": p["point"]} for p in gt_points],
        "detections": [{"id": d["id"],
                        "point": d.get("point") or d.get("case") or d.get("desc", ""),
                        **({"bucket": d["bucket"]} if "bucket" in d else {})} for d in detections],
        "agent_output": out_file.read_text()[:60000],
    }
    prompt = JUDGE_PROMPT + "\n\n## 黄金标准与待评审产出（JSON）\n```json\n" + \
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n```"
    samples = []
    for _ in range(JUDGE_SAMPLES):
        r = call_model(prompt, model=JUDGE_MODEL, timeout=JUDGE_TIMEOUT, max_tokens=16384,
                       schema_path=str(JUDGE_SCHEMA_PATH), temperature="0.2", thinking="disabled")
        if r["ok"]:
            d = normalize_judge_json(r["content"])
            if d:
                samples.append(d)
    jf.parent.mkdir(parents=True, exist_ok=True)
    if not samples:
        jf.write_text(json.dumps({"ok": False, "error": "all judge samples failed"}, ensure_ascii=False))
        return (task_name, mode, sample, "FAIL: judge")
    merged = merge_judge_samples(samples)
    merged.update({"ok": True, "n_samples": len(samples)})
    jf.write_text(json.dumps(merged, ensure_ascii=False, indent=2))
    return (task_name, mode, sample, "ok")


# ---------------------------------------------------------------- 成对评审（pairwise + 位置互换）
PAIR_SCHEMA = REPO / "eval/harness/pairwise_schema.json"

PAIR_PROMPT = """你是严格的测试产物评审官。同一任务的两份测试产出（产物A、产物B）,
从「测试工程师拿到后能否直接开工执行」的专业标准评审，选出整体更好的一份：

评判维度（按重要性）：正确性（预期与规则一致）> 可执行性（具体数据/入口/判定，无占位符模糊）> 覆盖完整性 > 组织与可读性。
- 忽略排版风格与长度本身的影响（长不等于好，但覆盖更全算更好）
- 只看内容实质。若两者质量确实接近到无法区分，选 tie
只输出 JSON。"""


def judge_pair(task_name, sample, run_dir):
    a_file = run_dir / "outputs" / f"{task_name}__on__s{sample}.md"
    b_file = run_dir / "outputs" / f"{task_name}__off__s{sample}.md"
    jf = run_dir / "pairwise" / f"{task_name}__s{sample}.json"
    if not (a_file.exists() and b_file.exists()):
        return (task_name, sample, "missing")
    if jf.exists() and json.loads(jf.read_text()).get("ok"):
        return (task_name, sample, "cached")
    ann, _ = load_task(GOLDEN / task_name)
    on_txt, off_txt = a_file.read_text()[:45000], b_file.read_text()[:45000]

    def one_round(first_name, first_txt, second_name, second_txt):
        payload = {"task": ann.get("description", task_name),
                   "output_A": first_txt if first_name == "A" else second_txt,
                   "output_B": second_txt if first_name == "A" else first_txt,
                   "note": "output_A 与 output_B 的命名仅为本轮标记，与任何生成方式无关"}
        prompt = PAIR_PROMPT + "\n```json\n" + json.dumps(payload, ensure_ascii=False, indent=1) + "\n```"
        r = call_model(prompt, model=PAIR_JUDGE_MODEL, timeout=JUDGE_TIMEOUT, max_tokens=8192,
                       schema_path=str(PAIR_SCHEMA), temperature="0.2", thinking="disabled")
        if not r["ok"]:
            return None
        d = normalize_json(r["content"])
        if not d:
            return None
        raw = str(d.get("winner", ""))
        if re.search(r"tie|draw|平局|无法区分|相当", raw, re.I):
            w = "tie"
        elif "A" in raw:
            w = "A"
        elif "B" in raw:
            w = "B"
        else:
            return None
        return {"winner": w, "reason": str(d.get("reason") or d.get("justification") or "")[:300]}

    # 第一轮：On 放 A；第二轮：On 放 B（位置互换，消位置偏差）
    r1 = one_round("A", on_txt, "B", off_txt)
    r2 = one_round("B", off_txt, "A", on_txt)
    jf.parent.mkdir(parents=True, exist_ok=True)
    if not (r1 and r2):
        jf.write_text(json.dumps({"ok": False, "error": "pairwise calls failed"}, ensure_ascii=False))
        return (task_name, sample, "FAIL")
    w1 = "on" if r1["winner"] == "A" else ("off" if r1["winner"] == "B" else "tie")
    w2 = "on" if r2["winner"] == "B" else ("off" if r2["winner"] == "A" else "tie")
    consistent = w1 if w1 == w2 else "tie"
    jf.write_text(json.dumps({"ok": True, "round1": r1, "round2": w2, "result": consistent,
                              "position_consistent": w1 == w2}, ensure_ascii=False, indent=2))
    return (task_name, sample, consistent)


# ---------------------------------------------------------------- 统计
def paired_bootstrap_ci(diffs, n=BOOTSTRAP_N, seed=42, alpha=0.05):
    """任务层配对 bootstrap：对差值列表重采样，返回 (mean, lo, hi)。"""
    if not diffs:
        return None, None, None
    rng = random.Random(seed)
    k = len(diffs)
    means = []
    for _ in range(n):
        sample = [diffs[rng.randrange(k)] for _ in range(k)]
        means.append(sum(sample) / k)
    means.sort()
    lo = means[int(alpha / 2 * n)]
    hi = means[int((1 - alpha / 2) * n) - 1]
    return sum(diffs) / k, lo, hi


def wilson_ci(wins, n, z=1.96):
    if n == 0:
        return None, None, None
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, center - half, center + half


# ---------------------------------------------------------------- 评分聚合
def fmt_pct(v):
    return "—" if v is None else f"{round(v * 100, 1)}%"


def discover_tags(run_dir):
    tags = {""}
    for f in (run_dir / "outputs").glob("*__s[0-9]*.md"):
        m = re.match(r".*__s\d+(__.+)?\.md", f.name)
        if m and m.group(1):
            tags.add(m.group(1))
    return sorted(tags)


def phase_score(run_dir, samples=3):
    task_names = sorted(d.name for d in GOLDEN.iterdir() if d.is_dir())
    tags = discover_tags(run_dir)
    print(f"[score] model tags: {[t or '<primary>' for t in tags]}")
    print("[score] judge 每个采样 ...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = []
        for t in task_names:
            for m in ("on", "off"):
                for s in range(samples):
                    for tag in tags:
                        if (run_dir / "outputs" / f"{t}__{m}__s{s}{tag}.md").exists():
                            futs.append(ex.submit(judge_sample, t, m, s, run_dir, tag))
        for f in concurrent.futures.as_completed(futs):
            r = f.result()
            if "FAIL" in str(r[3]):
                print("  judge", r)
    pair_samples = min(samples, int(os.environ.get("EVAL_PAIR_SAMPLES", "2")))
    print(f"[score] pairwise 成对评审（前 {pair_samples} 个采样, 位置互换）...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(judge_pair, t, s, run_dir) for t in task_names for s in range(pair_samples)]
        for f in concurrent.futures.as_completed(futs):
            r = f.result()
            if r[2] == "FAIL":
                print("  pair", r)

    def build_rows(tag):
        rows = {}
        for t in task_names:
            for m in ("on", "off"):
                per_sample = []
                for s in range(samples):
                    out_f = run_dir / "outputs" / f"{t}__{m}__s{s}{tag}.md"
                    jf = run_dir / "judge" / f"{t}__{m}__s{s}{tag}.json"
                    meta_f = run_dir / "outputs" / f"{t}__{m}__s{s}{tag}.meta.json"
                    entry = {}
                    if out_f.exists():
                        entry["objective"] = objective_checks(t, out_f.read_text())
                    if jf.exists():
                        j = json.loads(jf.read_text())
                        if j.get("ok"):
                            pts = j.get("point_results", [])
                            dts = j.get("detection_results", [])
                            entry["coverage"] = round(sum(1 for p in pts if p.get("covered")) / len(pts), 4) if pts else None
                            entry["detection"] = round(sum(1 for d in dts if d.get("detected")) / len(dts), 4) if dts else None
                            q = j.get("quality", {})
                            entry["quality"] = round(sum(q.get(k, 0) for k in
                                                         ("correctness", "specificity", "actionability")) / 15, 4)
                    if meta_f.exists():
                        entry["tokens"] = json.loads(meta_f.read_text()).get("usage", {})
                    ex_obj = (entry.get("objective") or {}).get("executability")
                    if entry.get("coverage") is not None:
                        if ex_obj and ex_obj.get("veto"):
                            entry["effective_coverage"] = 0.0
                        elif ex_obj and ex_obj.get("exec_score") is not None:
                            entry["effective_coverage"] = round(entry["coverage"] * ex_obj["exec_score"], 4)
                        else:
                            entry["effective_coverage"] = entry["coverage"]
                    per_sample.append(entry)
                rows[f"{t}__{m}"] = per_sample
        return rows

    def task_metric(rows, t, m, key):
        vals = [e.get(key) for e in rows[f"{t}__{m}"]]
        vals = [v for v in vals if v is not None]
        if not vals:
            return None, None
        return statistics.mean(vals), (statistics.stdev(vals) if len(vals) > 1 else 0.0)

    rows = build_rows("")

    # 真实执行（主模型）
    print("[score] 真实执行（E2E 浏览器 / API 服务）...")
    exec_results = {}
    for t in ("e2e-markmap-to-spec", "api-openapi-coupon"):
        for m in ("on", "off"):
            for s in range(samples):
                out_f = run_dir / "outputs" / f"{t}__{m}__s{s}.md"
                ef = run_dir / "exec" / f"{t}__{m}__s{s}.json"
                if not out_f.exists():
                    continue
                if ef.exists():
                    exec_results[f"{t}__{m}__s{s}"] = json.loads(ef.read_text())
                    continue
                r = exec_e2e(out_f.read_text()) if t.startswith("e2e") else exec_api(out_f.read_text())
                ef.parent.mkdir(parents=True, exist_ok=True)
                ef.write_text(json.dumps(r, ensure_ascii=False, indent=2))
                exec_results[f"{t}__{m}__s{s}"] = r
                print(f"  exec {t} {m} s{s}: pass_rate={r.get('pass_rate')}")

    # 成对统计
    pair_stats = {}
    for t in task_names:
        results = []
        for s in range(pair_samples):
            jf = run_dir / "pairwise" / f"{t}__s{s}.json"
            if jf.exists():
                d = json.loads(jf.read_text())
                if d.get("ok"):
                    results.append(d["result"])
        if results:
            pair_stats[t] = {"on": results.count("on"), "off": results.count("off"),
                             "tie": results.count("tie"), "n": len(results)}

    def agg(key, prefix=None):
        diffs, detail = [], {}
        for t in task_names:
            if prefix and not t.startswith(prefix):
                continue
            on_m, _ = task_metric(rows, t, "on", key)
            off_m, _ = task_metric(rows, t, "off", key)
            if on_m is not None and off_m is not None:
                diffs.append(on_m - off_m)
                detail[t] = (round(off_m, 4), round(on_m, 4))
            elif on_m is not None or off_m is not None:
                detail[t] = (round(off_m, 4) if off_m is not None else None,
                             round(on_m, 4) if on_m is not None else None)
        if diffs:
            mean, lo, hi = paired_bootstrap_ci(diffs)
            return {"mean_diff": round(mean, 4), "ci95": [round(lo, 4), round(hi, 4)],
                    "n_tasks": len(diffs), "detail": detail,
                    "on_avg": round(statistics.mean([v[1] for v in detail.values() if v[1] is not None]), 4),
                    "off_avg": round(statistics.mean([v[0] for v in detail.values() if v[0] is not None]), 4)}
        return {"detail": detail}

    stats = {
        "effective_coverage_tcw": agg("effective_coverage", "tcw-"),
        "effective_coverage_all": agg("effective_coverage"),
        "quality": agg("quality"),
        "detection": agg("detection"),
    }
    pair_total = {"on": sum(v["on"] for v in pair_stats.values()),
                  "off": sum(v["off"] for v in pair_stats.values()),
                  "tie": sum(v["tie"] for v in pair_stats.values()),
                  "n": sum(v["n"] for v in pair_stats.values())}
    if pair_total["n"]:
        score_on = pair_total["on"] + 0.5 * pair_total["tie"]
        stats["pairwise"] = {"win_rate_on": round(score_on / pair_total["n"], 4),
                             "wilson95": [round(x, 4) for x in wilson_ci(score_on, pair_total["n"])],
                             **pair_total}
    ex_vals_on, ex_vals_off = [], []
    for t in task_names:
        if not t.startswith(TCW_PREFIXES):
            continue
        for m, arr in (("on", ex_vals_on), ("off", ex_vals_off)):
            vals = [e.get("objective", {}).get("executability", {}).get("exec_score")
                    for e in rows[f"{t}__{m}"]]
            vals = [v for v in vals if v is not None]
            if vals:
                arr.append(statistics.mean(vals))
    stats["executability_on"] = round(statistics.mean(ex_vals_on), 4) if ex_vals_on else None
    stats["executability_off"] = round(statistics.mean(ex_vals_off), 4) if ex_vals_off else None
    stats["bug_detection_on"] = task_metric(rows, "tcw-user-delete-code", "on", "detection")[0]
    compile_results = {}
    for t in ("api-openapi-coupon", "e2e-markmap-to-spec"):
        vals = [1.0 if (e.get("objective") or {}).get("compile_pass") is True else 0.0
                for e in rows[f"{t}__on"]]
        compile_results[t] = round(statistics.mean(vals), 4) if vals else None
    stats["compile_on"] = compile_results
    exec_agg = {}
    for t in ("e2e-markmap-to-spec", "api-openapi-coupon"):
        for m in ("on", "off"):
            rates = [v.get("pass_rate") for k, v in exec_results.items()
                     if k.startswith(f"{t}__{m}__s") and v.get("pass_rate") is not None]
            exec_agg[f"{t}__{m}"] = round(statistics.mean(rates), 4) if rates else None
    stats["execution_success"] = exec_agg
    eff = {}
    for m in ("on", "off"):
        cases, dups, toks = [], [], []
        for t in task_names:
            for e in rows[f"{t}__{m}"]:
                ex = (e.get("objective") or {}).get("executability")
                if ex and ex.get("n_cases"):
                    cases.append(ex["n_cases"])
                    dups.append(ex.get("dup_rate", 0))
                u = e.get("tokens", {})
                if u.get("total_tokens"):
                    toks.append(u["total_tokens"])
        eff[m] = {"mean_cases": round(statistics.mean(cases), 1) if cases else None,
                  "dup_rate": round(statistics.mean(dups), 4) if dups else None,
                  "mean_tokens_total": round(statistics.mean(toks)) if toks else None}
    stats["efficiency"] = eff
    sd_by_task = {}
    for t in task_names:
        for m in ("on", "off"):
            _, sd = task_metric(rows, t, m, "effective_coverage")
            if sd is not None:
                sd_by_task[f"{t}__{m}"] = round(sd, 4)
    stats["gen_sd_effective_coverage"] = sd_by_task

    # 泛化模型（次要 tag）方向性统计
    generalization = {}
    for tag in tags:
        if tag == "":
            continue
        rows_g = build_rows(tag)

        def agg_g(key, prefix=None, _rows=rows_g):
            diffs = []
            for t in task_names:
                if prefix and not t.startswith(prefix):
                    continue
                on_m, _ = task_metric(_rows, t, "on", key)
                off_m, _ = task_metric(_rows, t, "off", key)
                if on_m is not None and off_m is not None:
                    diffs.append(on_m - off_m)
            return round(statistics.mean(diffs), 4) if diffs else None

        gen_exec = []
        for t in task_names:
            if not t.startswith(TCW_PREFIXES):
                continue
            vals = [e.get("objective", {}).get("executability", {}).get("exec_score")
                    for e in rows_g[f"{t}__on"]]
            vals = [v for v in vals if v is not None]
            if vals:
                gen_exec.append(statistics.mean(vals))
        generalization[tag] = {
            "tcw_effective_coverage_diff": agg_g("effective_coverage", "tcw-"),
            "quality_diff": agg_g("quality"),
            "executability_on": round(statistics.mean(gen_exec), 4) if gen_exec else None,
        }
    stats["generalization"] = generalization

    gates = evaluate_gates(stats, task_names, rows, task_metric)
    report = build_report(run_dir, task_names, rows, task_metric, stats, gates, pair_stats, samples)
    (run_dir / "metrics.json").write_text(json.dumps(
        {"rows": rows, "stats": stats, "gates": gates, "pair_stats": pair_stats,
         "gen_model": GEN_MODEL, "judge_model": JUDGE_MODEL, "samples": samples,
         "judge_samples": JUDGE_SAMPLES}, ensure_ascii=False, indent=2))
    (run_dir / "report.md").write_text(report)
    (RESULTS / "LATEST.md").write_text(report)
    print(report)
    return all(g["pass"] for g in gates.values())


def evaluate_gates(stats, task_names, rows, task_metric):
    gates = {}
    ec = stats.get("effective_coverage_tcw", {})
    gates["G1_tcw_cov_mean"] = {
        "desc": GATES["G1_tcw_cov_mean"]["desc"],
        "pass": ec.get("mean_diff") is not None and ec["mean_diff"] >= 0.05 and ec["ci95"][0] > 0,
        "detail": f"Δ={fmt_pct(ec.get('mean_diff'))} CI95=[{fmt_pct(ec['ci95'][0]) if ec.get('ci95') else '—'}, "
                  f"{fmt_pct(ec['ci95'][1]) if ec.get('ci95') else '—'}] (n={ec.get('n_tasks')})"}
    d = (ec.get("detail") or {}).get("tcw-order-state")
    if d and d[0] is not None and d[1] is not None:
        diff = d[1] - d[0]
        gates["G1_state_cov"] = {"desc": GATES["G1_state_cov"]["desc"],
                                 "pass": diff >= 0.20,
                                 "detail": f"On={fmt_pct(d[1])} Off={fmt_pct(d[0])} Δ={fmt_pct(diff)}"}
    else:
        gates["G1_state_cov"] = {"desc": GATES["G1_state_cov"]["desc"], "pass": False, "detail": "数据缺失"}
    eo = stats.get("executability_on")
    gates["G2_exec"] = {"desc": GATES["G2_exec"]["desc"],
                        "pass": eo is not None and eo >= 0.85, "detail": f"On 可执行性均值={eo}"}
    bo = stats.get("bug_detection_on")
    gates["G3_bug"] = {"desc": GATES["G3_bug"]["desc"],
                       "pass": bo is not None and bo >= 0.75, "detail": f"On 检出={fmt_pct(bo)}"}
    comp = stats.get("compile_on", {})
    gates["G4_compile"] = {"desc": GATES["G4_compile"]["desc"],
                           "pass": bool(comp) and all(v == 1.0 for v in comp.values()),
                           "detail": str(comp)}
    q = stats.get("quality", {})
    qd = q.get("mean_diff")
    gates["G5_quality"] = {"desc": GATES["G5_quality"]["desc"],
                           "pass": q.get("on_avg") is not None and q["on_avg"] >= 0.80 and
                           (qd is None or qd > 0),
                           "detail": f"On={q.get('on_avg')} Off={q.get('off_avg')} Δ={qd}"}
    wins, total = 0, 0
    for t in task_names:
        pairs = []
        for k in ("effective_coverage", "coverage", "detection"):
            a = task_metric(rows, t, "on", k)[0]
            b = task_metric(rows, t, "off", k)[0]
            if a is not None and b is not None:
                pairs.append((a, b))
        if pairs:
            total += 1
            if any(a >= b - 0.10 for a, b in pairs):
                wins += 1
    gates["G6_no_regression"] = {"desc": GATES["G6_no_regression"]["desc"],
                                 "pass": total > 0 and wins / total >= 2 / 3,
                                 "detail": f"不劣于 {wins}/{total}"}
    gens = stats.get("generalization", {})
    if gens:
        details, ok_all = [], True
        for tag, g in gens.items():
            cov_d = g.get("tcw_effective_coverage_diff")
            q_d = g.get("quality_diff")
            ok = cov_d is not None and cov_d > 0
            ok_all = ok_all and ok
            details.append(f"{tag}: tcw覆盖Δ={fmt_pct(cov_d)} 质量Δ={q_d}")
        gates["G7_generalization"] = {"desc": "泛化：次要生成模型上 tcw 覆盖方向性为正（On > Off）",
                                      "pass": ok_all, "detail": "；".join(details)}
    return gates


def build_report(run_dir, task_names, rows, task_metric, stats, gates, pair_stats, samples):
    lines = [f"# Benchmark 报告（v2 科学评估体系）— {run_dir.name}", "",
             f"- 生成模型：{GEN_MODEL}；评审模型：{JUDGE_MODEL}；每任务×模式 {samples} 采样；"
             f"judge {JUDGE_SAMPLES} 采样多数表决；成对评审含位置互换",
             f"- 统计推断：任务层配对 bootstrap {BOOTSTRAP_N} 次报 95%CI；成对胜率报 Wilson 95%CI",
             f"- 时间：{datetime.now().isoformat(timespec='seconds')}", "",
             "## 逐任务指标（任务均值 ± 生成 SD）", "",
             "| 任务 | 模式 | 有效覆盖(mean±sd) | 检出 | 质量 | 可执行性 | 编译 | 执行通过率 | 成对 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for t in task_names:
        for m in ("on", "off"):
            cov, cov_sd = task_metric(rows, t, m, "effective_coverage")
            det, _ = task_metric(rows, t, m, "detection")
            q, q_sd = task_metric(rows, t, m, "quality")
            exs = [e.get("objective", {}).get("executability", {}).get("exec_score")
                   for e in rows[f"{t}__{m}"]]
            exs = [x for x in exs if x is not None]
            comp = rows[f"{t}__{m}"][0].get("objective", {}).get("compile_pass") if rows[f"{t}__{m}"] else None
            comp_all = [e.get("objective", {}).get("compile_pass") for e in rows[f"{t}__{m}"]]
            comp_str = "—" if all(c is None for c in comp_all) else f"{round(statistics.mean([c is True for c in comp_all]) * 100)}%"
            rates = [v.get("pass_rate") for k, v in stats.get("execution_success", {}).items()
                     if k.startswith(f"{t}__{m}")] if False else None
            pair = pair_stats.get(t, {})
            pair_str = f"{pair.get('on', 0)}胜/{pair.get('off', 0)}负/{pair.get('tie', 0)}平" if pair else "—"
            lines.append(
                f"| {t} | {m} | {fmt_pct(cov)}±{round((cov_sd or 0) * 100)}pp | {fmt_pct(det)} | "
                f"{round(q, 3) if q is not None else '—'} | "
                f"{round(statistics.mean(exs), 3) if exs else '—'} | {comp_str} | "
                f"{rates[0] if rates else '—'} | {pair_str} |")
    lines += ["", "## 聚合与统计推断", ""]
    for name, s in stats.items():
        if name in ("efficiency",):
            continue
        if isinstance(s, dict) and s.get("mean_diff") is not None:
            lines.append(f"- **{name}**：Δ={fmt_pct(s['mean_diff'])}，95%CI[{fmt_pct(s['ci95'][0])}, "
                         f"{fmt_pct(s['ci95'][1])}]（On={fmt_pct(s.get('on_avg'))} / Off={fmt_pct(s.get('off_avg'))}，n={s['n_tasks']} 任务）")
        elif isinstance(s, dict):
            lines.append(f"- **{name}**：{json.dumps({k: v for k, v in s.items() if not isinstance(v, dict)}, ensure_ascii=False)}")
        else:
            lines.append(f"- **{name}**：{s}")
    pw = stats.get("pairwise", {})
    if pw:
        lines.append(f"- **pairwise 胜率(On, 平局=0.5)**：{fmt_pct(pw['win_rate_on'])}，"
                     f"Wilson95[{fmt_pct(pw['wilson95'][0])}, {fmt_pct(pw['wilson95'][1])}]"
                     f"（{pw['on']}胜/{pw['off']}负/{pw['tie']}平 / {pw['n']} 对）")
    eff = stats.get("efficiency", {})
    lines.append(f"- **efficiency**：{json.dumps(eff, ensure_ascii=False)}")
    lines += ["", "## 预期效果门（v1.0 冻结版，见 eval/EXPECTED.md）", ""]
    for g, v in gates.items():
        lines.append(f"- {'✅' if v['pass'] else '❌'} **{g}**：{v['desc']} —— {v['detail']}")
    lines += ["", "## 观察型指标（本轮采集，下一轮纳入门）", ""]
    for o in OBSERVATIONAL:
        lines.append(f"- {o}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["setup-e2e", "audit-annotations", "generate", "score"])
    ap.add_argument("--tasks", nargs="*")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--label", default=None)
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--model", default=None, help="生成模型覆盖（多模型泛化时用）")
    args = ap.parse_args()
    if args.phase == "setup-e2e":
        r1 = sh(["npm", "install", "--prefix", str(SCAFFOLD)], timeout=600)
        print("npm install", "ok" if r1.returncode == 0 else r1.stderr[-300:])
        r2 = sh(["./node_modules/.bin/playwright", "install", "chromium"], timeout=1200, cwd=SCAFFOLD)
        print("playwright install chromium", "ok" if r2.returncode == 0 else r2.stderr[-300:])
        if r2.returncode == 0:
            (SCAFFOLD / "node_modules" / ".browser-installed").write_text("ok")
        sys.exit(0 if (r1.returncode == 0 and r2.returncode == 0) else 1)
    run_dir = Path(args.run_dir) if args.run_dir else RESULTS / "runs" / (
        datetime.now().strftime("%Y%m%d_%H%M") + ("_" + args.label if args.label else ""))
    run_dir.mkdir(parents=True, exist_ok=True)
    if args.phase == "audit-annotations":
        phase_audit(run_dir)
    elif args.phase == "generate":
        ok = phase_generate(run_dir, only_tasks=args.tasks, samples=args.samples, model=args.model)
        print("run_dir:", run_dir)
        sys.exit(0 if ok else 1)
    else:
        ok = phase_score(run_dir, samples=args.samples)
        print("run_dir:", run_dir)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
