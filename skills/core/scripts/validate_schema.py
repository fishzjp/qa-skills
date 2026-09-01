#!/usr/bin/env python3
"""Test Case Schema 校验器（markmap ↔ schema.yaml 一致性）+ 测试策略类型域校验（V1–V5 + 覆盖门禁）.

模式一（用例 Schema，配套 core/schema-extraction.md，抽取 / 修订重抽后运行）：

    python3 validate_schema.py 测试用例_markmap.md 测试用例.schema.yaml

  1. YAML 可解析（转义纪律）——环境装有 PyYAML 时全量解析并检查枚举值；
     未安装时降级为基础 lint（引号配对 / 裸引号），仍能抓住
     "双引号值内裸放引号" 这类最常见的中断下游消费的解析错误
  2. TC 编号一致性——schema 中的 id 必须存在于 markmap（孤儿报错），
     markmap 中的编号缺失于 schema（遗漏告警，增量更新场景可接受但需人工确认）
  3. 占位符——title / steps / expected 等字段值出现 {xxx} / <xxx> / 「某某」即报错
     （用例可执行性红线，见 core/executability.md）
  4. 契约词表与结构——tags 词表外标签告警；module 编号与 TC 编号首段不一致报错；
     用例级 preconditions 与顶层 modules 表共享前置重复仅告警

模式二（测试策略类型域决策，配套 core/test-type-matrix.md，test-strategy 落盘后运行）：

    python3 validate_schema.py 测试策略.md

  V1 全轴必答——十轴齐全且 decision ∈ include/exclude/handoff（每轴单行 flow 风格）；
     depth ∈ full/standard/light（"不测"是范围决策不是深度值：功能域 include: false，
     类型域 decision: exclude/handoff）
  V2 include 挂证据——signals 或 risk_refs 非空（无证据纳入 = 过测）
  V3 exclude 挂理由——rationale 非空 + scanned 含 G 级与 S 级双记录（无理由排除 = 漏测；
     无代码仓库场景豁免 S 级）；security_business 为硬默认轴（Web/API 系统无排除
     出口），其 exclude 须在 rationale 声明非 Web/API 依据，否则告警级提示复核
  V4 full 有预算——depth=full 轴必须挂 risk_refs；full 总数（两域合并）≤3，
     超限须有 budget_review（预算裁决记录，R6>R1）；depth_budget.full_axes 与实际一致。
     两域 scope 可写在同一或不同 yaml 代码块，均纳入统计
  V4-终态留痕——include 且挂 Critical 风险的类型域轴若 depth 未达 full，其轴名必须出现
     在 budget_review 文本中（堵住"先超限触发检查点、再裁剪回 ≤3 后无迹可查"的逃逸窗口：
     维持低档也须留一行依据，不许无声消失）
  V5 移交不断链——execution_status=blocked 必带 todo；executor 非空且非 agent 时
     （含 handoff）必带 handoff_ref

模式三（可选增强参数，两模式均可叠加）：

    --strategy 测试策略.md   仅模式一生效：从策略正文的 Risk Map 提取 Critical/High 风险编号，
                             校验每条均被至少一条用例的 risk_ref 反向覆盖（证据链最后一环，
                             Critical/High 风险零覆盖 = 报错）；risk_ref 指涉未知编号则告警（疑似笔误）
    --repo-root <仓库路径>   抽查指涉真实性：axis signals 与用例 code_refs 中形如
                             "path.ext:行号" 的文件必须在指定仓库下真实存在（缺失告警，
                             防"格式合规的幻觉证据"穿过 V2/V3 形式闸门）

退出码：0 通过（含告警）/ 1 有错误
"""
import argparse
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

# ---------- 三层契约词表（core/schema-extraction.md「文件整体形态」） ----------
# tags 两组合法值：可测试性标注 + 类型域轴标签；开放格式下的拼写防呆，词表外只告警
TAG_VOCAB = {
    "[需真机]", "[需Mock]", "[需专业环境]",
    "[并发]", "[可靠]", "[安全]", "[兼容]", "[迁移]", "[集成]", "[国际化]",
}
MODULE_NUM_RE = re.compile(r"^\s*(\d+)")   # 一级模块标题首段编号（"2. 营销活动" → 2）

# ---------- 审计加固常量（覆盖门禁 / 终态留痕 / 指涉抽查） ----------
# 硬默认轴集合：矩阵 §轴2——Web/API 系统一律 standard，无 R4 排除出口
HARD_DEFAULT_AXES = {"security_business"}
# 风险编号与等级词形：risk-model.md 权威口径为 R1…Rn + Critical/High/Medium/Low
RISK_ID_RE = re.compile(r"\bR\d{1,3}\b")
CRITICAL_WORD_RE = re.compile(r"\bCritical\b", re.I)
HIGH_WORD_RE = re.compile(r"\bHigh\b", re.I)
# 仓库内文件指涉形态："路径/文件名.ext:行号"（signals 与 code_refs 共用）
REPO_FILE_LOC_RE = re.compile(
    r"([\w.\-/\\]{1,120}\.(?:py|go|java|kt|swift|m|ts|tsx|js|jsx|mjs|vue|svelte|"
    r"rb|php|cs|scala|dart|sql|yaml|yml|json|toml|xml|proto|sh|gradle)):(\d+)", re.I)


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
    # tags 词表防呆：未知标签不阻断，但提示人工确认拼写或补词表
    for tag in as_list(case.get("tags")):
        if tag not in TAG_VOCAB:
            warnings.append(f"{cid}: tags 含词表外标签 '{tag}'（合法集见 schema-extraction.md tags 注释）")
    # module 编号与 TC 编号首段一致性：挂错模块属结构性笔误；任一侧解析不出编号则跳过
    m_case = re.match(r"TC-(\d+)-\d+", str(cid))
    mod = case.get("module")
    if m_case and isinstance(mod, str):
        m_mod = MODULE_NUM_RE.match(mod)
        if m_mod and int(m_mod.group(1)) != int(m_case.group(1)):
            errors.append(f"{cid}: id 模块号 {m_case.group(1)} 与 module '{mod}' 的编号不一致")


def collect_shared_preconditions(doc):
    """读取顶层 modules 表的共享前置集合 {前置原文: 模块名}；旧形态无此键时返回空表。"""
    out = {}
    for mod in (doc.get("modules") or []) if isinstance(doc, dict) else []:
        if isinstance(mod, dict):
            name = str(mod.get("module", "?"))
            for pre in as_list(mod.get("shared_preconditions")):
                out[pre] = name
    return out


def as_list(val):
    """字段值统一为字符串列表（兼容 str / list / None 三种落盘形态）。"""
    if isinstance(val, list):
        return [v for v in val if isinstance(v, str)]
    if isinstance(val, str):
        return [val]
    return []


def extract_risk_levels(md_text):
    """从策略/风险正文中提取 {风险编号: 等级}，同号取最高级（Critical > High > 其余忽略）。

    只认 Critical / High 两个门禁相关等级；扫描逐行进行，行内同时出现编号与等级词
    才建立映射——宽松启发式，误报只会让门禁偏严而非偏松。
    """
    levels = {}
    for line in md_text.splitlines():
        rids = set(RISK_ID_RE.findall(line))
        if not rids:
            continue
        if CRITICAL_WORD_RE.search(line):
            lv = "Critical"
        elif HIGH_WORD_RE.search(line):
            lv = "High"
        else:
            continue
        for rid in rids:
            old = levels.get(rid)
            if old == "Critical" or (old == "High" and lv != "Critical"):
                continue
            levels[rid] = lv
    return levels


def check_path_refs(items, repo_root, ctx, warnings):
    """抽查 items 中 "文件.ext:行号" 指涉在 repo_root 下真实存在；缺失按告警不按错误。

    行号无法机械核对（代码会漂移），文件存在性是最便宜的反幻觉锚点：
    抓"穿了 V2/V3 合规外衣、指向不存在文件的幻觉证据"这一最高频伪造形态。
    """
    seen = set()
    for item in items:
        m = REPO_FILE_LOC_RE.search(item)
        if not m:
            continue
        rel = m.group(1)
        key = f"{ctx}:{rel}"
        if key in seen:
            continue
        seen.add(key)
        if not (repo_root / rel).is_file():
            warnings.append(f"{ctx}: 指涉文件不存在于 --repo-root 仓库: {rel}（核实是否幻觉证据或路径笔误）")


def check_risk_coverage(cases, strategy_md_path, errors, warnings):
    """覆盖门禁：策略 Risk Map 中全部 Critical/High 风险必须被 ≥1 条用例的 risk_ref 反向覆盖。

    risk-model.md §双向引用主从规则：机器消费一律走 case.risk_ref 反查——
    此前该末环无任何机械校验，Critical 风险零覆盖也能全绿过检。本函数补上这最后一道闸。
    """
    try:
        text = Path(strategy_md_path).read_text(encoding="utf-8").replace("\r\n", "\n")
    except OSError as e:
        errors.append(f"--strategy 文件不可读: {e}")
        return
    levels = extract_risk_levels(text)
    known_ids = set(levels)
    covered = set()
    for case in cases:
        refs = as_list(case.get("risk_ref"))
        for r in refs:
            rid = r.strip()
            if RISK_ID_RE.fullmatch(rid):
                covered.add(rid)
            if rid and known_ids and rid not in known_ids:
                warnings.append(f"{case.get('id', '?')}: risk_ref='{rid}' 未在策略 Risk Map 中找到（疑似编号笔误）")
    gate = {rid for rid, lv in levels.items() if lv in ("Critical", "High")}
    for rid in sorted(gate - covered):
        errors.append(f"风险覆盖: {levels[rid]} 风险 {rid} 无任何用例通过 risk_ref 覆盖"
                      "（证据链最后一环断裂——要么补用例挂 ref，要么经预算裁决降级并留痕）")


# ---------- 模式二：测试策略类型域校验（V1–V5，配套 core/test-type-matrix.md） ----------

TYPE_AXES = ["performance", "security_business", "reliability", "concurrency",
             "compatibility", "accessibility", "visual", "i18n", "migration",
             "contract_integration"]
FULL_MAX = 3
DEPTHS = {"full", "standard", "light"}
# 轴 2（security_business）排除的合法依据形态：系统非 Web/API（命令行 / 桌面 / 离线库等）。
# 宽松匹配——告警级提示复核，不是门禁
NON_WEB_API_RE = re.compile(
    r"非\s*[-/·、\s]*[Ww]eb|非\s*[-/·、\s]*API|无\s*[-/·、\s]*[Ww]eb|无\s*[-/·、\s]*API"
    r"|不是\s*[Ww]eb|不是\s*API|命令行|CLI|桌面|离线|纯库|无网络|无界面")
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


def validate_strategy(path, repo_root=None):
    errors, warnings = [], []
    # 统一换行（Windows 宿主产物的 CRLF 会让行锚定正则全部失配）
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    block = extract_scope_blocks(text)
    if block is None:
        errors.append("未找到含 type_scope:/functional_scope: 的 yaml 代码块——测试策略必须包含类型域十轴决策（V1）")
        return errors, warnings
    # Risk Map 等级抽取：供 V4-终态留痕判定哪些轴挂着 Critical 风险；
    # 仅行内同现 Rn 与等级词才建立映射，全文提不出等级则该检查自动失效（偏松方向，不误伤正常流）
    risk_levels = extract_risk_levels(text)

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
            elif axis == "security_business" and not NON_WEB_API_RE.search(rationale):
                # 硬默认轴（矩阵 §4：Web/API 系统一律 standard，无排除出口）——
                # 脚本无法判定系统形态，故仅告警：排除仅在非 Web/API 系统成立，
                # rationale 未声明该依据时提示人工复核
                warnings.append(
                    f"V3 {axis}: exclude 但 rationale 未声明非 Web/API 依据——"
                    "该轴为硬默认轴（Web/API 系统无排除出口），请复核排除是否成立")
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
    critical_low_axes = []  # include 且挂 Critical 风险但 depth<full 的轴名——终态留痕候选
    seen_names = set()
    for m in FLOW_LINE_RE.finditer(block):
        name, inner = m.group(1), m.group(2)
        if name in seen_names:
            continue  # 重复轴已由 V1 报错；统计以首处为准
        seen_names.add(name)
        kv = parse_flow_map(inner)
        depth = scalar(kv, "depth")
        decision = kv.get("decision", "")
        # depth 缺省警示：类型域轴必须显式声明档位，否则绕过 full_axes/预算审计链；
        # functional_scope 行无 depth 属常态，仅对类型域轴名告警防误伤
        if name in TYPE_AXES and not depth:
            warnings.append(
                f"V4 {name}: depth 缺省——档位未声明则不参与 full_axes/预算审计，"
                "请显式写入 full/standard/light（'不测'应表达为 exclude/handoff 并挂理由）")
        # 指涉真实性抽查：signals / scanned 中 "文件.ext:行号" 必须真实存在于仓库（告警级，
        # 抓"格式合规的幻觉证据"，见 --repo-root 参数说明）
        if repo_root is not None:
            check_path_refs(list_items(kv.get("signals")) + list_items(kv.get("scanned")),
                            repo_root, name, warnings)
        # V4-终态留痕候选：挂 Critical 风险却未给足深度的降档裁量，必须在 budget_review 留痕
        rids = [r.strip() for r in list_items(kv.get("risk_refs"))]
        if (decision == "include" and depth and depth != "full"
                and any(risk_levels.get(r) == "Critical" for r in rids)):
            critical_low_axes.append(name)
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
    elif full_axes:
        # 实际存在 full 轴却检不出行内数组声明：或漏写、或用了多行展开式（后者不受支持），
        # 两种情况都令一致性核对失效——警示级提示人工补声明
        warnings.append(
            f"V4 未检出 depth_budget.full_axes 行内数组声明（实际 full 轴 {full_axes}）"
            "——缺声明或多行展开式（不受支持），无法核对一致性")
    if len(full_axes) > FULL_MAX and not re.search(r"^[ \t]*budget_review:", block, re.M):
        errors.append(f"V4 full 轴 {len(full_axes)} 个 > {FULL_MAX}（两域合并）："
                      "须触发预算裁决检查点并记录 budget_review（R6 > R1）")
    # V4-终态留痕：堵住"先超限触发裁决、再裁剪回 ≤3 后无迹可查"的逃逸窗口——
    # 每条 Critical 降档裁量都须在 budget_review 文本中留下轴名，不许无声消失
    if critical_low_axes:
        m_br = re.search(r"(?ms)^[ \t]*budget_review:[ \t]*(.*?)(?=^[ \t]*\w+:|\Z)", block)
        br_text = m_br.group(1) if m_br else ""
        for ax in critical_low_axes:
            if ax not in br_text:
                errors.append(
                    f"V4-终态 {ax}: include 且挂 Critical 风险但 depth 未达 full,"
                    " 且 budget_review 中无该轴的降档依据（深度降档属重大裁量，须留一行依据）")
    return errors, warnings


def build_arg_parser():
    """构造 CLI 参数解析器：位置文件参数个数区分两模式，可选增强参数可叠加。"""
    parser = argparse.ArgumentParser(
        description="Test Case Schema 校验器（模式一）+ 测试策略类型域校验（模式二）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    parser.add_argument("files", nargs="+", metavar="文件",
                        help="1 个 = 测试策略.md（模式二）；2 个 = markmap + schema.yaml（模式一）")
    parser.add_argument("--strategy", metavar="PATH", default=None,
                        help="仅模式一：风险覆盖门禁——策略 Risk Map 中的 Critical/High 风险"
                             "必须被至少一条用例的 risk_ref 反向覆盖")
    parser.add_argument("--repo-root", metavar="DIR", default=None, dest="repo_root",
                        help="指涉真实性抽查：signals / code_refs 中 '文件.ext:行号' 形式的"
                             "引用须在该目录下真实存在（缺失告警）")
    return parser


def main(argv=None):
    """CLI 入口：按位置参数个数分发模式一/二，并叠加覆盖门禁与指涉抽查两项增强校验。"""
    args = build_arg_parser().parse_args(argv)
    paths = [Path(p) for p in args.files]
    repo_root = Path(args.repo_root) if args.repo_root else None
    strategy_md = Path(args.strategy) if args.strategy else None

    # 参数前置体检：目录/文件存在性在进任何业务校验前拦截
    if repo_root is not None and not repo_root.is_dir():
        print(f"错误: --repo-root 不是存在的目录: {repo_root}")
        return 1
    if len(paths) > 2:
        print(build_arg_parser().format_usage())
        print("错误: 文件参数最多 2 个（markmap + schema.yaml，或仅一个测试策略.md）")
        return 1
    for p in paths:
        if not p.is_file():
            print(f"错误: 文件不存在或不是普通文件 {p}")
            return 1
    if strategy_md is not None and len(paths) != 2:
        print("提示: --strategy 仅模式一（两个文件参数）生效，本次调用已忽略")
        strategy_md = None

    # ---------- 模式二：测试策略类型域校验（单文件参数） ----------
    if len(paths) == 1:
        p = paths[0]
        errors, warnings = validate_strategy(p, repo_root=repo_root)
        for e in errors:
            print(f"  ✗ {e}")
        for w in warnings:
            print(f"  ⚠ {w}")
        verdict = "✅ 类型域决策校验通过（V1–V5 + 终态留痕）" if not errors else f"✗ {len(errors)} 个错误"
        print(f"{verdict}: {p.name}")
        return 1 if errors else 0

    # ---------- 模式一：用例 Schema 校验（双文件参数） ----------
    md_path, yaml_path = paths
    errors, warnings = [], []
    for _p, _label in ((yaml_path, "schema"), (md_path, "markmap")):
        try:
            _p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"错误: {_label} 文件非 UTF-8 编码（{_p}）。"
                  "请以 UTF-8 重新保存后重试（Windows 记事本默认 ANSI/GBK）")
            return 1
    yaml_text = yaml_path.read_text(encoding="utf-8")
    md_text = md_path.read_text(encoding="utf-8")

    cases = []
    shared_pres = {}   # {前置原文: 模块名}：顶层 modules 表的共享前置，供去冗余复核
    parsed_ok = False   # 仅在 PyYAML 真正完成解析时置位（降级 lint 不算，防止误报零用例）
    try:
        import yaml  # type: ignore
        docs = [d for d in yaml.safe_load_all(yaml_text) if d is not None]
        for doc in docs:
            walk_cases(doc, cases)
            shared_pres.update(collect_shared_preconditions(doc))
        parsed_ok = True
    except ImportError:
        warnings.append("未安装 PyYAML，降级为基础 lint（引号配对 / 裸引号），建议 pip install pyyaml")
        lint_yaml_basic(yaml_text, errors)
    except Exception as e:  # yaml.YAMLError 等
        errors.append(f"YAML 解析失败（检查转义纪律，见 core/schema-extraction.md）: {e}")

    # 零用例骗绿防线：YAML 合法但一条 TC 都没收集到（顶层 key 拼错/结构漂移的典型形态），
    # 直接判失败——格式合法的空产物是最常见的失败形态，不能让它全绿通过
    if parsed_ok and not cases:
        errors.append("schema 中未发现任何 TC 用例（检查顶层 key 是否为 test_cases、"
                      "结构是否符合 core/schema-extraction.md）")

    for case in cases:
        check_case(case, errors, warnings)
        # 共享前置去冗余复核（case-format §5）：与模块级重复声明仅告警
        cid = str(case.get("id", "?"))
        for pre in as_list(case.get("preconditions")):
            if pre in shared_pres:
                warnings.append(
                    f"{cid}: 前置 '{pre}' 与模块级共享前置重复"
                    f"（module={shared_pres[pre]}），应只写该条特有部分")

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

    # 增强校验一：--strategy 风险覆盖门禁（证据链最后一环）
    if strategy_md is not None:
        check_risk_coverage(cases, strategy_md, errors, warnings)
    # 增强校验二：--repo-root 指涉抽查（code_refs 反幻觉锚点）
    if repo_root is not None:
        for case in cases:
            check_path_refs(as_list(case.get("code_refs")), repo_root,
                            str(case.get("id", "?")), warnings)

    for e in errors:
        print(f"  ✗ {e}")
    for w in warnings:
        print(f"  ⚠ {w}")
    n_ok = len(cases)
    verdict = "✅ 校验通过" if not errors else f"✗ {len(errors)} 个错误"
    print(f"{verdict}（用例 {n_ok} 条，错误 {len(errors)}，告警 {len(warnings)}）: {yaml_path.name}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
