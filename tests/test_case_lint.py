#!/usr/bin/env python3
"""case_lint.py 的回归测试（用例红线确定性闸门）。

不依赖 eval/：公开检出与维护者本地均可跑。

测试锚定的都是"散文规则 vs 机器闸门"的分歧点：
- 正例必须零错误（否则闸门不可用于定稿，Agent 只能绕过它）
- 每条红线各有正反例（只测反例 = 假阳性无人发现）
- JSON/HTML 标签不得被误判为占位符（API 用例请求体是高频误报源）
- 真实 On/Off 产出回放：框架产出应过闸门，无框架产出应被判红（判别力证据）
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skills" / "core" / "scripts"))

import case_lint  # noqa: E402

EXAMPLES = REPO / "examples"

PREAMBLE = """## 导读

### 功能简介与角色表
运营：创建优惠券。

### 环境与账号表
| 角色 | 账号 |
|------|------|
| 运营 | ops001 |

### 术语表
| 术语 | 含义 |
|------|------|
| 券 | 优惠券 |

### 图例
[P0] 冒烟
"""


def make_doc(cases, preamble=PREAMBLE, module_title="## 1. 优惠券创建"):
    return "# 测试用例\n\n" + preamble + "\n" + module_title + "\n\n" + cases


def good_case(tc="TC-01-01", name="创建成功", extra=""):
    return (
        "- **%s %s** [P0]\n"
        "  - 操作步骤: 1. 填写券名称\"测试券\" 2. 点击\"提交\"\n"
        "  - 预期结果: 列表新增该券%s\n" % (tc, name, extra)
    )


def run_lint(text, allow_compact=False):
    cases, findings, untagged = case_lint.lint(text)
    findings.extend(case_lint.check_required_fields(cases, allow_compact))
    return cases, findings


def codes(findings, severity=None):
    return [f.code for f in findings if severity is None or f.severity == severity]


class PositiveCaseTests(unittest.TestCase):
    def test_valid_document_has_no_errors(self):
        cases, findings = run_lint(make_doc(good_case()))
        self.assertEqual(len(cases), 1)
        self.assertEqual(codes(findings, "error"), [])

    def test_dev_collab_five_section_form_passes(self):
        case = (
            "- **TC-01-01 定时任务清理过期券** [P1]\n"
            "  - 前置条件: 已存在一张过期待清理券\n"
            "  - 操作步骤（请开发执行）: 1. 触发清理任务\n"
            "  - 预期结果（请开发反馈）: 该券状态为已失效\n"
            "  - 验证方式: 开发查库反馈状态字段\n"
        )
        _, findings = run_lint(make_doc(case))
        self.assertEqual(codes(findings, "error"), [])


class StructuralRuleTests(unittest.TestCase):
    def test_missing_preamble_item_is_error(self):
        _, findings = run_lint(make_doc(good_case(), preamble=PREAMBLE.replace(
            "### 图例\n[P0] 冒烟\n", "")))
        self.assertIn("E1", codes(findings, "error"))

    def test_bad_tc_format_is_error(self):
        _, findings = run_lint(make_doc(good_case(tc="TC-NAME-001")))
        self.assertIn("E2", codes(findings, "error"))

    def test_duplicate_tc_is_error(self):
        _, findings = run_lint(make_doc(good_case() + good_case()))
        self.assertIn("E3", codes(findings, "error"))

    def test_module_mismatch_is_error(self):
        doc = make_doc(good_case(tc="TC-02-01"))
        _, findings = run_lint(doc)
        self.assertIn("E4", codes(findings, "error"))

    def test_no_cases_is_error_not_green(self):
        doc = "# 测试用例\n\n## 导读\n\n### 术语表\n\n## 1. 模块\n\n没有用例\n"
        _, findings = run_lint(doc)
        self.assertIn("E0", codes(findings, "error"))

    def test_duplicate_module_number_is_error(self):
        """导读占用 `## 1.` 后正文模块又从 1 起编号——A/B 实测产出出现过的真实形态。"""
        doc = make_doc(good_case(), preamble=PREAMBLE + "\n## 1. 导读续\n", module_title="## 1. 优惠券创建")
        _, findings = run_lint(doc)
        self.assertIn("E8", codes(findings, "error"))

    def test_contiguous_module_numbers_pass(self):
        doc = (make_doc(good_case()) +
               "\n## 2. 第二个模块\n\n" + good_case(tc="TC-02-01"))
        _, findings = run_lint(doc)
        self.assertNotIn("E8", codes(findings, "error"))


class ExecutabilityRuleTests(unittest.TestCase):
    def test_brace_placeholder_is_error(self):
        case = good_case().replace('"测试券"', "{券名称}")
        _, findings = run_lint(make_doc(case))
        self.assertIn("E5", codes(findings, "error"))

    def test_angle_placeholder_is_error(self):
        case = good_case().replace('"测试券"', "<活动编号>")
        _, findings = run_lint(make_doc(case))
        self.assertIn("E5", codes(findings, "error"))

    def test_mou_placeholder_is_error(self):
        case = good_case().replace('"测试券"', "某数据")
        _, findings = run_lint(make_doc(case))
        self.assertIn("E5", codes(findings, "error"))

    def test_json_body_is_not_placeholder(self):
        case = (
            "- **TC-01-01 创建订单** [P0]\n"
            "  - 操作步骤: 1. POST /orders 请求体 {\"amount\": 20, \"code\": 0} 2. 查看响应\n"
            "  - 预期结果: 返回 201 且响应体 {\"code\": 0, \"id\": 1001}\n"
        )
        _, findings = run_lint(make_doc(case))
        self.assertNotIn("E5", codes(findings, "error"))

    def test_html_tag_is_not_placeholder(self):
        case = good_case().replace('"测试券"', '"<div>测试券</div>"')
        _, findings = run_lint(make_doc(case))
        self.assertNotIn("E5", codes(findings, "error"))

    def test_code_ref_in_body_is_error(self):
        case = good_case(extra="，见 coupon_service.py:124")
        _, findings = run_lint(make_doc(case))
        self.assertIn("E6", codes(findings, "error"))

    def test_code_ref_in_appendix_is_exempt(self):
        doc = make_doc(good_case()) + "\n## 附录：代码证据清单\n\n| TC | 证据 |\n|----|------|\n| TC-01-01 | coupon_service.py:124 |\n"
        _, findings = run_lint(doc)
        self.assertNotIn("E6", codes(findings, "error"))

    def test_missing_expected_is_error(self):
        case = (
            "- **TC-01-01 创建成功** [P0]\n"
            "  - 操作步骤: 1. 填写券名称\"测试券\" 2. 点击\"提交\"\n"
        )
        _, findings = run_lint(make_doc(case))
        self.assertIn("E7", codes(findings, "error"))

    def test_compact_form_allowed_when_declared(self):
        case = "- TC-01-01 券名称为空时提交按钮置灰 [P0]\n"
        _, findings = run_lint(make_doc(case), allow_compact=True)
        self.assertNotIn("E7", codes(findings, "error"))

    def test_compact_form_rejected_by_default(self):
        case = "- TC-01-01 券名称为空时提交按钮置灰 [P0]\n"
        _, findings = run_lint(make_doc(case))
        self.assertIn("E7", codes(findings, "error"))

    def test_flat_field_form_is_recognised(self):
        """字段与用例同缩进（弱模型常见扁平写法）不得误报 E7。"""
        case = (
            "- **TC-01-01 创建成功** [P0]\n"
            "- 操作步骤: 1. 点击\"提交\"\n"
            "- 预期结果: 列表新增该券\n"
        )
        _, findings = run_lint(make_doc(case))
        self.assertNotIn("E7", codes(findings, "error"))

    def test_bold_field_label_is_recognised(self):
        """`- **操作步骤**:` 加粗标签与全角冒号不得误报 E7。"""
        case = (
            "- **TC-01-01 创建成功** [P0]\n"
            "  - **操作步骤**：1. 点击\"提交\"\n"
            "  - **预期结果**：列表新增该券\n"
        )
        _, findings = run_lint(make_doc(case))
        self.assertNotIn("E7", codes(findings, "error"))


class WarningTests(unittest.TestCase):
    def test_undeterminable_expected_warns(self):
        case = good_case(extra="，校验是否正确处理")
        _, findings = run_lint(make_doc(case))
        self.assertIn("W1", codes(findings, "warn"))

    def test_async_without_time_limit_warns(self):
        case = good_case(extra="，状态自动变为已结束")
        _, findings = run_lint(make_doc(case))
        self.assertIn("W2", codes(findings, "warn"))

    def test_async_with_time_limit_is_clean(self):
        case = good_case(extra="，到达结束时间后 1 小时内自动变为已结束")
        _, findings = run_lint(make_doc(case))
        self.assertNotIn("W2", codes(findings, "warn"))

    def test_alternative_expected_warns(self):
        case = good_case(extra="，提交按钮置灰或提交后拦截")
        _, findings = run_lint(make_doc(case))
        self.assertIn("W3", codes(findings, "warn"))

    def test_untagged_cases_are_counted(self):
        case = (
            "- **TC-01-01 创建成功**\n"
            "  - 操作步骤: 1. 点击\"提交\"\n"
            "  - 预期结果: 列表新增该券\n"
        )
        _, _, untagged = case_lint.lint(make_doc(case))
        self.assertEqual(untagged, 1)


class CliContractTests(unittest.TestCase):
    def _run(self, argv):
        """跑 CLI 并吞掉 stdout，避免污染 check.sh / CI 日志（用例要的是退出码）。"""
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = case_lint.main(argv)
        return code, buf.getvalue()

    def _write(self, td, text):
        path = Path(td) / "case.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_exit_code_zero_on_pass(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write(td, make_doc(good_case()))
            self.assertEqual(self._run([str(path)])[0], 0)

    def test_exit_code_one_on_error(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write(td, make_doc(good_case(tc="TC-NAME-001")))
            self.assertEqual(self._run([str(path)])[0], 1)

    def test_missing_file_is_error(self):
        self.assertEqual(self._run(["/nonexistent/case.md"])[0], 1)

    def test_gbk_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "case.md"
            path.write_bytes(make_doc(good_case()).encode("gb18030"))
            self.assertEqual(self._run([str(path)])[0], 0)

    def test_json_output_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write(td, make_doc(good_case(tc="TC-NAME-001")))
            code, out = self._run([str(path), "--json"])
            payload = json.loads(out)
            self.assertEqual(code, 1)
            self.assertEqual(payload["errors"], 1)
            self.assertEqual(payload["findings"][0]["code"], "E2")


class BookkeepingTests(unittest.TestCase):
    """E9：审查记录账目必须与实际一致（模型产出实测 8/8 不符，人写示例精确）。"""

    def _doc(self, record):
        return make_doc(good_case()) + "\n## 审查记录（test-case-review 2026-11-09）\n" + record

    def test_matching_counts_pass(self):
        doc = self._doc("- 审查前：1 条用例，1 个模块\n- 审查后：1 条用例，1 个模块\n")
        _, findings = run_lint(doc)
        self.assertNotIn("E9", codes(findings, "error"))

    def test_after_count_mismatch_is_error(self):
        doc = self._doc("- 审查前：5 条用例，1 个模块\n- 审查后：5 条用例，1 个模块\n")
        _, findings = run_lint(doc)
        self.assertIn("E9", codes(findings, "error"))

    def test_module_count_mismatch_is_error(self):
        doc = self._doc("- 审查后：1 条用例，4 个模块\n")
        _, findings = run_lint(doc)
        self.assertIn("E9", codes(findings, "error"))

    def test_arithmetic_mismatch_is_error(self):
        doc = self._doc("- 审查前：3 条用例，1 个模块\n- 新增：1 条\n- 审查后：1 条用例，1 个模块\n")
        _, findings = run_lint(doc)
        self.assertIn("E9", codes(findings, "error"))

    def test_no_review_record_skips_check(self):
        _, findings = run_lint(make_doc(good_case()))
        self.assertNotIn("E9", codes(findings, "error"))

    def test_two_records_only_last_is_checked(self):
        """写时自审 + 独立审查两段共存时，前一段的旧数字不算错。"""
        doc = (make_doc(good_case())
               + "\n## 审查记录\n- 审查后：1 条用例，1 个模块\n"
               + "\n## 审查记录（test-case-review 2026-11-08）\n- 审查后：1 条用例，1 个模块\n")
        _, findings = run_lint(doc)
        self.assertNotIn("E9", codes(findings, "error"))


class RealCorpusDiscriminationTests(unittest.TestCase):
    """examples/ 是真实评测产出：框架产出应过闸门，无框架产出应被判红。"""

    def _errors(self, name):
        path = EXAMPLES / name
        self.assertTrue(path.is_file(), "%s 缺失" % name)
        cases, findings, _ = case_lint.lint(path.read_text(encoding="utf-8"))
        findings.extend(case_lint.check_required_fields(cases, False))
        return [f for f in findings if f.severity == "error"]

    def test_with_skills_output_passes(self):
        self.assertEqual(self._errors("test-cases_with-skills.md"), [])

    def test_without_skills_output_is_rejected(self):
        self.assertTrue(self._errors("test-cases_without-skills.md"))


if __name__ == "__main__":
    unittest.main()


class PriorityConcentrationTests(unittest.TestCase):
    """W5：P0（冒烟）占比过高的告警（2026-11-09）。

    触发依据是实测：审查任务产物出现 8/18 = 44% P0（原违规含"P0 泛滥"未被审出），
    而 204 份真实产物 P0 占比中位 15%、p95 26%、最高 40%。故取 35% 且用例 ≥6 条，
    只命中约 1.5% 样本——告警级（不阻断），要求逐条过 P0 自检。
    """

    def _cases(self, p0, p1, p2=0):
        lines = ["# 用例", "## 1. 模块", ""]
        n = 1
        for _ in range(p0):
            lines.append(f"- TC-01-{n:02d} 用例 {n} [P0]")
            lines.append("  - 操作步骤: 1. 打开页面 2. 点击按钮")
            lines.append("  - 预期结果: 显示成功提示，页面停留 1 秒内可见结果")
            n += 1
        for _ in range(p1):
            lines.append(f"- TC-01-{n:02d} 用例 {n} [P1]")
            lines.append("  - 操作步骤: 1. 打开页面 2. 点击按钮")
            lines.append("  - 预期结果: 显示成功提示，页面停留 1 秒内可见结果")
            n += 1
        for _ in range(p2):
            lines.append(f"- TC-01-{n:02d} 用例 {n} [P2]")
            lines.append("  - 操作步骤: 1. 打开页面")
            lines.append("  - 预期结果: 无变化")
            n += 1
        return "\n".join(lines) + "\n"

    def _warns(self, text):
        out, _ = case_lint.render("x.md", case_lint.lint(text)[0],
                                  case_lint.lint(text)[1], case_lint.lint(text)[2])
        return "W5" in out

    def test_high_p0_ratio_warns(self):
        self.assertTrue(self._warns(self._cases(p0=8, p1=9, p2=1)))  # 44%

    def test_normal_ratio_does_not_warn(self):
        self.assertFalse(self._warns(self._cases(p0=3, p1=12, p2=3)))  # 17%，接近实测中位

    def test_small_suite_not_warned(self):
        """用例 <6 条时比例失真（3/5=60% 也可能是合理冒烟集），不告警。"""
        self.assertFalse(self._warns(self._cases(p0=3, p1=2)))

    def test_threshold_boundary(self):
        self.assertTrue(self._warns(self._cases(p0=7, p1=13)))    # 35%
        self.assertFalse(self._warns(self._cases(p0=6, p1=14)))   # 30%


class AsyncTimeLimitNoiseTests(unittest.TestCase):
    """W2 误报收敛（2026-11-09）。

    实测 255 条 W2 中约 32% 是误报，两类清晰可判：
    ① 否定式异步——「不会自动变为已结束」「无内存溢出或超时错误」：没有事件可限时；
    ② 钟点时间——「凌晨 2:00 自动启动」：锚点是钟点而非时长，仍属可判定。
    修复后 255 → 184（-28%），原始误报清零；真正的"缺时限"仍照报。
    """

    def _w2(self, expected):
        text = ("# 用例\n## 1. 模块\n\n- TC-01-01 用例 [P1]\n"
                "  - 操作步骤: 1. 打开页面\n"
                f"  - 预期结果: {expected}\n")
        findings = case_lint.lint(text)[1]
        return any(f.code == "W2" for f in findings)

    def test_negated_async_not_flagged(self):
        self.assertFalse(self._w2("券状态仍为待发布，不会自动变为已结束"))

    def test_negation_enumeration_not_flagged(self):
        self.assertFalse(self._w2("任务成功完成，无内存溢出或超时错误"))

    def test_parenthetical_note_not_flagged(self):
        """括号内是补充说明，不是预期本身。"""
        self.assertFalse(self._w2("状态保持不变（自动结束仅对已发布的券生效）"))

    def test_clock_time_is_valid_anchor(self):
        self.assertFalse(self._w2("任务在凌晨 2:00 自动启动执行"))
        self.assertFalse(self._w2("任务在 2026-08-20 02:00 自动触发"))

    def test_genuine_missing_limit_still_flagged(self):
        self.assertTrue(self._w2("任务自动触发执行，日志中出现启动记录"))

    def test_duration_still_accepted(self):
        self.assertFalse(self._w2("任务自动触发，30 分钟内完成"))


class DevinCaseLintRegressionTests(unittest.TestCase):
    """case_lint 的两个误判（Devin 评审 PR #13 指出，2026-11-09 修复）。"""

    def _doc(self, review, n=6, title="用例"):
        s = "# 用例\n## 1. 模块1\n"
        for i in range(1, n + 1):
            s += (f"- TC-01-{i:02d} {title}{i} [P1]\n"
                  "  - 操作步骤: 1. 打开页面\n  - 预期结果: 显示成功，1 秒内可见\n")
        return s + f"\n## 审查记录（test-case-review 2026-11-09）\n\n{review}\n"

    def test_deletion_arithmetic_accepted(self):
        """审查允许删除/合并冗余用例：审查前 − 删除 + 新增 == 审查后 应通过。"""
        e9 = [f for f in case_lint.lint(self._doc(
            "审查前：8 条，新增：0 条，删除：2 条，审查后：6 条", n=6))[1] if f.code == "E9"]
        self.assertEqual(e9, [])

    def test_wrong_deletion_arithmetic_still_rejected(self):
        e9 = [f for f in case_lint.lint(self._doc(
            "审查前：8 条，新增：0 条，删除：1 条，审查后：6 条", n=6))[1] if f.code == "E9"]
        self.assertTrue(e9)

    def test_placeholder_in_case_title_rejected(self):
        """标题里的占位符同样是未完成正文，E5 必须拦（此前只扫字段值）。"""
        e5 = [f for f in case_lint.lint(self._doc(
            "审查前：6 条，审查后：6 条", n=6, title="用{手机号}登录"))[1] if f.code == "E5"]
        self.assertTrue(e5)
        self.assertIn("标题", e5[0].message)


class ReviewAttributionTests(unittest.TestCase):
    """审查记录节标题须含 test-case-review 落款（qa 阶段 4 判据在 case_lint 层前置拦截）。

    qa 编排层阶段 4 完成判据：用例文件末尾含「test-case-review 落款」的审查记录节。
    此前 case_lint 只查账目（E9 算术），不查落款——没有 test-case-review 标识的
    自审节也能过闸，编排层才（可能）发现，续跑时静默跳过独立审查。
    """

    def _doc(self, review_heading):
        base = "# 用例\n## 1. 模块\n\n"
        for i in range(1, 7):
            base += (f"- TC-01-{i:02d} 用例{i} [P1]\n"
                     "  - 操作步骤: 1. 打开页面\n  - 预期结果: 显示成功，1 秒内可见\n")
        return base + f"\n## {review_heading}\n\n- 审查前：6 条，审查后：6 条\n"

    def test_with_tc_review_attribution_passes(self):
        e9 = [f for f in case_lint.lint(self._doc(
            "审查记录（test-case-review 2026-11-09）"))[1] if f.code == "E9"]
        self.assertFalse(any("test-case-review 落款" in f.message for f in e9),
                         "有落款不应报缺落款")

    def test_without_tc_review_attribution_flagged(self):
        e9 = [f for f in case_lint.lint(self._doc(
            "审查记录"))[1] if f.code == "E9"]
        self.assertTrue(any("test-case-review 落款" in f.message for f in e9),
                        "无落款应被拦截")

    def test_generic_review_heading_flagged(self):
        e9 = [f for f in case_lint.lint(self._doc(
            "审查记录（自查）"))[1] if f.code == "E9"]
        self.assertTrue(any("test-case-review 落款" in f.message for f in e9),
                        "自查落款不足以标识独立审查")
