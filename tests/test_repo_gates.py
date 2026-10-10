#!/usr/bin/env python3
"""validate_repo.py 仓库面守门的回归测试（安装器行为冒烟由 tests/install_smoke.sh 承接）.

锚定的都是守门脚本自身的漏报/误报形态——守门脚本漏报 = 门禁骗绿，比产品 bug 更危险：
- 链接 / 资产提取对坏输入必须报错、好输入必须放行（含 <img src>、<source srcset>、目录目标）
- 语法门对坏 py / 坏 json 必须报错
- 自锚定契约：对本仓库实跑 main() 必须全绿——守门脚本与仓库内容任何一边破坏立即红
"""
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import _gate_common    # noqa: E402
import validate_repo  # noqa: E402


class LocalTargetExtractionTests(unittest.TestCase):
    """extract_local_refs 的形态覆盖：什么算本地目标、什么该跳过、行号必须对。"""

    def test_md_img_srcset_all_extracted(self):
        text = ('[doc](./README.md) ![h](./assets/hero.png) '
                '<img src="./assets/hero.png"> <source srcset="./assets/hero-dark.png">')
        paths = [p for _, _, p in validate_repo.extract_local_refs(text)]
        self.assertIn("./README.md", paths)
        # md 图片与 <img src> 各命中一次
        self.assertEqual(paths.count("./assets/hero.png"), 2)
        self.assertIn("./assets/hero-dark.png", paths)

    def test_reference_style_definition_extracted(self):
        # 引用式链接定义 [x]: path——两个校验器此前都漏查的形态（2026-09-07 审查）
        text = '见 [手册](MANUAL)\n\n[MANUAL]: ./docs/manual.md\n'
        paths = [p for _, _, p in validate_repo.extract_local_refs(text)]
        self.assertIn("./docs/manual.md", paths)

    def test_fenced_block_and_footnote_skipped(self):
        # 围栏内示例与脚注定义是两类实证误报源（2026-09-07 二轮审查），必须跳过
        text = ('```md\n[manual]: ./docs/fenced.md\n[link](./fenced-link.md)\n```\n'
                '[^1]: note\n[ok]: ./docs/real.md\n')
        paths = [p for _, _, p in validate_repo.extract_local_refs(text)]
        self.assertEqual(paths, ["./docs/real.md"])

    def test_reference_def_with_title_and_image_prefix(self):
        text = '![logo]: ./img.png "Logo"\n[with-title]: ./docs/a.md "标题"\n'
        paths = [p for _, _, p in validate_repo.extract_local_refs(text)]
        self.assertEqual(paths, ["./img.png", "./docs/a.md"])

    def test_line_numbers_accurate(self):
        text = 'line1\n\n[x](./a.md)\n[y](./missing.md)\n'
        rows = validate_repo.extract_local_refs(text)
        by_ref = {raw: line for line, raw, _ in rows}
        self.assertEqual(by_ref["./a.md"], 3)
        self.assertEqual(by_ref["./missing.md"], 4)

    def test_external_anchor_data_skipped(self):
        text = ('[gh](https://github.com/x) [top](#section) '
                '<img src="data:image/png;base64,AAA"> <a href="mailto:a@b.c">')
        self.assertEqual(validate_repo.extract_local_refs(text), [])

    def test_fragment_and_query_stripped_url_decoded(self):
        text = '[c](./CHANGELOG.md#v010) [s](docs%20file.md?q=1)'
        paths = [p for _, _, p in validate_repo.extract_local_refs(text)]
        self.assertEqual(paths, ["./CHANGELOG.md", "docs file.md"])

    def test_srcset_multiple_candidates_take_urls_only(self):
        text = '<source srcset="./a.png 2x, ./b.png 1x">'
        paths = [p for _, _, p in validate_repo.extract_local_refs(text)]
        self.assertEqual(paths, ["./a.png", "./b.png"])


class RootMdLinkCheckTests(unittest.TestCase):
    """md 链接检查的存在性判定（含目录目标——README 链接 ./examples/ 这类；
    基准 = 文件所在目录，覆盖 .github/、examples/ 等非根目录 md）。"""

    def _check(self, md_text, layout, md_rel="README.md"):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            p = td / md_rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(md_text, encoding="utf-8")
            for rel, content in layout.items():
                q = td / rel
                if rel.endswith("/"):
                    q.mkdir(parents=True, exist_ok=True)
                else:
                    q.parent.mkdir(parents=True, exist_ok=True)
                    q.write_text(content, encoding="utf-8")
            errors = []
            validate_repo.check_md_links(td, [md_rel], errors)
            return errors

    def test_missing_target_flagged(self):
        errors = self._check("[x](./nope.md) [y](./also-missing/)", {})
        self.assertEqual(len(errors), 2)
        self.assertIn("README.md", errors[0])

    def test_existing_file_and_dir_pass(self):
        errors = self._check("[x](./a.md) [d](./examples/)",
                             {"a.md": "hi", "examples/": ""})
        self.assertEqual(errors, [])

    def test_non_root_md_resolves_relative_to_own_dir(self):
        """非根目录 md（.github/ 模板形态）的相对链接按文件所在目录判定——
        2026-10-10 扩面审查抓到的真问题形态：.github/PULL_REQUEST_TEMPLATE.md
        写 ./CONTRIBUTING.md 解析到 .github/CONTRIBUTING.md 断链。"""
        errors = self._check("[见](./CONTRIBUTING.md)", {},
                             md_rel=".github/PULL_REQUEST_TEMPLATE.md")
        self.assertEqual(len(errors), 1)
        self.assertIn(".github/PULL_REQUEST_TEMPLATE.md", errors[0])
        errors = self._check("[见](../CONTRIBUTING.md)", {"CONTRIBUTING.md": "x"},
                             md_rel=".github/PULL_REQUEST_TEMPLATE.md")
        self.assertEqual(errors, [])


class FenceErrorTests(unittest.TestCase):
    """未闭合围栏自检：mask_fenced / visible_lines 对未闭合围栏是"其后全部按代码块
    掩掉"的保守行为——引用检查静默跳过该区间（fail-silent）。此门把未闭合本身
    变成独立错误（2026-10-10 对抗审查实测构造：一个未闭合围栏废掉单文件引用门）。"""

    def test_unclosed_fence_reported_with_line(self):
        fe = _gate_common.fence_error("正文\n```python\n[x](./fenced.md)\n再一段")
        self.assertEqual(fe, (2, "```"))

    def test_closed_fence_passes(self):
        self.assertIsNone(_gate_common.fence_error("```python\ncode\n```\n正文"))

    def test_mismatched_fence_marker_reported(self):
        # ``` 开、~~~ 闭不匹配——同样视为未闭合
        fe = _gate_common.fence_error("~~~\ncode\n```\n正文")
        self.assertIsNotNone(fe)


class BilingualPairTests(unittest.TestCase):
    """落地页静态双语对门：zh-only/en-only 计数相等 + 序列相邻交替。
    此前成对性只活在发版提交信息里（缺一半照绿，2026-10-10 对抗审查实测构造）。"""

    def _check(self, html):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "index.html").write_text(html, encoding="utf-8")
            errors = []
            validate_repo.check_bilingual_pairs(Path(td), errors)
            return errors

    def test_paired_sequence_passes(self):
        errors = self._check(
            '<span class="zh-only">中文</span><span class="en-only">EN</span>'
            '<p class="zh-only">中文2</p><p class="en-only">EN2</p>')
        self.assertEqual(errors, [])

    def test_missing_half_flagged(self):
        errors = self._check(
            '<span class="zh-only">中文</span><span class="en-only">EN</span>'
            '<span class="zh-only">孤儿中文</span>')
        self.assertTrue(any("静态双语对不完整" in e for e in errors), errors)

    def test_consecutive_same_kind_flagged(self):
        errors = self._check(
            '<span class="zh-only">中文</span><span class="zh-only">又一个中文</span>'
            '<span class="en-only">EN</span><span class="en-only">EN2</span>')
        self.assertTrue(any("相邻性破坏" in e for e in errors), errors)

    def test_no_pairs_at_all_flagged(self):
        errors = self._check('<div class="hero">无双语标记的单语页</div>')
        self.assertTrue(any("未检出" in e for e in errors), errors)

    def test_ambiguous_both_classes_flagged(self):
        errors = self._check('<span class="zh-only en-only">自相矛盾</span>')
        self.assertTrue(any("同时挂" in e for e in errors), errors)

    def test_css_and_script_not_counted(self):
        # CSS 选择器与 JS 字符串里的类名不是元素——不得计入序列（零对会误报"未检出"）
        errors = self._check(
            '<style>html.lang-en .zh-only{display:none}</style>'
            '<script>var t="zh-only";</script>'
            '<span class="zh-only">中文</span><span class="en-only">EN</span>')
        self.assertEqual(errors, [])


class JsonldVersionTests(unittest.TestCase):
    """JSON-LD softwareVersion 与 package.json 一致（GEO 层版本事实曾停更两个版本，
    从 RELEASING 人工检查单机制化为常驻门）。"""

    def _check(self, html_version, pkg_version="1.2.3"):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            html = ('{"@type":"SoftwareApplication"' +
                    (f',"softwareVersion":"{html_version}"' if html_version else "") + '}')
            (td / "index.html").write_text(html, encoding="utf-8")
            (td / "package.json").write_text(f'{{"version": "{pkg_version}"}}', encoding="utf-8")
            errors = []
            validate_repo.check_jsonld_version(td, errors)
            return errors

    def test_mismatch_flagged(self):
        errors = self._check("0.8.0", pkg_version="0.9.0")
        self.assertTrue(any("softwareVersion" in e for e in errors), errors)

    def test_match_passes(self):
        self.assertEqual(self._check("0.9.0", pkg_version="0.9.0"), [])

    def test_missing_field_flagged(self):
        errors = self._check(None)
        self.assertTrue(any("缺 JSON-LD softwareVersion" in e for e in errors), errors)


class HtmlAssetCheckTests(unittest.TestCase):
    def _check(self, html, layout):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "index.html").write_text(html, encoding="utf-8")
            for rel, content in layout.items():
                p = td / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
            errors = []
            n = validate_repo.check_html_assets(td, errors)
            return n, errors

    def test_missing_asset_flagged(self):
        n, errors = self._check('<img src="assets/gone/gone.jpg">', {})
        self.assertEqual(n, 1)
        self.assertEqual(len(errors), 1)
        self.assertIn("gone.jpg", errors[0])

    def test_existing_assets_pass_external_skipped(self):
        n, errors = self._check(
            '<img src="assets/a.jpg"><link href="https://cdn.example/x.css">'
            '<source srcset="assets/b.png 2x">',
            {"assets/a.jpg": "", "assets/b.png": ""})
        self.assertEqual(n, 2)
        self.assertEqual(errors, [])


class YamlGateDependencyTests(unittest.TestCase):
    """YAML 门依赖钉子：无 PyYAML 必须 FAIL 而非降级跳过。

    2026-09-03 事故同族的防线：此前的降级跳过 + 无测试覆盖 = 删掉 CI 的 pip 步骤
    YAML 门零文件校验照绿。本测试模拟 yaml 缺失，钉住 fail-loud 行为。
    """

    def setUp(self):
        self._real_yaml = validate_repo.yaml

    def tearDown(self):
        validate_repo.yaml = self._real_yaml

    def test_missing_pyyaml_fails_loud(self):
        if self._real_yaml is None:
            self.fail("开发环境应安装 PyYAML（pip install pyyaml），否则本测试无法锚定 fail-loud")
        validate_repo.yaml = None
        with unittest.mock.patch("sys.stdout"):  # 吞掉守门脚本正常输出
            rc = validate_repo.main()
        self.assertEqual(rc, 1)
        validate_repo.yaml = self._real_yaml  # 恢复依赖，证明 FAIL 只来自依赖缺失而非仓库内容
        with unittest.mock.patch("sys.stdout"):
            self.assertEqual(validate_repo.main(), 0)


class SyntaxGateTests(unittest.TestCase):
    """py / json 语法门的正负例（YAML 门依赖钉子见 YamlGateDependencyTests）。"""

    def test_bad_python_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "broken.py").write_text("def f(:\n  pass\n", encoding="utf-8")
            errors = []
            n = validate_repo.check_python(td, ["broken.py"], errors)
            self.assertEqual(n, 1)
            self.assertEqual(len(errors), 1)
            self.assertIn("语法错误", errors[0])

    def test_good_python_passes(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "ok.py").write_text("x = 1\n", encoding="utf-8")
            errors = []
            validate_repo.check_python(td, ["ok.py"], errors)
            self.assertEqual(errors, [])

    def test_non_utf8_python_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "gbk.py").write_bytes("# 中文\nx = 1\n".encode("gbk"))
            errors = []
            validate_repo.check_python(td, ["gbk.py"], errors)
            self.assertTrue(any("非 UTF-8" in e for e in errors))


class RepoSelfCheckTests(unittest.TestCase):
    """自锚定契约：守门脚本对本仓库实跑必须全绿。"""

    @unittest.skipUnless(validate_repo.find_git(), "无 git 环境")
    def test_repo_self_check_green(self):
        self.assertEqual(validate_repo.main(), 0)


if __name__ == "__main__":
    unittest.main()
