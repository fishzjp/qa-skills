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
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import validate_repo  # noqa: E402


class LocalTargetExtractionTests(unittest.TestCase):
    """local_targets 的形态覆盖：什么算本地目标、什么该跳过。"""

    def test_md_img_srcset_all_extracted(self):
        text = ('[doc](./README.md) ![h](./assets/hero.png) '
                '<img src="./assets/hero.png"> <source srcset="./assets/hero-dark.png">')
        paths = [p for _, p in validate_repo.local_targets(text)]
        self.assertIn("./README.md", paths)
        # md 图片与 <img src> 各命中一次
        self.assertEqual(paths.count("./assets/hero.png"), 2)
        self.assertIn("./assets/hero-dark.png", paths)

    def test_external_anchor_data_skipped(self):
        text = ('[gh](https://github.com/x) [top](#section) '
                '<img src="data:image/png;base64,AAA"> <a href="mailto:a@b.c">')
        self.assertEqual(validate_repo.local_targets(text), [])

    def test_fragment_and_query_stripped_url_decoded(self):
        text = '[c](./CHANGELOG.md#v010) [s](docs%20file.md?q=1)'
        paths = [p for _, p in validate_repo.local_targets(text)]
        self.assertEqual(paths, ["./CHANGELOG.md", "docs file.md"])

    def test_srcset_multiple_candidates_take_urls_only(self):
        text = '<source srcset="./a.png 2x, ./b.png 1x">'
        paths = [p for _, p in validate_repo.local_targets(text)]
        self.assertEqual(paths, ["./a.png", "./b.png"])


class RootMdLinkCheckTests(unittest.TestCase):
    """根目录 md 链接检查的存在性判定（含目录目标——README 链接 ./examples/ 这类）。"""

    def _check(self, md_text, layout):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "README.md").write_text(md_text, encoding="utf-8")
            for rel, content in layout.items():
                p = td / rel
                if rel.endswith("/"):
                    p.mkdir(parents=True, exist_ok=True)
                else:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(content, encoding="utf-8")
            errors = []
            validate_repo.check_md_links(td, errors)
            return errors

    def test_missing_target_flagged(self):
        errors = self._check("[x](./nope.md) [y](./also-missing/)", {})
        self.assertEqual(len(errors), 2)
        self.assertIn("README.md", errors[0])

    def test_existing_file_and_dir_pass(self):
        errors = self._check("[x](./a.md) [d](./examples/)",
                             {"a.md": "hi", "examples/": ""})
        self.assertEqual(errors, [])


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
        n, errors = self._check('<img src="assets/landing/gone.jpg">', {})
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


class SyntaxGateTests(unittest.TestCase):
    """py / json 语法门的正负例（yml 门依赖 PyYAML，由 CI 环境覆盖，此处不重复）。"""

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

    @unittest.skipUnless(validate_repo._find_git(), "无 git 环境")
    def test_repo_self_check_green(self):
        self.assertEqual(validate_repo.main(), 0)


if __name__ == "__main__":
    unittest.main()
