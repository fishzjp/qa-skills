#!/usr/bin/env python3
"""报告机读摘要校验器回归（report_meta_check.py）。

为什么需要：`core/report-template.md` 第 7 节要求报告末节追加固定 yaml「机读摘要」，
并声明"流水线聚合与质量门禁只解析此节"；生产方有四个（qa 收尾 / api-testing /
automated-e2e-testing / test-reliability）。此前无任何脚本校验该块——写坏时人读内容照常、
仓库侧无红灯，聚合侧才炸。本组用例钉住五类失败形态，全部正反例实测。
"""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skills/core/scripts"))
import report_meta_check as rmc  # noqa: E402

GOOD = """# 测试报告 — 2026-11-09

```yaml
meta:
  project: 优惠券
  date: 2026-11-09
  source_run: pr-smoke
summary:
  total: 10
  passed: 9
  failed: 1
  blocked: 0
triage_distribution:
  A: 1
  B1: 0
  B2: 0
  C: 0
  D: 0
  U: 0
exit_code_hint: 1
open_items: 2
bugs:
  - {id: BUG-001, severity: S1, status: 新建}
```
"""


class ReportMetaCheckTests(unittest.TestCase):
    def _run(self, text):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "测试报告.md"
            p.write_text(text, encoding="utf-8")
            return rmc.main([str(p)]), rmc.check(text)

    def test_good_block_passes(self):
        code, (errors, warnings) = self._run(GOOD)
        self.assertEqual(errors, [])
        self.assertEqual(code, 0)

    def test_missing_block_fails(self):
        code, (errors, _) = self._run("# 报告\n\n正文没有机读摘要\n")
        self.assertEqual(code, 1)
        self.assertTrue(any(e.startswith("E1") for e in errors), errors)

    def test_duplicate_blocks_fail(self):
        block = GOOD[GOOD.index("```yaml"):]
        code, (errors, _) = self._run(GOOD + "\n" + block)
        self.assertEqual(code, 1)
        self.assertTrue(any("出现 2 个" in e for e in errors), errors)

    def test_missing_required_field_fails(self):
        code, (errors, _) = self._run(GOOD.replace("  total: 10\n", ""))
        self.assertEqual(code, 1)
        self.assertTrue(any("summary.total" in e for e in errors), errors)

    def test_enum_violations_fail(self):
        text = GOOD.replace("source_run: pr-smoke", "source_run: smoke") \
                   .replace("exit_code_hint: 1", "exit_code_hint: ok")
        code, (errors, _) = self._run(text)
        self.assertEqual(code, 1)
        self.assertTrue(any("source_run" in e for e in errors), errors)
        self.assertTrue(any("exit_code_hint" in e for e in errors), errors)

    def test_triage_unknown_key_fails(self):
        code, (errors, _) = self._run(GOOD.replace("  B1: 0", "  E: 0"))
        self.assertEqual(code, 1)
        self.assertTrue(any("triage_distribution" in e for e in errors), errors)

    def test_count_inconsistent_fails(self):
        code, (errors, _) = self._run(GOOD.replace("  passed: 9", "  passed: 99"))
        self.assertEqual(code, 1)
        self.assertTrue(any("大于 total" in e for e in errors), errors)

    def test_partial_execution_warns_not_fails(self):
        """已执行 < total 属正常（有未执行用例），只告警不阻断。"""
        code, (errors, warnings) = self._run(GOOD.replace("  passed: 9", "  passed: 5")
                                                  .replace("  failed: 1", "  failed: 0"))
        self.assertEqual(errors, [])
        self.assertEqual(code, 0)
        self.assertTrue(any(w.startswith("W1") for w in warnings), warnings)

    def test_bug_entry_fields_checked(self):
        text = GOOD.replace("severity: S1", "severity: P0").replace("status: 新建", "status: 待定")
        code, (errors, _) = self._run(text)
        self.assertEqual(code, 1)
        self.assertTrue(any("severity='P0'" in e for e in errors), errors)
        self.assertTrue(any("status='待定'" in e for e in errors), errors)


    def test_trailing_comments_do_not_break_parsing(self):
        """模板与真实产物普遍带行尾注释，Agent 会照抄——注释不得导致误报。

        （本轮实测发现：`summary:  # ← §2 执行统计` 让父键行不匹配、`0  # ← 对照…`
        被整串当成枚举值，结果对**合规**产物误报。真实发现，非构造。）
        """
        text = GOOD.replace("summary:", "summary:            # ← §2 执行统计") \
                   .replace("exit_code_hint: 1", "exit_code_hint: 1   # ← 对照约定三") \
                   .replace("  project: 优惠券", "  project: 优惠券   # 项目名")
        code, (errors, _) = self._run(text)
        self.assertEqual(errors, [])
        self.assertEqual(code, 0)

    def test_placeholder_values_report_as_unreplaced(self):
        """照抄模板占位符时，报错须指明"未替换"而不是含糊的"不是整数"。"""
        text = GOOD.replace("  total: 10", "  total: {总数}")
        code, (errors, _) = self._run(text)
        self.assertEqual(code, 1)
        self.assertTrue(any("仍是模板占位符" in e or "占位符" in e for e in errors), errors)

if __name__ == "__main__":
    unittest.main()
