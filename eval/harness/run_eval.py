#!/usr/bin/env python3
"""qa-skills Benchmark harness v0.

用法：
  python3 eval/harness/run_eval.py generate            # 跑生成（Skill On / Off 双模式）
  python3 eval/harness/run_eval.py score               # 评分（客观检查 + LLM judge）+ 汇总报告
  python3 eval/harness/run_eval.py setup-e2e           # 安装 E2E 编译检查脚手架依赖（一次性）

方法学（对齐 docs/qa-skills-v2.md 第 12 章）：
  - 同任务集、同模型（--model 固定）、同 harness；On/Off 唯一差异是是否注入 Skill 指令
  - Coverage 分母 = 黄金集人工标注的可测点清单（annotation.json）
  - Executability = 一票否决指标：客观检查（占位符/模糊判定/正文代码泄漏/异步无时限/导读缺失）
    逐条扫用例，脏用例比例 > 50% 时该任务 Coverage 计 0
  - 主观质量用 LLM-as-judge（固定 rubric + JSON Schema 输出），judge prompt 纳入版本管理
"""
import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "eval" / "golden"
RESULTS = REPO / "eval" / "results"
MODEL = os.environ.get("EVAL_MODEL", "glm-5-2-260617")
GENERATE_TIMEOUT = int(os.environ.get("EVAL_GEN_TIMEOUT", "900"))
JUDGE_TIMEOUT = int(os.environ.get("EVAL_JUDGE_TIMEOUT", "600"))
MAX_OUTPUT_TOKENS = 32768
WORKERS = int(os.environ.get("EVAL_WORKERS", "3"))
JUDGE_SAMPLES = int(os.environ.get("EVAL_JUDGE_SAMPLES", "3"))

DETECTION_KEYS = ["known_bugs", "planted_violations", "expected_issues", "expected_risks",
                  "expected_findings", "expected_selections"]

PERSONA_OFF = (
    "你是一名资深软件测试工程师。请阅读用户提供的任务与材料，完成任务的最终产出。"
    "直接输出产出文件的完整内容，不要输出与产出无关的解释。"
)

EVAL_PREAMBLE = """【交付约定（评测模式）】
- 单轮交付：输入材料即全部已知信息；需要澄清的问题不要停下来等待答复，以「待澄清」清单并入交付文件末尾后继续完成交付。
- 只输出任务要求的那一份交付文件本身的完整内容；任务未明确要求的附加产物（如 Schema 抽取文件、独立审查报告）不要输出。
- 不要输出工作流过程叙述、阶段说明、与用户的对话或元评论——文件内容之外一个字都不要有。
"""


def sh(cmd, timeout=None, cwd=None, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env)


def load_task(task_dir: Path):
    ann = json.loads((task_dir / "annotation.json").read_text())
    task_md = (task_dir / "task.md").read_text()
    return ann, task_md


def call_model(instructions: str, prompt: str, timeout: int, max_tokens: int,
               schema_path: str = None, temperature: str = None, retries: int = 2,
               thinking: str = None):
    cmd = ["arkcli", "+chat", prompt, "--model", MODEL, "--no-progress",
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
                last_err = f"exit={r.returncode} stderr={r.stderr[:500]}"
            else:
                data = json.loads(r.stdout)
                content = data.get("content") or ""
                if content.strip():
                    return {"ok": True, "content": content, "usage": data.get("usage", {}),
                            "resp_id": data.get("id", ""), "raw": r.stdout}
                last_err = "empty content"
        except Exception as e:  # noqa: BLE001
            last_err = repr(e)[:500]
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


# ---------------------------------------------------------------- generate

def gen_one(task_name: str, mode: str, run_dir: Path):
    ann, task_md = load_task(GOLDEN / task_name)
    out_file = run_dir / "outputs" / f"{task_name}__{mode}.md"
    meta_file = run_dir / "outputs" / f"{task_name}__{mode}.meta.json"
    if out_file.exists() and json.loads(meta_file.read_text()).get("ok"):
        return task_name, mode, "cached"
    instr = build_on_instructions(ann["skill_files_on"]) if mode == "on" else PERSONA_OFF
    res = call_model(instr, EVAL_PREAMBLE + task_md, GENERATE_TIMEOUT, MAX_OUTPUT_TOKENS)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    meta = {"task": task_name, "mode": mode, "ok": res["ok"], "error": res.get("error"),
            "usage": res.get("usage", {}), "resp_id": res.get("resp_id", ""),
            "model": MODEL, "ts": datetime.now().isoformat(timespec="seconds")}
    if res["ok"]:
        out_file.write_text(res["content"])
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    return task_name, mode, ("ok" if res["ok"] else f"FAIL: {res.get('error')}")


def phase_generate(run_dir: Path, only_tasks=None, modes=("on", "off")):
    tasks = sorted(d.name for d in GOLDEN.iterdir() if d.is_dir())
    if only_tasks:
        tasks = [t for t in tasks if any(p in t for p in only_tasks)]
    jobs = [(t, m) for t in tasks for m in modes]
    print(f"[generate] {len(jobs)} runs, model={MODEL}, workers={WORKERS}")
    fails = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(gen_one, t, m, run_dir): (t, m) for t, m in jobs}
        for fut in concurrent.futures.as_completed(futs):
            t, m, status = fut.result()
            print(f"  {t} [{m}] -> {status}")
            if status.startswith("FAIL"):
                fails += 1
    if fails:
        print(f"[generate] {fails} FAILED —— 重跑同一命令即可续跑（已成功的会缓存）")
        return False
    return True


# ---------------------------------------------------------------- objective checks

CASE_START = re.compile(r"^\s*-\s+\*{0,2}TC-\d+-\d+", re.M)
PLACEHOLDER = re.compile(r"\{[A-Za-z_\u4e00-\u9fff][^{}\n]{0,30}\}")
FUZZ_WORDS = re.compile(r"某某|xxx|XXX")
CODE_LOC = re.compile(r"[A-Za-z0-9_]+\.(py|go|ts|tsx|js|java|sql|rb|rs):\d+")
VAGUE = re.compile(r"功能正常|正常显示|运行正常|系统正常|工作正常")
TIME_UNITS = re.compile(r"\d+\s*(秒|分钟|小时|天)|秒内|分钟内|小时内|天内")


def split_body_appendix(text):
    """优先按「附录」标题切；否则整段视为正文（模型常在导读区后就写 ---，不能用 --- 定位附录）。"""
    m = re.search(r"^#{2,3}\s*附录", text, re.M)
    return text[:m.start()] if m else text, text[m.start():] if m else ""


def split_cases(body):
    starts = [m.start() for m in CASE_START.finditer(body)]
    if not starts:
        return []
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
    body, appendix = split_body_appendix(text)
    cases = split_cases(body)
    dirty = 0
    viol_counts = {}
    for c in cases:
        vs = case_violations(c)
        if vs:
            dirty += 1
        for v in vs:
            viol_counts[v] = viol_counts.get(v, 0) + 1
    guide = {
        "intro_role": bool(re.search(r"功能简介|角色[:：]|角色表", text)),
        "env_account": bool(re.search(r"环境与账号|测试账号|后台入口", text)),
        "glossary": bool(re.search(r"术语表", text)),
        "legend": bool(re.search(r"图例", text)),
    }
    guide_score = sum(guide.values()) / 4
    clean_ratio = (len(cases) - dirty) / len(cases) if cases else (1.0 if not cases else 0)
    # 无用例可判时（分析类任务）不惩罚
    exec_score = round(0.5 * clean_ratio + 0.5 * guide_score, 4) if cases else None
    return {
        "n_cases": len(cases), "n_dirty": dirty, "clean_ratio": round(clean_ratio, 4),
        "violations": viol_counts, "guide": guide, "guide_score": round(guide_score, 4),
        "exec_score": exec_score, "veto": bool(cases and clean_ratio < 0.5),
    }


CODE_BLOCK = re.compile(r"```(\w+)?\n(.*?)```", re.S)
FILE_HINT = re.compile(r"([\w./-]+\.(?:py|ts|tsx|js))")


def extract_code_blocks(text, lang):
    blocks = []
    lines = text.splitlines()
    pending_file = None
    i = 0
    while i < len(lines):
        m = re.match(r"^```(\w+)?\s*$", lines[i])
        if m and (m.group(1) == lang or (lang is None)):
            j, buf = i + 1, []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j])
                j += 1
            code = "\n".join(buf)
            inner = FILE_HINT.search(code.splitlines()[0] if code.splitlines() else "")
            name = pending_file or (inner.group(1) if inner else None)
            blocks.append({"file": name, "code": code})
            i = j + 1
            pending_file = None
        else:
            hint = FILE_HINT.search(lines[i])
            if hint and len(lines[i]) < 120 and "```" not in lines[i]:
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


SCAFFOLD = REPO / "eval" / "harness" / "fixtures" / "playwright_scaffold"


def check_ts_compile(text):
    blocks = extract_code_blocks(text, "typescript")
    if not blocks:
        blocks = extract_code_blocks(text, "ts")
    if not blocks:
        return {"compile_pass": False, "n_blocks": 0, "errors": ["no ts code blocks"]}
    if not (SCAFFOLD / "node_modules").exists():
        return {"compile_pass": None, "n_blocks": len(blocks),
                "errors": ["scaffold not installed — run setup-e2e"]}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        shutil.copytree(SCAFFOLD, td / "proj", dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("node_modules"))
        proj = td / "proj"
        (proj / "node_modules").symlink_to(SCAFFOLD / "node_modules")
        spec_text = ""
        written = []
        for b in blocks:
            name = (b["file"] or f"gen_{abs(hash(b['code'])) % 9999}.spec.ts").lstrip("/")
            if "tests/" in name:                      # 规范化：去掉 playwright/ 等工程目录前缀
                name = name[name.index("tests/"):]
            target = proj / name if name.startswith("tests/") else proj / "tests" / Path(name).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(b["code"])
            written.append(target)
            if ".spec." in name:
                spec_text += b["code"] + "\n"
        # 对齐 PO 落盘路径与 spec 的 './pages/...' 导入（import 不带扩展名）
        for imp in set(re.findall(r"from\s+'(\./pages/[\w.-]+)'", spec_text)):
            base = imp.replace("./", "")
            for cand in (base + ".ts", base + ".tsx", base):
                wanted = proj / "tests" / cand
                if wanted.exists():
                    break
            else:
                for t in written:
                    if t.name in (Path(base).name + ".ts", Path(base).name + ".tsx") and str(t).endswith(t.name):
                        dst = proj / "tests" / (base + t.suffix)
                        if not dst.exists():
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            dst.write_text(t.read_text())
                            t.unlink()               # 移除非预期层级的原副本，避免其相对导入编不过
                        break
        r = sh(["./node_modules/.bin/tsc", "--noEmit", "-p", "tsconfig.json"],
               timeout=180, cwd=proj)
        errors = [l for l in r.stdout.splitlines() if "error TS" in l][:10]
        spec_checks = {
            "tc_naming": bool(re.search(r"test\(\s*['\"`][^'\"`]*TC-\d+-\d+", spec_text)),
            "no_fixed_wait": "waitForTimeout" not in spec_text,
            "po_usage": len(re.findall(r"page\.(locator|getByRole|getByTestId)\(", spec_text)) <= 2,
            "assert_persist": bool(re.search(r"reload|refresh", spec_text, re.I)),
        }
        return {"compile_pass": r.returncode == 0, "n_blocks": len(blocks), "errors": errors,
                "spec_checks": spec_checks}


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


# ---------------------------------------------------------------- judge

JUDGE_SCHEMA_PATH = REPO / "eval" / "harness" / "judge_schema.json"

JUDGE_PROMPT = """你是严格的测试产物评审官。对照给定的黄金标准，评审一份测试产出。

## 评审规则
1. 逐条核对「可测点清单」：产出中存在一条用例/内容实质覆盖该点即 covered=true（同一条用例可覆盖多个点；仅在提及概念而无验证动作时算 false）。evidence 填产出中的 TC 编号或原文短语（≤40 字）。
2. 逐条核对「检出项清单」：产出中实质发现/完成了该项即 detected=true（evidence 填产出原文短语，≤40 字）。要求的是实质命中，不是关键词碰巧出现。缺陷/风险记录常以**表格行**呈现（如 `| C2 | 现象 | 证据 |`），表格行同样算检出，逐行读。带 bucket 字段的项（回归清单类）：detected=true 要求该项出现在对应分桶——must=必须回归区、should=建议回归区、suggest_new=产出中有对应的新增用例建议、excluded=产出将其显式排除（排除清单）。
3. quality 三项各 0–5 分：
   - correctness：预期结果/结论与黄金标准规则一致，无错误断言或错误结论
   - specificity：数据/入口/判定具体（占位符、模糊判定扣分）
   - actionability：零上下文执行者能否直接按产出开工
4. notes 一句话总结最大缺陷。只输出 JSON。"""


def judge_one(task_name: str, mode: str, run_dir: Path):
    ann, _ = load_task(GOLDEN / task_name)
    out_file = run_dir / "outputs" / f"{task_name}__{mode}.md"
    judge_file = run_dir / "judge" / f"{task_name}__{mode}.json"
    if not out_file.exists():
        return task_name, mode, "missing-output"
    if judge_file.exists() and json.loads(judge_file.read_text()).get("ok"):
        return task_name, mode, "cached"
    output = out_file.read_text()
    gt_points = ann.get("testable_points", [])
    detections = []
    for k in DETECTION_KEYS:
        for item in ann.get(k, []):
            detections.append(item)
    payload = {
        "task": ann.get("description", task_name),
        "expected_output": ann.get("expected_output", ""),
        "points": [{"id": p["id"], "point": p["point"]} for p in gt_points],
        "detections": [{"id": d["id"], "point": d.get("point") or d.get("case") or d.get("desc", ""),
                        **({"bucket": d["bucket"]} if "bucket" in d else {})}
                       for d in detections],
        "agent_output": output[:60000],
    }
    prompt = JUDGE_PROMPT + "\n\n## 黄金标准与待评审产出（JSON）\n```json\n" + \
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n```"
    res = call_model(None, prompt, JUDGE_TIMEOUT, 16384,
                     schema_path=str(JUDGE_SCHEMA_PATH), temperature="0.2", thinking="disabled")
    judge_file.parent.mkdir(parents=True, exist_ok=True)
    if not res["ok"]:
        judge_file.write_text(json.dumps({"ok": False, "error": res.get("error")}, ensure_ascii=False))
        return task_name, mode, f"FAIL: {res.get('error')}"
    data = normalize_judge_json(res["content"])
    if data is None:
        judge_file.write_text(json.dumps({"ok": False, "error": "parse",
                                          "raw": res["content"][:2000]}, ensure_ascii=False))
        return task_name, mode, "FAIL: parse"
    # 多数表决采样（v2 §12.3②：多次采样取一致值）：共 3 个样本，逐点/逐项投票，质量分取中位数
    samples = [data]
    for _ in range(JUDGE_SAMPLES - 1):
        r2 = call_model(None, prompt, JUDGE_TIMEOUT, 16384,
                        schema_path=str(JUDGE_SCHEMA_PATH), temperature="0.2", thinking="disabled")
        if r2["ok"]:
            d2 = normalize_judge_json(r2["content"])
            if d2:
                samples.append(d2)
    merged = merge_judge_samples(samples)
    merged["ok"] = True
    merged["n_samples"] = len(samples)
    merged["usage"] = res.get("usage", {})
    judge_file.write_text(json.dumps(merged, ensure_ascii=False, indent=2))
    return task_name, mode, "ok"


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
    return {
        "point_results": [{"id": i, "covered": majority(v)} for i, v in pts.items()],
        "detection_results": [{"id": i, "detected": majority(v)} for i, v in dts.items()],
        "quality": quality,
        "notes": samples[0].get("notes", ""),
    }


POINT_KEYS = ("point_results", "points", "points_review", "coverage", "points_evaluation")
DETECT_KEYS = ("detection_results", "detections", "detections_review", "violations")


def normalize_judge_json(content: str):
    """容忍模型输出偏差：markdown 围栏、键名别名、截断。返回归一化 dict 或 None。"""
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(data, dict):
        return None
    pts, dts = None, None
    for k in (*POINT_KEYS, *DETECT_KEYS):        # 先按已知键名取
        v = data.get(k)
        if isinstance(v, list) and v and isinstance(v[0], dict):
            if pts is None and all("covered" in i for i in v):
                pts = v
            elif dts is None and all("detected" in i for i in v):
                dts = v
    for k, v in data.items():                    # 再按字段特征兜底（任意键名）
        if not (isinstance(v, list) and v and isinstance(v[0], dict)):
            continue
        if pts is None and all("covered" in i for i in v):
            pts = v
        elif dts is None and all("detected" in i for i in v):
            dts = v
    return {"point_results": pts or [], "detection_results": dts or [],
            "quality": data.get("quality") or {}, "notes": data.get("notes", "")}


def phase_score(run_dir: Path):
    rows = {}
    task_names = sorted(d.name for d in GOLDEN.iterdir() if d.is_dir())
    print("[score] judging ...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = []
        for t in task_names:
            for m in ("on", "off"):
                futs.append(ex.submit(judge_one, t, m, run_dir))
        for fut in concurrent.futures.as_completed(futs):
            print(f"  judge {fut.result()}")
    # aggregate
    for t in task_names:
        ann, _ = load_task(GOLDEN / t)
        n_points = len(ann.get("testable_points", []))
        n_detect = sum(len(ann.get(k, [])) for k in DETECTION_KEYS)
        for m in ("on", "off"):
            jf = run_dir / "judge" / f"{t}__{m}.json"
            of = run_dir / "outputs" / f"{t}__{m}.md"
            mf = run_dir / "outputs" / f"{t}__{m}.meta.json"
            row = {"task": t, "skill": ann.get("skill", ""), "mode": m}
            try:
                row["tokens"] = json.loads(mf.read_text()).get("usage", {})
            except Exception:  # noqa: BLE001
                row["tokens"] = {}
            if jf.exists():
                j = json.loads(jf.read_text())
                if j.get("ok"):
                    pts = j.get("point_results", [])
                    dts = j.get("detection_results", [])
                    row["coverage"] = round(sum(1 for p in pts if p.get("covered")) / len(pts), 4) if pts else None
                    row["detection"] = round(sum(1 for d in dts if d.get("detected")) / len(dts), 4) if dts else None
                    q = j.get("quality", {})
                    row["quality"] = round(sum(q.get(k, 0) for k in
                                               ("correctness", "specificity", "actionability")) / 15, 4)
                else:
                    row["judge_error"] = j.get("error")
            if of.exists():
                row["objective"] = objective_checks(t, of.read_text())
            # executability veto
            ex_obj = (row.get("objective") or {}).get("executability")
            if row.get("coverage") is not None:
                if ex_obj and ex_obj.get("veto"):
                    row["effective_coverage"] = 0.0
                    row["veto"] = True
                elif ex_obj and ex_obj.get("exec_score") is not None:
                    row["effective_coverage"] = round(row["coverage"] * ex_obj["exec_score"], 4)
                else:
                    row["effective_coverage"] = row["coverage"]
            rows[f"{t}__{m}"] = row
    # report
    lines = [f"# Benchmark 报告 — {run_dir.name}", "",
             f"- 模型：{MODEL}（On/Off 同模型同 harness，唯一差异 = 是否注入 Skill 指令）",
             f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}", ""]
    lines += ["## 逐任务结果", "",
              "| 任务 | 模式 | 覆盖 | 有效覆盖 | 检出 | 质量 | 可执行性 | 编译 | tokens(in/out) |",
              "|---|---|---|---|---|---|---|---|---|"]
    for t in task_names:
        for m in ("on", "off"):
            r = rows.get(f"{t}__{m}", {})
            ex_obj = (r.get("objective") or {}).get("executability")
            ex_s = ex_obj.get("exec_score") if ex_obj else None
            comp = r.get("objective", {}).get("compile_pass")
            u = r.get("tokens", {})
            lines.append(
                f"| {t} | {m} | {fmt_pct(r.get('coverage'))} | {fmt_pct(r.get('effective_coverage'))}"
                f" | {fmt_pct(r.get('detection'))} | {r.get('quality', '—')}"
                f" | {ex_s if ex_s is not None else '—'} | {comp if comp is not None else '—'}"
                f" | {u.get('prompt_tokens', '—')}/{u.get('completion_tokens', '—')} |")
    lines += ["", "## 聚合（On vs Off）", "", "| 指标 | Off | On | Δ |", "|---|---|---|---|"]
    agg = {}
    for metric, key in [("有效覆盖均值(tcw类)", "effective_coverage"),
                        ("检出率均值", "detection"), ("质量均分", "quality")]:
        for m in ("on", "off"):
            vals = [rows[f"{t}__{m}"].get(key) for t in task_names
                    if rows.get(f"{t}__{m}", {}).get(key) is not None]
            agg[(metric, m)] = round(sum(vals) / len(vals), 4) if vals else None
        o, n = agg[(metric, "off")], agg[(metric, "on")]
        d = round((n - o) * 100, 1) if (o is not None and n is not None) else None
        lines.append(f"| {metric} | {fmt_pct(o)} | {fmt_pct(n)} | {f'+{d}pp' if d is not None else '—'} |")
    # gates
    lines += ["", "## 预期效果门（详见 eval/EXPECTED.md）", ""]
    gates = evaluate_gates(rows, task_names)
    for g in gates:
        lines.append(f"- {'✅' if g['pass'] else '❌'} **{g['id']} {g['name']}**：{g['detail']}")
    (run_dir / "metrics.json").write_text(json.dumps(
        {"rows": rows, "aggregate": {f"{k[0]}|{k[1]}": v for k, v in agg.items()},
         "gates": gates, "model": MODEL}, ensure_ascii=False, indent=2))
    (run_dir / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    latest = RESULTS / "LATEST.md"
    latest.write_text("\n".join(lines) + "\n")
    return all(g["pass"] for g in gates)


def fmt_pct(v):
    if v is None:
        return "—"
    return f"{round(v * 100, 1)}%"


TCW_PREFIXES = ("tcw-", "rev-")


def evaluate_gates(rows, task_names):
    gates = []

    def vals(key, prefix=None):
        out = {"on": [], "off": []}
        for t in task_names:
            if prefix and not t.startswith(prefix):
                continue
            for m in ("on", "off"):
                v = rows.get(f"{t}__{m}", {}).get(key)
                if v is not None:
                    out[m].append(v)
        return out

    def mean(xs):
        return sum(xs) / len(xs) if xs else None

    ec = vals("effective_coverage", "tcw-")
    m_on, m_off = mean(ec["on"]), mean(ec["off"])
    delta = round((m_on - m_off) * 100, 1) if m_on is not None and m_off is not None else None
    gates.append({"id": "G1a", "name": "tcw 任务有效覆盖均值 On ≥ Off + 5pp",
                  "pass": delta is not None and delta >= 5,
                  "detail": f"On={fmt_pct(m_on)} Off={fmt_pct(m_off)} Δ={delta}pp（G1 定义见 eval/EXPECTED.md 修订记录）"})
    os_on = rows.get("tcw-order-state__on", {}).get("effective_coverage")
    os_off = rows.get("tcw-order-state__off", {}).get("effective_coverage")
    os_d = round((os_on - os_off) * 100, 1) if os_on is not None and os_off is not None else None
    gates.append({"id": "G1b", "name": "状态机任务覆盖 On ≥ Off + 20pp",
                  "pass": os_d is not None and os_d >= 20,
                  "detail": f"On={fmt_pct(os_on)} Off={fmt_pct(os_off)} Δ={os_d}pp"})

    ex_on = [rows[f"{t}__on"]["objective"]["executability"]["exec_score"]
             for t in task_names if t.startswith(TCW_PREFIXES)
             and (rows.get(f"{t}__on", {}).get("objective", {}).get("executability", {}) or {}).get("exec_score") is not None]
    me = mean(ex_on)
    gates.append({"id": "G2", "name": "tcw 类 On 可执行性均分 ≥ 0.75",
                  "pass": me is not None and me >= 0.75, "detail": f"On 可执行性均值={me}"})

    bug_row = rows.get("tcw-user-delete-code__on", {})
    bug_det = bug_row.get("detection")
    gates.append({"id": "G3", "name": "代码任务 bug 检出 On ≥ 75%",
                  "pass": bug_det is not None and bug_det >= 0.75,
                  "detail": f"On 检出={fmt_pct(bug_det)}（4 个植入 bug）"})

    comp = [rows[f"{t}__on"]["objective"].get("compile_pass")
            for t in ("api-openapi-coupon", "e2e-markmap-to-spec")
            if rows.get(f"{t}__on", {}).get("objective")]
    all_pass = bool(comp) and all(c is True for c in comp)
    gates.append({"id": "G4", "name": "代码类任务 On 编译通过率 100%",
                  "pass": all_pass, "detail": f"结果={comp}"})

    q = vals("quality")
    mq_on, mq_off = mean(q["on"]), mean(q["off"])
    gates.append({"id": "G5", "name": "质量均分 On ≥ 4.0/5 且 ≥ Off",
                  "pass": mq_on is not None and mq_on >= 0.8 and mq_on >= (mq_off or 0),
                  "detail": f"On={mq_on} Off={mq_off}"})

    wins, total_cmp = 0, 0
    for t in task_names:
        r_on = rows.get(f"{t}__on", {})
        r_off = rows.get(f"{t}__off", {})
        worse = True
        for k in ("effective_coverage", "coverage", "detection"):
            a, b = r_on.get(k), r_off.get(k)
            if a is not None and b is not None and not (a is None or b is None or a < b - 0.10):
                worse = False
                break
        if any(r_on.get(k) is not None for k in ("effective_coverage", "coverage", "detection")):
            total_cmp += 1
            if not worse:
                wins += 1
    gates.append({"id": "G6", "name": "On 在 ≥ 2/3 任务上不劣于 Off（-10pp 容差）",
                  "pass": total_cmp > 0 and wins / total_cmp >= 2 / 3,
                  "detail": f"不劣于 {wins}/{total_cmp}"})
    return gates


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["generate", "score", "setup-e2e"])
    ap.add_argument("--tasks", nargs="*", help="任务名子串过滤")
    ap.add_argument("--label", default=None, help="run 目录标签")
    ap.add_argument("--run-dir", default=None, help="复用既有 run 目录（score 阶段）")
    args = ap.parse_args()
    if args.phase == "setup-e2e":
        r = sh(["npm", "install", "--prefix", str(SCAFFOLD)], timeout=600)
        print("npm install exit", r.returncode, r.stderr[-500:] if r.returncode else "ok")
        sys.exit(r.returncode)
    run_dir = Path(args.run_dir) if args.run_dir else RESULTS / "runs" / (
        datetime.now().strftime("%Y%m%d_%H%M") + ("_" + args.label if args.label else ""))
    run_dir.mkdir(parents=True, exist_ok=True)
    if args.phase == "generate":
        ok = phase_generate(run_dir, only_tasks=args.tasks)
        print("run_dir:", run_dir)
        sys.exit(0 if ok else 1)
    else:
        if args.tasks:
            global GOLDEN  # noqa: PLW0603
            GOLDEN = REPO / "eval" / "golden"
        ok = phase_score(run_dir)
        print("run_dir:", run_dir)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
