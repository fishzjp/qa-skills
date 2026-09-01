#!/usr/bin/env python3
"""随产品分发脚本的回归测试（validate_schema / scan_signals / validate_skills）。

不依赖 eval/（本地评测链路），公开检出与维护者本地均可跑：
    python3 -m unittest discover -s tests -p "test_product_scripts.py" -v

测试锚定的都是已发生过或高价值的失败形态：
- 零用例骗绿（顶层 key 拼错时校验器曾全绿放行）
- 路径基准约定（references/ 内相对路径曾出现两种互斥基准并存）
- YAML 转义 sanitize 的顺序硬约束（截断落在转义对中间会产生非法 YAML）
- GBK 输入（中文 Windows 环境高发）
"""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skills" / "core" / "scripts"))
sys.path.insert(0, str(REPO / "scripts"))

import scan_signals       # noqa: E402
import validate_schema    # noqa: E402
import validate_skills    # noqa: E402

GOOD_CASES_YAML = """test_cases:
  - id: TC-01-01
    title: 正常用例
    priority: P0
    type: functional
    steps:
      - 打开页面
    expected:
      - 显示正常
"""
MIN_MARKMAP = "## 模块\n- TC-01-01 测试\n"


class ValidateSchemaCliTests(unittest.TestCase):
    """validate_schema.py main() 的退出码契约（agent 按退出码判定门禁）。"""

    def _run(self, files):
        return validate_schema.main([str(p) for p in files])

    def test_empty_cases_fails_not_green(self):
        """YAML 合法但零用例（顶层 key 拼错形态）必须 FAIL，防骗绿。"""
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            md, yml = td / "case.md", td / "s.yaml"
            md.write_text(MIN_MARKMAP, encoding="utf-8")
            yml.write_text("test_case:\n  TC-01-01:\n    title: 错误顶层key\n", encoding="utf-8")
            self.assertEqual(self._run([md, yml]), 1)

    def test_valid_cases_pass(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            md, yml = td / "case.md", td / "s.yaml"
            md.write_text(MIN_MARKMAP, encoding="utf-8")
            yml.write_text(GOOD_CASES_YAML, encoding="utf-8")
            self.assertEqual(self._run([md, yml]), 0)

    def test_non_utf8_input_fails_with_message(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            md, yml = td / "case.md", td / "gbk.yaml"
            md.write_text(MIN_MARKMAP, encoding="utf-8")
            yml.write_bytes("test_cases:\n  - id: TC-01-01\n    title: 中文GBK\n".encode("gbk"))
            self.assertEqual(self._run([md, yml]), 1)


class ScanSignalsUnitTests(unittest.TestCase):
    """scan_signals 的 YAML 输出安全性（sanitize 顺序是硬约束，见其注释）。"""

    def test_sanitize_replaces_control_chars(self):
        self.assertNotIn("\x00", scan_signals.sanitize("a\x00b\x07c"))
        self.assertNotIn("\x7f", scan_signals.sanitize("del\x7fchar"))

    def test_sanitize_truncates_to_80(self):
        self.assertLessEqual(len(scan_signals.sanitize("x" * 300)), 80)

    def test_sanitize_strips_trailing_backslash_before_escape(self):
        # 截断落在反斜杠上时不得留下奇数个尾部反斜杠（YAML 双引号标量会解析失败）
        out = scan_signals.sanitize("path\\" + "y" * 100)
        self.assertFalse(out.endswith("\\\\"))
        self.assertEqual(out.count("\\") % 2, 0)

    def test_sanitize_converts_double_quotes(self):
        self.assertNotIn('"', scan_signals.sanitize('他说"满100减20"'))


class ValidateSkillsRefResolutionTests(unittest.TestCase):
    """validate_skills 的引用解析基准（消费方 SKILL.md 目录约定）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        td = Path(self._tmp.name)
        (td / "skills" / "alpha" / "references").mkdir(parents=True)
        (td / "skills" / "alpha" / "templates").mkdir(parents=True)
        (td / "skills" / "core" / "methods").mkdir(parents=True)
        (td / "skills" / "beta").mkdir(parents=True)
        (td / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")
        (td / "skills" / "beta" / "SKILL.md").write_text("---\nname: beta\n---\n", encoding="utf-8")
        (td / "skills" / "core" / "x.md").write_text("core x\n", encoding="utf-8")
        (td / "skills" / "core" / "methods" / "m.md").write_text("core m\n", encoding="utf-8")
        self._old = (validate_skills.SKILLS_ROOT, validate_skills.REPO)
        validate_skills.SKILLS_ROOT = td / "skills"
        validate_skills.REPO = td

    def tearDown(self):
        validate_skills.SKILLS_ROOT, validate_skills.REPO = self._old
        self._tmp.cleanup()

    def _check(self, md_path, ref):
        errors = []
        validate_skills.check_target(md_path, ref, errors)
        return errors

    def test_reference_file_convention_basis_passes(self):
        """references/ 内 `../core/x.md` 按消费方 SKILL.md 目录解析 → 通过。"""
        ref_md = validate_skills.SKILLS_ROOT / "alpha" / "references" / "ref.md"
        self.assertEqual(self._check(ref_md, "../core/x.md"), [])

    def test_reference_file_self_basis_flagged(self):
        """references/ 内仅按文件自身可解析的路径（如 `../../core/x.md`）→ 基准违规。"""
        ref_md = validate_skills.SKILLS_ROOT / "alpha" / "references" / "ref.md"
        errors = self._check(ref_md, "../../core/x.md")
        self.assertTrue(any("路径基准违反约定" in e for e in errors))

    def test_missing_target_reported(self):
        ref_md = validate_skills.SKILLS_ROOT / "alpha" / "references" / "ref.md"
        errors = self._check(ref_md, "../core/nope.md")
        self.assertTrue(any("引用的文件不存在" in e for e in errors))

    def test_core_methods_self_basis_is_convention(self):
        """core/methods/ 内 `../x.md`（core 无单一消费方，文件自身即约定基准）→ 不误报。"""
        m = validate_skills.SKILLS_ROOT / "core" / "methods" / "m.md"
        self.assertEqual(self._check(m, "../x.md"), [])

    def test_cross_skill_reference_flagged(self):
        """alpha 的文件以约定基准引用 beta 目录（`../beta/y.md`）→ 跨 skill 红线。"""
        ref_md = validate_skills.SKILLS_ROOT / "alpha" / "references" / "ref.md"
        (validate_skills.SKILLS_ROOT / "beta" / "y.md").write_text("beta y\n", encoding="utf-8")
        errors = self._check(ref_md, "../beta/y.md")
        self.assertTrue(any("跨 skill 引用" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
