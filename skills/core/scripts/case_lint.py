#!/usr/bin/env python3
"""用例红线确定性检查器（markmap 用例文件）——不调模型、零第三方依赖.

配套 core/executability.md（8 条硬标准 + 第 4 节红线）与 core/case-format.md
（导读四件套 / TC 编号 / 四段式 / 附录隔离）。这些规则的权威定义仍在两份 core
文档中，本脚本只把它们里**可机械判定**的部分变成闸门，供产出方自查与评审方复核：

    python3 case_lint.py 测试用例_markmap.md [--allow-compact] [--json]

为什么需要它：可执行性是本框架的一票否决项，但此前只写在散文里——弱模型不会
自查、评审方也无法机械复核，只能靠"看起来专业"。闸门把"看起来"变成"测出来"。

检查项（E = 错误，阻断定稿；W = 告警，需人工确认）：

    E1  导读四件套缺失（功能简介/角色、环境与账号、术语、图例）
    E2  TC 编号不符合 TC-{模块号}-{序号}
    E3  TC 编号重复
    E4  TC 编号的模块号与所在 `## N.` 模块不符
    E5  正文占位符（{xxx} / <xxx> / 某数据）
    E6  正文出现代码内部（文件:行）
    E7  用例缺 操作步骤 / 预期结果（紧凑格式须显式 --allow-compact）
    E8  一级模块编号 `## N.` 重复（导读占用模块编号时高发）
    W1  预期结果不可判定（"是否正确处理 / 正常显示 / 视情况"类）
    W2  异步预期缺判定时限（有"自动/异步/生效"而无时间词）
    W3  预期结果非唯一（"或"表述，应拆条）
    W4  未标注优先级的用例数

附录区（`## 附录…` / `## 审查记录…` 之后）整体跳过 E5/E6/W1-W3——那里按
core/case-format.md 第 9 节就该放代码证据与缺陷记录。

退出码：0 = 无错误（告警不算失败）；1 = 有错误（须修复后重跑）。
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ---------- 结构识别 ----------
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET_RE = re.compile(r"^(\s*)[-*]\s+(.*)$")
MODULE_HEADING_RE = re.compile(r"^##\s+(\d+)\s*[.、]")
FENCE_RE = re.compile(r"^\s*(```|~~~)")

TC_ANY_RE = re.compile(r"TC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
TC_CANON_RE = re.compile(r"^TC-(\d+)-(\d+)$")
CASE_LINE_RE = re.compile(r"^\s*[-*]\s+(?:\*\*)?\s*(TC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)")

FIELD_NAMES = ("前置条件", "操作步骤", "预期结果", "验证方式")
PRIORITY_RE = re.compile(r"\[(P0|P1|P2)\]")

# ---------- 内容红线 ----------
# {xxx} / {券名称} 形态；排除 JSON/模板语法（含引号、冒号、逗号、数字开头）
BRACE_RE = re.compile(r"\{([^{}\n]{1,40})\}")
ANGLE_RE = re.compile(r"<([^<>\n]{1,40})>")
WORDISH_RE = re.compile(r"^[\u4e00-\u9fff A-Za-z_][\u4e00-\u9fff A-Za-z0-9_ \-]*$")
MOU_RE = re.compile(r"某(?:某|数据|账号|账户|用户|活动|订单|接口)")
# HTML/XML 标签不是占位符（<div> 等允许出现在测试数据里）
HTML_TAGS = {
    "a", "b", "br", "button", "code", "div", "em", "form", "h1", "h2", "h3",
    "h4", "h5", "h6", "i", "img", "input", "label", "li", "ol", "option", "p",
    "path", "pre", "script", "select", "span", "strong", "style", "svg",
    "table", "tbody", "td", "textarea", "th", "thead", "tr", "ul",
}
CODE_REF_RE = re.compile(
    r"[\w./-]+\.(?:py|ts|tsx|js|jsx|go|java|kt|rs|rb|php|cs|swift|sql|vue|svelte):\d+"
)
UNDETERMINABLE_RE = re.compile(
    r"是否正确|是否正常|是否允许|是否视为|视情况|待确认|功能正常|正常显示|无异常"
)
ASYNC_RE = re.compile(r"自动|异步|稍后|生效|轮询|超时")
TIME_LIMIT_RE = re.compile(r"毫秒|秒|分钟|小时|工作日|当天|次日|立即|实时|即刻")
ALTERNATIVE_RE = re.compile(r"[，。；]?\s*或\s*")

PREAMBLE_ITEMS = (
    ("功能简介/角色表", re.compile(r"功能简介|角色表|角色说明")),
    ("环境与账号表", re.compile(r"环境.{0,8}账号|账号.{0,8}环境|环境与账号|测试账号")),
    ("术语表", re.compile(r"术语")),
    ("图例", re.compile(r"图例|标注说明")),
)


class Finding(object):
    __slots__ = ("code", "severity", "line", "message")

    def __init__(self, code, severity, line, message):
        self.code = code
        self.severity = severity
        self.line = line
        self.message = message

    def as_dict(self):
        return {
            "code": self.code,
            "severity": self.severity,
            "line": self.line,
            "message": self.message,
        }


class Case(object):
    __slots__ = ("line", "tc", "text", "indent", "module", "fields")

    def __init__(self, line, tc, text, indent, module):
        self.line = line
        self.tc = tc
        self.text = text
        self.indent = indent
        self.module = module
        self.fields = {}   # field name -> 正文（含续行）


def mask_fences(lines):
    """把围栏代码块内容替换为等长空白（保留行号），避免示例代码被当成用例正文。"""
    masked = []
    in_fence = False
    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            masked.append(" " * len(line))
            continue
        masked.append(" " * len(line) if in_fence else line)
    return masked


def is_appendix_heading(title):
    return ("附录" in title) or ("审查记录" in title)


def is_placeholder(match_text):
    inner = match_text.strip()
    if not inner or inner.isdigit():
        return False
    if inner.lower() in HTML_TAGS:
        return False
    return bool(WORDISH_RE.match(inner))


def find_placeholders(text):
    hits = []
    for m in BRACE_RE.finditer(text):
        if is_placeholder(m.group(1)):
            hits.append(m.group(0))
    for m in ANGLE_RE.finditer(text):
        if is_placeholder(m.group(1)):
            hits.append(m.group(0))
    for m in MOU_RE.finditer(text):
        hits.append(m.group(0))
    return hits


def split_field(body):
    """解析 "- 操作步骤: xxx" / "- **操作步骤**：xxx" / 同缩进扁平写法。

    弱模型产出的字段行形态不统一（加粗标签、全角冒号、与用例同缩进），
    只认一种写法会把"写了但没识别到"误报成 E7。
    """
    s = re.sub(r"^[\s*_]+", "", body.strip())
    for name in FIELD_NAMES:
        if s.startswith(name):
            rest = re.sub(r"^[\s*_]*[：:]?[\s*_]*", "", s[len(name):])
            return name, rest.strip()
    return None, None


def parse_cases(masked_lines):
    """解析用例块与模块上下文；返回 (cases, 首条用例行号)。"""
    cases = []
    current_module = None
    current = None
    in_appendix = False
    first_case_line = None

    for idx, line in enumerate(masked_lines, start=1):
        heading = HEADING_RE.match(line)
        if heading:
            current = None
            title = heading.group(2).strip()
            if heading.group(1) == "##":
                if is_appendix_heading(title):
                    in_appendix = True
                else:
                    m = MODULE_HEADING_RE.match(line)
                    current_module = int(m.group(1)) if m else None
            continue
        if in_appendix:
            current = None
            continue

        case_m = CASE_LINE_RE.match(line)
        if case_m:
            if first_case_line is None:
                first_case_line = idx
            bullet = BULLET_RE.match(line)
            indent = len(bullet.group(1)) if bullet else 0
            current = Case(idx, case_m.group(1), line.strip(), indent, current_module)
            cases.append(current)
            continue

        if current is not None:
            field_m = BULLET_RE.match(line)
            if not field_m:
                continue
            name, rest = split_field(field_m.group(2))
            if name:
                # 同缩进也接受（扁平写法），缩进更深则为常规写法
                current.fields.setdefault(name, rest)
            else:
                # 既不是字段也不是用例的兄弟项：该用例块结束
                current = None

    return cases, first_case_line


def lint(text):
    raw_lines = text.splitlines()
    masked = mask_fences(raw_lines)
    findings = []
    cases, first_case_line = parse_cases(masked)

    if not cases:
        findings.append(Finding(
            "E0", "error", 1,
            "未识别到任何用例（编号须为 TC-{模块号}-{序号}）",
        ))
        return cases, findings, 0

    # E1 导读四件套（用例开始前的标题区）
    preamble_end = first_case_line or len(masked)
    preamble_text = "\n".join(masked[: max(0, preamble_end - 1)])
    missing = [name for name, pat in PREAMBLE_ITEMS if not pat.search(preamble_text)]
    if missing:
        findings.append(Finding(
            "E1", "error", 1,
            "导读四件套缺失：" + "、".join(missing) + "（core/case-format.md 第 1 节）",
        ))

    # E8 一级模块编号重复（导读若也用 `## N.` 编号，正文模块会重号）
    module_lines = {}
    in_appendix = False
    for idx, line in enumerate(masked, start=1):
        h = HEADING_RE.match(line)
        if not h or h.group(1) != "##":
            continue
        if is_appendix_heading(h.group(2).strip()):
            in_appendix = True
            continue
        if in_appendix:
            continue
        m = MODULE_HEADING_RE.match(line)
        if not m:
            continue
        n = int(m.group(1))
        module_lines.setdefault(n, []).append(idx)
    for n, where in sorted(module_lines.items()):
        if len(where) > 1:
            findings.append(Finding(
                "E8", "error", where[1],
                "一级模块编号 `## %d.` 重复（首次出现于第 %d 行）——导读不要占用模块编号，"
                "模块编号从 1 起连续" % (n, where[0]),
            ))

    # E2/E3/E4 编号（E2/E4 按根因归并：一处编号方案错误会命中整批用例，
    # 逐条报 26 行只会淹没信息，反而降低可操作性）
    seen = {}
    untagged = 0
    bad_format = []
    mismatch = {}
    for case in cases:
        canon = TC_CANON_RE.match(case.tc)
        if not canon:
            bad_format.append((case.line, case.tc))
        if case.tc in seen:
            findings.append(Finding(
                "E3", "error", case.line,
                "TC 编号 %s 重复（首次出现于第 %d 行）" % (case.tc, seen[case.tc]),
            ))
        else:
            seen[case.tc] = case.line
        if canon and case.module is not None and int(canon.group(1)) != case.module:
            mismatch.setdefault((case.module, int(canon.group(1))), []).append(case.line)
        if not PRIORITY_RE.search(case.text):
            untagged += 1

    if bad_format:
        samples = "、".join(t for _, t in bad_format[:3])
        findings.append(Finding(
            "E2", "error", bad_format[0][0],
            "%d 条用例的编号不符合 TC-{模块号}-{序号}（如 %s）（core/case-format.md 第 3 节）" % (
                len(bad_format), samples),
        ))
    for (heading_mod, tc_mod), lines in sorted(mismatch.items()):
        findings.append(Finding(
            "E4", "error", lines[0],
            "模块 `## %d.` 下 %d 条用例的编号模块号是 %d，与所在模块不符"
            "（一级模块从 `## 1.` 起连续编号，导读不占编号）" % (heading_mod, len(lines), tc_mod),
        ))

    # E5/E6/E7 + W1/W2/W3 逐条用例
    for case in cases:
        expected_text = case.fields.get("预期结果", "")

        for field_name in FIELD_NAMES:
            value = case.fields.get(field_name, "")
            if not value:
                continue
            placeholders = find_placeholders(value)
            if placeholders:
                findings.append(Finding(
                    "E5", "error", case.line,
                    "%s 用例的「%s」含占位符：%s（core/executability.md 第 4 节）" % (
                        case.tc, field_name, "、".join(sorted(set(placeholders)))),
                ))
            refs = CODE_REF_RE.findall(value)
            if refs:
                findings.append(Finding(
                    "E6", "error", case.line,
                    "%s 用例正文出现代码内部：%s（应隔离到附录，core/case-format.md 第 2 节）" % (
                        case.tc, "、".join(sorted(set(refs)))),
                ))

        if expected_text:
            if UNDETERMINABLE_RE.search(expected_text):
                findings.append(Finding(
                    "W1", "warn", case.line,
                    "%s 预期结果不可判定：「%s」" % (case.tc, _excerpt(expected_text)),
                ))
            if ASYNC_RE.search(expected_text) and not TIME_LIMIT_RE.search(expected_text):
                findings.append(Finding(
                    "W2", "warn", case.line,
                    "%s 异步预期缺判定时限：「%s」" % (case.tc, _excerpt(expected_text)),
                ))
            if ALTERNATIVE_RE.search(expected_text):
                findings.append(Finding(
                    "W3", "warn", case.line,
                    "%s 预期结果非唯一（含「或」，应拆条）：「%s」" % (
                        case.tc, _excerpt(expected_text)),
                ))

    return cases, findings, untagged


def _excerpt(text, limit=40):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def check_required_fields(cases, allow_compact):
    """E7：缺 操作步骤/预期结果（紧凑格式须显式声明）。按缺项归并，避免整批刷屏。"""
    findings = []
    if allow_compact:
        return findings
    buckets = {}
    for case in cases:
        missing = tuple(n for n in ("操作步骤", "预期结果") if not case.fields.get(n))
        if missing:
            buckets.setdefault(missing, []).append(case)
    for missing, group in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        lines = "、".join(str(c.line) for c in group[:3])
        more = "…" if len(group) > 3 else ""
        findings.append(Finding(
            "E7", "error", group[0].line,
            "%d 条用例缺少 %s（行 %s%s）——紧凑格式须显式 --allow-compact"
            "（用户明确要求或信息密度优先时，core/case-format.md 第 4 节）" % (
                len(group), "、".join(missing), lines, more),
        ))
    return findings


def render(path, cases, findings, untagged):
    errors = [f for f in findings if f.severity == "error"]
    warns = [f for f in findings if f.severity == "warn"]
    out = []
    out.append("用例红线检查 — %s" % path)
    out.append("用例 %d 条 / 错误 %d / 告警 %d" % (len(cases), len(errors), len(warns)))
    for f in sorted(findings, key=lambda x: (x.severity != "error", x.line, x.code)):
        out.append("%-3s 行 %-4d %s" % (f.code, f.line, f.message))
    if untagged:
        out.append("W4  共 %d 条用例未标注 [P0]/[P1]/[P2]（默认按 P1 处理）" % untagged)
    verdict = "FAIL（%d 个错误，修复后重跑）" % len(errors) if errors else "PASS（无错误）"
    out.append("判定：%s" % verdict)
    return "\n".join(out) + "\n", len(errors)


def main(argv=None):
    ap = argparse.ArgumentParser(description="用例红线确定性检查（markmap）")
    ap.add_argument("markmap", help="测试用例 markmap 文件")
    ap.add_argument("--allow-compact", action="store_true",
                    help="允许紧凑格式（用户明确要求时）；不改变其他检查")
    ap.add_argument("--json", action="store_true", help="机读输出")
    args = ap.parse_args(argv)

    path = Path(args.markmap)
    if not path.is_file():
        print("错误: 文件不存在 %s" % path, file=sys.stderr)
        return 1
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="gb18030")
        except (UnicodeDecodeError, LookupError):
            print("错误: 无法以 UTF-8/GB18030 解码 %s" % path, file=sys.stderr)
            return 1

    cases, findings, untagged = lint(text)
    findings.extend(check_required_fields(cases, args.allow_compact))
    rendered, error_count = render(str(path), cases, findings, untagged)

    if args.json:
        payload = {
            "file": str(path),
            "cases": len(cases),
            "errors": error_count,
            "warnings": sum(1 for f in findings if f.severity == "warn") + (1 if untagged else 0),
            "untagged": untagged,
            "findings": [f.as_dict() for f in findings],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(rendered, end="")
    return 1 if error_count else 0


if __name__ == "__main__":
    sys.exit(main())
