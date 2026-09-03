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


# 风险覆盖门禁（V4-终态留痕）曾对 risk-model.md §4 权威 Risk Map 格式整块失效：
# id 与 level 分行书写时逐行启发式提取为空 → 门禁静默放行（全绿通过）。
# 以下用例锚定该失败形态：跨行 yaml 记录、行内同现表格、extract 为空告警、
# exclude 轴按 schema 约定无 depth 时不得误告警。
STRATEGY_YAML_BLOCK = """test_strategy:
  type_scope:
    performance: { decision: include, depth: standard, signals: ["PRD-4.2 SLA"], risk_refs: [R1] }
    security_business: { decision: include, depth: light, signals: ["鉴权"] }
    reliability: { decision: include, depth: light, signals: ["retry"] }
    concurrency: { decision: include, depth: light, signals: ["秒杀"] }
    compatibility: { decision: include, depth: light, signals: ["有前端"] }
    accessibility: { decision: include, depth: light, signals: ["有前端"] }
    visual: { decision: include, depth: light, signals: ["有前端"] }
    i18n: { decision: exclude, rationale: "需求信号未命中；无代码仓库", scanned: ["需求信号(G)"] }
    migration: { decision: include, depth: light, signals: ["migrations/x.sql"] }
    contract_integration: { decision: include, depth: light, signals: ["外部风控"] }
  depth_budget:
    full_axes: []
"""


def _strategy_md(riskmap_block):
    return f"# 测试策略\n\n{riskmap_block}\n```yaml\n{STRATEGY_YAML_BLOCK}```\n"


RISKMAP_YAML_MULTILINE = """## Risk Map

```yaml
risk:
  id: R1
  feature: 用户删除
  impact: 5
  likelihood: 3
  level: Critical                  # 15 = 5 × 3
  evidence:
    level: E2
    source: user_service.go:124
  confidence: medium
  status: hypothesis
```
"""

RISKMAP_TABLE_INLINE = """## Risk Map

| 风险 | 等级 | 状态 |
|------|------|------|
| R1 用户删除 | Critical | 待验证 |
"""


class RiskGateExtractionTests(unittest.TestCase):
    """风险等级提取双形态 + 门禁对权威格式的实际生效（H1 回归锚）。"""

    def test_yaml_multiline_record_extracted(self):
        """risk-model.md §4 权威格式（id 与 level 分行）必须能建立映射。"""
        levels = validate_schema.extract_risk_levels(RISKMAP_YAML_MULTILINE)
        self.assertEqual(levels.get("R1"), "Critical")

    def test_inline_table_row_extracted(self):
        levels = validate_schema.extract_risk_levels(RISKMAP_TABLE_INLINE)
        self.assertEqual(levels.get("R1"), "Critical")

    def test_multiline_record_survives_multiple_risks(self):
        text = RISKMAP_YAML_MULTILINE + RISKMAP_YAML_MULTILINE.replace(
            "id: R1", "id: R2").replace("level: Critical", "level: High")
        levels = validate_schema.extract_risk_levels(text)
        self.assertEqual(levels.get("R1"), "Critical")
        self.assertEqual(levels.get("R2"), "High")

    def test_v4_terminal_trace_fires_on_authoritative_format(self):
        """挂 Critical 风险却降档且 budget_review 无留痕——权威格式下必须报错（曾静默放行）。"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.md"
            p.write_text(_strategy_md(RISKMAP_YAML_MULTILINE), encoding="utf-8")
            errors, _ = validate_schema.validate_strategy(p)
            self.assertTrue(any("V4-终态" in e and "performance" in e for e in errors))

    def test_mode1_gate_fires_on_authoritative_format(self):
        """模式一覆盖门禁：Critical 风险零 risk_ref 覆盖必须报错（曾静默放行）。"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.md"
            p.write_text(_strategy_md(RISKMAP_YAML_MULTILINE), encoding="utf-8")
            errors, warnings = [], []
            validate_schema.check_risk_coverage(
                [{"id": "TC-01-01"}], p, errors, warnings)  # 用例无 risk_ref
            self.assertTrue(any("风险覆盖" in e and "R1" in e for e in errors))
            errors2, _ = [], []
            validate_schema.check_risk_coverage(
                [{"id": "TC-01-01", "risk_ref": ["R1"]}], p, errors2, warnings)
            self.assertEqual(errors2, [])

    def test_no_levels_with_risk_ids_warns(self):
        """出现 Rn 但两种形态都提取不到等级 → 告警门禁失效，不得安静。"""
        text = "risk_refs: [R7]，正文无等级词"
        levels = validate_schema.extract_risk_levels(text)
        self.assertEqual(levels, {})
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.md"
            p.write_text(_strategy_md(text), encoding="utf-8")
            _, warnings = validate_schema.validate_strategy(p)
            self.assertTrue(any("无门禁等级依据" in w and "R7" in w for w in warnings))

    def test_partial_gap_warns_only_missing_id(self):
        """部分记录可提取、部分无等级 → 只对缺口编号告警，不误伤已提取的。"""
        text = RISKMAP_YAML_MULTILINE + "另有风险 R9 等级待补\n"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.md"
            p.write_text(_strategy_md(text), encoding="utf-8")
            _, warnings = validate_schema.validate_strategy(p)
            gap_warns = [w for w in warnings if "无门禁等级依据" in w]
            self.assertEqual(len(gap_warns), 1)
            self.assertIn("R9", gap_warns[0])
            self.assertNotIn("R1", gap_warns[0])

    def test_medium_only_record_not_gap_warned(self):
        """记录 level 为 Medium/Low 属正常不入门禁——不算提取缺口，不告警。"""
        text = RISKMAP_YAML_MULTILINE.replace("level: Critical", "level: Medium")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.md"
            p.write_text(_strategy_md(text), encoding="utf-8")
            _, warnings = validate_schema.validate_strategy(p)
            self.assertFalse(any("无门禁等级依据" in w for w in warnings))

    def test_list_style_record_medium_not_gap_warned(self):
        """yaml 列表式记录（`- id: R5` 后深缩进的 level: Medium）不算缺口——
        缩进基准须取 id token 列位置而非行首，否则与 Critical/High 可提取不对称。"""
        text = """## Risk Map

```yaml
risks:
  - id: R5
    feature: 数据导出
    level: Medium
```
"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.md"
            p.write_text(_strategy_md(text), encoding="utf-8")
            _, warnings = validate_schema.validate_strategy(p)
            # 夹具的 type_scope 引用了无记录的 R1，其缺口告警属预期噪音；
            # 本测试锚定的是：列表式 R5（Medium）不得被误报为缺口
            self.assertFalse(any("无门禁等级依据" in w and "R5" in w
                                 for w in warnings))

    def test_nested_evidence_level_not_treated_as_record_level(self):
        """只有嵌套 evidence.level（缩进深于 id 行）而无记录自身 level → 属缺口，须告警。"""
        text = """## Risk Map

```yaml
risk:
  id: R2
  feature: 数据导出
  evidence:
    level: E2
    source: export_service.go:88
```
"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.md"
            p.write_text(_strategy_md(text), encoding="utf-8")
            _, warnings = validate_schema.validate_strategy(p)
            self.assertTrue(any("无门禁等级依据" in w and "R2" in w for w in warnings))

    def test_exclude_axis_without_depth_not_warned(self):
        """exclude 轴按 schema 约定不写 depth——校验器不得反向建议（此前对官方示例也告警）。"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.md"
            p.write_text(_strategy_md(RISKMAP_YAML_MULTILINE), encoding="utf-8")
            _, warnings = validate_schema.validate_strategy(p)
            self.assertFalse(any("depth 缺省" in w and "i18n" in w for w in warnings))

    def test_code_mode_missing_refs_warns(self):
        """代码模式（markmap 带测准声明）code_refs/evidence 缺失 → 告警；纯文档模式不告警。"""
        code_markmap = "> **测准声明**：本文件以 repo@main 实际实现为唯一功能基线。\n" + MIN_MARKMAP
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            md, yml = td / "case.md", td / "s.yaml"
            yml.write_text(GOOD_CASES_YAML, encoding="utf-8")
            md.write_text(code_markmap, encoding="utf-8")
            import io, contextlib
            with contextlib.redirect_stdout(io.StringIO()) as fh:
                rc = validate_schema.main([str(md), str(yml)])
            out = fh.getvalue()
            self.assertEqual(rc, 0)
            self.assertIn("代码模式但 code_refs 为空", out)
            self.assertIn("evidence 三件套", out)
            # 纯文档模式（无测准声明）不产生这两类告警
            md2 = td / "case2.md"
            md2.write_text(MIN_MARKMAP, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as fh2:
                rc2 = validate_schema.main([str(md2), str(yml)])
            self.assertEqual(rc2, 0)
            self.assertNotIn("代码模式但", fh2.getvalue())


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
