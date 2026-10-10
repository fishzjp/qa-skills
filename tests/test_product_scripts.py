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


@unittest.skipUnless(validate_skills.yaml is not None, "PyYAML 缺失时 YAML 门按 fail-loud 降级，正反例测试不适用")
class FrontmatterYamlGateTests(unittest.TestCase):
    """check_frontmatter 的 YAML 合法性门：手写行解析放行、标准解析器拒绝的 frontmatter 必须 FAIL。

    事故口径（2026-09-07）：description 值内含 ": " 的 plain scalar 被手写解析放行、
    宿主侧标准 YAML 解析器（js-yaml / 'yaml' npm 包 / PyYAML）全量拒绝——非法 frontmatter
    会在宿主加载 skill 时炸掉。此门保证 skills/ 内所有 frontmatter 通过标准解析器。
    """

    def setUp(self):
        self.errors = []

    def _check(self, description_line):
        fm = f"name: alpha\nversion: 0.8.1\n{description_line}\n"
        return validate_skills.check_frontmatter(f"---\n{fm}---\n正文", "alpha", self.errors)

    def test_plain_scalar_with_colon_space_fails(self):
        """手写解析放行、标准解析器拒绝的写法（值内裸 ": "）→ 必须进 errors。"""
        self._check('description: End-to-end QA entry: "test this feature fully" works')
        self.assertTrue(any("不是合法 YAML" in e for e in self.errors), self.errors)

    def test_double_quoted_wrapped_description_passes(self):
        """双引号包裹 + 内部引号转义 → 无错误，_fm_scalar 与 YAML 解析值一致。"""
        version = self._check('description: "End-to-end QA entry: \\"test this feature fully\\" works well enough here"')
        self.assertEqual(self.errors, [], self.errors)
        self.assertEqual(version, "0.8.1")
        desc = validate_skills._fm_scalar('name: alpha\ndescription: "a: \\"b\\""', "description")
        self.assertEqual(desc, 'a: "b"')

    def test_unterminated_quote_fails(self):
        """包裹引号不配对（YAML 解析报错）→ 必须进 errors。"""
        self._check('description: "没有闭合引号的描述文字在这里足够长')
        self.assertTrue(any("不是合法 YAML" in e for e in self.errors), self.errors)

    def test_single_quoted_with_apostrophe_passes(self):
        """单引号标量内 ASCII 单引号翻倍写法 → 通过且还原正确。"""
        self._check("description: 'Review others'' work for coverage and executability, long enough text'")
        self.assertEqual(self.errors, [], self.errors)
        desc = validate_skills._fm_scalar("description: 'Review others'' work'", "description")
        self.assertEqual(desc, "Review others' work")

    def test_literal_block_scalar_keeps_newlines(self):
        """`|` 字面块保留换行（`>` 折叠块空格连接）——混用空格折叠会让多行 `|`
        值恒与 YAML 解析值不一致（2026-10-10 二轮审查误拒原形）。"""
        desc = validate_skills._fm_scalar("description: |\n  第一行的描述文字\n  第二行的描述文字", "description")
        self.assertEqual(desc, "第一行的描述文字\n第二行的描述文字")
        desc = validate_skills._fm_scalar("description: >\n  第一行的描述文字\n  第二行的描述文字", "description")
        self.assertEqual(desc, "第一行的描述文字 第二行的描述文字")


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


class FrontmatterDuplicateKeyTests(unittest.TestCase):
    """frontmatter 重复键：手写行解析取首个、标准 YAML last-wins——同名键并存时
    校验口径与宿主解析结果分裂（2026-10-10 对抗审查：name 双写逃检）。"""

    def setUp(self):
        self.errors = []

    def _check(self, fm_body):
        return validate_skills.check_frontmatter(f"---\n{fm_body}\n---\n正文", "alpha", self.errors)

    def test_duplicate_name_key_flagged(self):
        self._check("name: alpha\nname: evil-twin\nversion: 0.9.0\n"
                    'description: "足够长的描述文字在这里凑够二十个字符以上"')
        self.assertTrue(any("重复键" in e and "name" in e for e in self.errors), self.errors)

    def test_unique_keys_pass(self):
        self._check("name: alpha\nversion: 0.9.0\n"
                    'description: "足够长的描述文字在这里凑够二十个字符以上"')
        self.assertFalse(any("重复键" in e for e in self.errors), self.errors)


class WhenNotToUseBodyTests(unittest.TestCase):
    """When NOT to Use 段体非空：空标题段 = 反触发边界退化归零（此前只查标题存在）。"""

    def _check(self, body_after_heading):
        text = f"---\nname: alpha\n---\n\n# t\n\n## When NOT to Use\n{body_after_heading}\n## 其他\n\n正文"
        errors = []
        validate_skills.check_when_not_to_use(text, "alpha", errors)
        return errors

    def test_empty_body_flagged(self):
        self.assertTrue(self._check("\n\n## 其他"), )  # 标题后直接下一节

    def test_missing_heading_flagged(self):
        errors = []
        validate_skills.check_when_not_to_use("---\nname: alpha\n---\n正文无该节", "alpha", errors)
        self.assertTrue(any("缺 '## When NOT to Use'" in e for e in errors))

    def test_populated_body_passes(self):
        self.assertEqual(self._check("\n- 写用例 → test-case-writing\n"), [])

    def test_comment_only_body_flagged(self):
        """纯 HTML 注释段体渲染为空——剥注释后判空（2026-10-10 二轮审查绕过形态）。"""
        errors = []
        text = ("---\nname: alpha\n---\n\n# t\n\n## When NOT to Use\n\n"
                "<!-- 交给 bug-analysis -->\n\n## 其他\n")
        validate_skills.check_when_not_to_use(text, "alpha", errors)
        self.assertTrue(any("段内容为空" in e for e in errors), errors)

    def test_heading_only_inside_fence_not_counted(self):
        """真实段删除、标题仅存于围栏示例内——掩码后不算数（2026-10-10 二轮审查骗绿原形）。"""
        errors = []
        text = ("---\nname: alpha\n---\n\n```md\n## When NOT to Use\n- 示例\n```\n\n正文\n")
        validate_skills.check_when_not_to_use(text, "alpha", errors)
        self.assertTrue(any("缺 '## When NOT to Use'" in e for e in errors), errors)


class SectionPointerTests(unittest.TestCase):
    """节号指针核对：引用检查只查路径存在性，不查"§N 指向的是不是声称的内容"——
    结构绿、语义漂（2026-10-10 审查实证：flaky-playbook 判定树+证据表实际在 §2–3
    而 SKILL.md 写「第 1–2 节：判定树 + 证据表」）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        td = Path(self._tmp.name)
        (td / "skills" / "alpha" / "references").mkdir(parents=True)
        (td / "skills" / "core").mkdir(parents=True)
        (td / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")
        (td / "skills" / "core" / "triage.md").write_text(
            "# triage\n\n## 1. 复跑矩阵\n\n内容\n\n## 2. 判定树\n\n内容\n\n## 3. 四分类证据表\n\n内容\n",
            encoding="utf-8")
        self._old = (validate_skills.SKILLS_ROOT, validate_skills.REPO)
        validate_skills.SKILLS_ROOT = td / "skills"
        validate_skills.REPO = td

    def tearDown(self):
        validate_skills.SKILLS_ROOT, validate_skills.REPO = self._old
        self._tmp.cleanup()

    def _pointers(self, line):
        sk = validate_skills.SKILLS_ROOT / "alpha" / "SKILL.md"
        sk.write_text(f"---\nname: alpha\n---\n\n{line}\n", encoding="utf-8")
        errors = []
        validate_skills.check_section_pointers(sk, errors)
        return errors

    def test_on_target_with_keywords_passes(self):
        """（第 2–3 节：判定树 + 证据表）——关键词都在 §2/§3 节题中 → 零错误。"""
        self.assertEqual(self._pointers("见 `../core/triage.md`（第 2–3 节：判定树 + 证据表）"), [])

    def test_wrong_range_with_keywords_flagged(self):
        """P0-1 原形：写 1–2 节但"证据表"只在 §3 → 关键词命中检查必须抓到。"""
        errors = self._pointers("见 `../core/triage.md`（第 1–2 节：判定树 + 证据表）")
        self.assertTrue(any("节号指针与目标节题不符" in e and "证据表" in e for e in errors), errors)

    def test_out_of_range_flagged(self):
        errors = self._pointers("见 `../core/triage.md` 第 9 节")
        self.assertTrue(any("节号指针越界" in e for e in errors), errors)

    def test_in_range_without_keywords_passes(self):
        self.assertEqual(self._pointers("见 `../core/triage.md` 第 3 节"), [])

    def test_unnumbered_target_skipped(self):
        (validate_skills.SKILLS_ROOT / "core" / "plain.md").write_text(
            "# 无编号节\n\n## When NOT to Use\n\n内容\n", encoding="utf-8")
        self.assertEqual(self._pointers("见 `../core/plain.md` 第 3 节"), [])

    def test_sha_pointer_out_of_range_flagged(self):
        """§N 形态（仓内活跃写法）纳入越界层——2026-10-10 二轮审查：本批手工修的
        triage §6→§7 正是 § 形态，此前完全逃逸。"""
        errors = self._pointers("见 `../core/triage.md`（§2–9）")
        self.assertTrue(any("节号指针越界" in e for e in errors), errors)

    def test_sha_pointer_in_range_passes(self):
        self.assertEqual(self._pointers("边界见 `../core/triage.md` §3"), [])

    def test_fenced_fake_heading_cannot_inflate_sections(self):
        """围栏投毒抬节图：目标文件围栏内放 `## 99. 泳道模板` + 指针第 99 节——
        节图基于掩码文本，围栏内伪标题不算（2026-10-10 二轮审查实测骗绿原形）。"""
        (validate_skills.SKILLS_ROOT / "core" / "triage.md").write_text(
            "# t\n\n## 1. A\n\n```md\n## 99. 泳道模板\n```\n", encoding="utf-8")
        errors = self._pointers("见 `../core/triage.md` 第 99 节：泳道模板")
        self.assertTrue(any("节号指针越界" in e for e in errors), errors)

    def test_fenced_fake_heading_cannot_shadow_real_titles(self):
        """围栏投毒反向覆盖：伪标题出现在真标题之后覆盖节图 → 正确指针被误报。
        节图掩码后该误报源消失。"""
        (validate_skills.SKILLS_ROOT / "core" / "triage.md").write_text(
            "# t\n\n## 2. 判定树\n\n## 3. 四分类证据表\n\n```md\n## 2. 伪标题甲\n```\n",
            encoding="utf-8")
        self.assertEqual(self._pointers("见 `../core/triage.md`（第 2–3 节：判定树 + 证据表）"), [])


class VersionGateChangelogTests(unittest.TestCase):
    """版本三处同步含 CHANGELOG 定版小节存在性（RELEASING 声称"机械强制"，
    实现此前只比 SKILL↔package.json——补齐名实相符）；package.json 缺失 fail-loud。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old = validate_skills.REPO
        validate_skills.REPO = Path(self._tmp.name)

    def tearDown(self):
        validate_skills.REPO = self._old
        self._tmp.cleanup()

    def _check(self, pkg_version, changelog):
        td = validate_skills.REPO
        if pkg_version is not None:
            (td / "package.json").write_text(f'{{"version": "{pkg_version}"}}', encoding="utf-8")
        if changelog is not None:
            (td / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
        errors = []
        validate_skills.check_versions(errors, [])
        return errors

    def test_missing_changelog_section_flagged(self):
        errors = self._check("0.9.0", "# 更新日志\n\n## [0.8.1] - 2026-09-07\n\n- 旧版本\n")
        self.assertTrue(any("缺 [0.9.0] 定版小节" in e for e in errors), errors)

    def test_present_changelog_section_passes(self):
        errors = self._check("0.9.0", "# 更新日志\n\n## [0.9.0] - 2026-09-20\n\n- 条目\n")
        self.assertEqual([e for e in errors if "CHANGELOG" in e], [])

    def test_fenced_fake_section_header_not_counted(self):
        """真定版节改名 + 围栏内伪节头顶替——掩码 + 节界锚定后必须红
       （2026-10-10 二轮审查实测骗绿原形）；rc 前缀不顶替定版节。"""
        errors = self._check("0.9.0", "# 更新日志\n\n## [0.9.0]-rc1\n\n```md\n## [0.9.0] - 2026-09-20\n```\n")
        self.assertTrue(any("缺 [0.9.0] 定版小节" in e for e in errors), errors)

    def test_missing_package_json_fails_loud(self):
        errors = self._check(None, "# 更新日志\n")
        self.assertTrue(any("package.json: 缺失" in e for e in errors), errors)


class MdLinkSuffixCoverageTests(unittest.TestCase):
    """md 链接存在性不限后缀：.png/.sh/.html 等资产断链同样红（此前只查
    md/py/yaml/json 后缀——2026-10-10 对抗审查：不存在的架构图照绿）。"""

    def _check(self, md_text, layout):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            sk = td / "skills" / "alpha" / "SKILL.md"
            sk.parent.mkdir(parents=True)
            sk.write_text(f"---\nname: alpha\n---\n\n{md_text}\n", encoding="utf-8")
            for rel in layout:
                q = td / "skills" / "alpha" / rel
                q.parent.mkdir(parents=True, exist_ok=True)
                q.write_text("", encoding="utf-8")
            old = (validate_skills.SKILLS_ROOT, validate_skills.REPO)
            validate_skills.SKILLS_ROOT, validate_skills.REPO = td / "skills", td
            try:
                errors = []
                validate_skills.check_md_links(sk, errors)
                return errors
            finally:
                validate_skills.SKILLS_ROOT, validate_skills.REPO = old

    def test_broken_non_md_asset_flagged(self):
        errors = self._check("![架构](references/arch.png)", ["references/x.md"])
        self.assertTrue(any("arch.png" in e and "链接目标不存在" in e for e in errors), errors)

    def test_existing_non_md_asset_passes(self):
        self.assertEqual(self._check("![架构](references/arch.png)", ["references/arch.png"]), [])

    def test_same_skill_asset_via_link_not_cross_flagged(self):
        """symlink 环境回归钉子（2026-10-10 修复）：macOS tempdir（/var→/private/var）
        下 references/ 内同 skill 资产的 md 链接不得因 resolve 口径分裂误报跨 skill 引用。"""
        self.assertEqual(self._check("![架构](references/arch.png)", ["references/arch.png"]), [])
        # 反引号引用形态同样不得误报
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "skills" / "alpha" / "references").mkdir(parents=True)
            (td / "skills" / "alpha" / "references" / "r.md").write_text("# r\n", encoding="utf-8")
            sk = td / "skills" / "alpha" / "SKILL.md"
            sk.write_text("---\nname: alpha\n---\n\n见 `references/r.md`\n", encoding="utf-8")
            old = (validate_skills.SKILLS_ROOT, validate_skills.REPO)
            validate_skills.SKILLS_ROOT, validate_skills.REPO = td / "skills", td
            try:
                errors = []
                validate_skills.check_references(sk, errors)
                self.assertEqual(errors, [])
            finally:
                validate_skills.SKILLS_ROOT, validate_skills.REPO = old


if __name__ == "__main__":
    unittest.main()
