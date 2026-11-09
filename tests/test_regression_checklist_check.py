#!/usr/bin/env python3
"""回归清单校验器回归（regression_checklist_check.py）。

为什么需要：`regression-testing/SKILL.md` 定义了回归清单五节结构
（必须回归 P0 / 建议回归 P1 / 可选回归 P2 / 影响不明 / 无影响确认），
且 Round 29 要求排除须给模块级/字段级理由，此前**没有任何脚本校验**。
"""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skills/core/scripts"))
import regression_checklist_check as rcc  # noqa: E402

GOOD = """# 回归清单 — 2026-11-09

- 变更基线：feature/coupon-fee...main（2 commits，2 文件）

## 必须回归（P0）
| 用例 | 依据 |
|------|------|
| TC-01-01 | code_refs 直连 `coupon/service.py:122` |
| TC-01-02 | code_refs 直连 `common/validator.py:18`，上限收紧致边界失效 |

## 建议回归（P1）
| 用例 | 依据 |
|------|------|
| TC-02-02 | 共享校验器消费方（编辑路径），上限收紧须同样生效 |

## 可选回归（P2）
（无符合"公共组件改动但消费关系疏远"的候选，已注明）

## 影响不明（建议人工判断）
- `edit.py:40` 是否允许修改面额未知，待人工确认（evidence: E2）

## 无影响确认（显式排除）
| 用例 | 排除理由 |
|------|---------|
| TC-02-01 | 字段级过滤：调整发放总量与面额字段无关 |
| TC-04-01 | 模块级：发布模块无改动无共享路径，R1 成因面未触及 |
"""


class RegressionChecklistCheckTests(unittest.TestCase):
    def test_good_checklist_passes(self):
        errors, warnings = rcc.check(GOOD)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_missing_tier_is_error(self):
        bad = GOOD.replace("## 可选回归（P2）\n（无符合\"公共组件改动但消费关系疏远\"的候选，已注明）\n", "")
        errors, _ = rcc.check(bad)
        self.assertTrue(any(e.startswith("E1") and "可选回归" in e for e in errors), errors)

    def test_missing_baseline_is_error(self):
        bad = GOOD.replace("- 变更基线：feature/coupon-fee...main（2 commits，2 文件）\n", "")
        errors, _ = rcc.check(bad)
        self.assertTrue(any(e.startswith("E2") for e in errors), errors)

    def test_exclusion_without_rationale_is_warning(self):
        bad = GOOD.replace("| TC-02-01 | 字段级过滤：调整发放总量与面额字段无关 |",
                           "| TC-02-01 | 排除 |")
        _, warnings = rcc.check(bad)
        self.assertIn("W1", [w.split(" ")[0] for w in warnings], warnings)

    def test_p0_without_rationale_is_warning(self):
        bad = GOOD.replace("| TC-01-01 | code_refs 直连 `coupon/service.py:122` |",
                           "| TC-01-01 | 纳入 |")
        _, warnings = rcc.check(bad)
        self.assertIn("W2", [w.split(" ")[0] for w in warnings], warnings)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as td:
            ok = Path(td) / "ok.md"; ok.write_text(GOOD, encoding="utf-8")
            self.assertEqual(rcc.main([str(ok)]), 0)
            bad = Path(td) / "bad.md"; bad.write_text("# 空\n", encoding="utf-8")
            self.assertEqual(rcc.main([str(bad)]), 1)


if __name__ == "__main__":
    unittest.main()
