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
        return make_doc(good_case()) + "\n## 审查记录\n" + record

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
