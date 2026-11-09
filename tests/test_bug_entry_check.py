#!/usr/bin/env python3
"""Bug 条目校验器回归（bug_entry_check.py）。

为什么需要：`core/report-template.md` §3 规定 Bug 条目 13 字段（8 基础 + 5 扩展），
`bug-analysis` 另有硬纪律（根因标 status Inference/Verified、Severity 用 S 系、证据标 E0–E4），
此前无任何机器校验。本组用例钉住：真实产物形态必须通过、每类缺陷必须被抓。
"""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skills/core/scripts"))
import bug_entry_check as bec  # noqa: E402

GOOD = """# Bug 条目 — 2026-11-09

### BUG-2077 行号提示错位

- **严重程度**: S2（体验问题：不阻断，仅提示偏移）
- **状态**: 新建
- **发现方式**: 手动执行
- **复现步骤**:
  1. 准备 CSV
  2. 导入
- **预期行为**: 提示第 3 行
- **实际行为**: 提示第 4 行
- **证据**: E0 用户报告 / E2 代码（`importer.py:38`）
- **环境**: staging-2
- **根因分析**:（根因：`importer.py:38` 的 `+1`）
  - **Root Cause**（status: Inference｜evidence: E2 `importer.py:38`）：多余 +1 导致偏移
  - **排除项**（evidence: E2）：解析逻辑本身正确
- **影响范围**:（五面）
  - **功能面**：所有校验失败行偏移 +1
- **Severity 依据**: 仅提示偏移，无数据错误 → S2
- **修复建议**（方向，不写补丁）:
  1. 统一行号口径
- **回归建议**:
  - 修复验证用例 TC-08-01
"""


class BugEntryCheckTests(unittest.TestCase):
    def test_real_world_shape_passes(self):
        self.assertEqual(bec.check(GOOD)[0], [])

    def test_missing_field_is_error(self):
        text = GOOD.replace("- **回归建议**:\n  - 修复验证用例 TC-08-01\n", "")
        self.assertTrue(any(e.startswith("E1") and "回归建议" in e for e in bec.check(text)[0]))

    def test_p_level_severity_is_error(self):
        text = GOOD.replace("S2（体验问题", "P2（体验问题")
        self.assertTrue(any(e.startswith("E2") for e in bec.check(text)[0]))

    def test_missing_root_cause_status_is_error(self):
        text = GOOD.replace("status: Inference｜", "")
        self.assertTrue(any(e.startswith("E3") for e in bec.check(text)[0]))

    def test_prose_mention_of_verified_does_not_count(self):
        """字段别处写"可升级为 Verified"不能替代 Root Cause 行上的标注。"""
        text = GOOD.replace("status: Inference｜", "").replace(
            "多余 +1 导致偏移", "多余 +1 导致偏移（补齐运行证据后可升级为 Verified）")
        self.assertTrue(any(e.startswith("E3") for e in bec.check(text)[0]))

    def test_missing_file_line_is_warning(self):
        text = GOOD.replace("`importer.py:38`", "相关实现").replace("importer.py:38`", "实现")
        self.assertIn("W2", [w.split(" ")[0] for w in bec.check(text)[1]])

    def test_patch_style_fix_is_warning(self):
        text = GOOD.replace("  1. 统一行号口径",
                            "```python\ndef fix():\n    return 1\n```")
        self.assertIn("W3", [w.split(" ")[0] for w in bec.check(text)[1]])

    def test_empty_regression_advice_is_warning(self):
        text = GOOD.replace("  - 修复验证用例 TC-08-01", "  TODO")
        self.assertIn("W4", [w.split(" ")[0] for w in bec.check(text)[1]])

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as td:
            ok = Path(td) / "ok.md"; ok.write_text(GOOD, encoding="utf-8")
            self.assertEqual(bec.main([str(ok)]), 0)
            bad = Path(td) / "bad.md"; bad.write_text("# 空\n", encoding="utf-8")
            self.assertEqual(bec.main([str(bad)]), 1)


if __name__ == "__main__":
    unittest.main()
