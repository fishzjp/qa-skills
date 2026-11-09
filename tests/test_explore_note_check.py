#!/usr/bin/env python3
"""探索笔记校验器回归（explore_note_check.py）。

为什么需要：`exploratory-testing` 的六节结构与风险五要素此前只写在 Schema 散文里，
无任何机器门。实测代价（同一任务的两份真实产物）：Round 17 之前 10 条风险 **0 条**带
`verification`，之后 10/10 —— 字段有效但无强制，换模型/旧产物即漏。
本组用例钉住：结构缺失必须报错、条目字段缺失只告警（不阻断）、且**真实产物**能被区分。
"""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skills/core/scripts"))
import explore_note_check as enc  # noqa: E402

GOOD = """# 探索笔记：文档分享与权限

## Charter（本轮探索的使命）
- **目标**：分享后权限会不会漏
- **范围**：分享弹窗、链接访问、邀请与通知
- **时长 / 停点**：时间盒 2 小时；停点 = 风险清单满 10 条

## 系统理解（探索中修正）
- 四种链接范围，默认「组织内」；文档 id 级访问控制

## 风险清单（每条带证据标注）
- **R1**｜权限收窄后存在缓存窗口期｜level: Critical｜evidence: E3 · 观察 #3 + 截图｜verification: 单次样本｜confidence: high｜status: hypothesis

## 测试想法（后续转化为正式用例的候选）
- 关闭分享的缓存窗口对称验证 → 建议归属：可直接转用例

## 发现的 Bug（现象 + 复现步骤 + 证据；未定性，标 Hypothesis）
- B1｜@ 提及可让非分享对象读到全文｜Hypothesis，待 Owner 定性

## 未解之谜（需要用户/开发澄清的问题）
- Q1：范围变更是否写审计日志？
"""


class ExploreNoteCheckTests(unittest.TestCase):
    def _codes(self, text):
        errors, warnings = enc.check(text)
        return ([e.split(" ")[0] for e in errors], [w.split(" ")[0] for w in warnings])

    def test_good_note_passes(self):
        self.assertEqual(self._codes(GOOD), ([], []))

    def test_missing_section_is_error(self):
        bad = GOOD.replace("## 未解之谜（需要用户/开发澄清的问题）\n- Q1：范围变更是否写审计日志？\n", "")
        errors, _ = self._codes(bad)
        self.assertIn("E1", errors)

    def test_charter_missing_stop_point_is_error(self):
        bad = GOOD.replace("- **时长 / 停点**：时间盒 2 小时；停点 = 风险清单满 10 条\n", "")
        errors, _ = self._codes(bad)
        self.assertIn("E2", errors)

    def test_risks_without_any_level_is_error(self):
        """整份笔记没有任何 level = 等于未评级（不是单条遗漏，是系统性缺失）。"""
        bad = GOOD.replace("｜level: Critical", "")
        errors, _ = self._codes(bad)
        self.assertIn("E3", errors)

    def test_missing_verification_is_warning_only(self):
        """缺 verification 是声明完整性，告警不阻断（门级判据同 W5/V6 的先例）。"""
        bad = GOOD.replace("｜verification: 单次样本", "")
        errors, warnings = self._codes(bad)
        self.assertEqual(errors, [])
        self.assertIn("W1", warnings)

    def test_missing_confidence_or_status_is_warning(self):
        bad = GOOD.replace("｜confidence: high", "").replace("｜status: hypothesis", "")
        _, warnings = self._codes(bad)
        self.assertIn("W2", warnings)

    def test_evidence_without_level_is_warning(self):
        bad = GOOD.replace("E3 · 观察 #3 + 截图", "观察 #3 + 截图")
        _, warnings = self._codes(bad)
        self.assertIn("W3", warnings)

    def test_ideas_without_owner_is_warning(self):
        bad = GOOD.replace(" → 建议归属：可直接转用例", "")
        _, warnings = self._codes(bad)
        self.assertIn("W4", warnings)

    def test_bug_without_hypothesis_mark_is_warning(self):
        bad = GOOD.replace("｜Hypothesis，待 Owner 定性", "｜已确认漏洞")
        _, warnings = self._codes(bad)
        self.assertIn("W5", warnings)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as td:
            ok = Path(td) / "ok.md"; ok.write_text(GOOD, encoding="utf-8")
            self.assertEqual(enc.main([str(ok)]), 0)
            bad = Path(td) / "bad.md"; bad.write_text("# 空笔记\n", encoding="utf-8")
            self.assertEqual(enc.main([str(bad)]), 1)


if __name__ == "__main__":
    unittest.main()
