"""Static-language and release-artifact contracts; no browser/model needed."""
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_site', REPO / 'scripts/build_site.py')
build_site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_site)


class SiteBuildTests(unittest.TestCase):
    def test_english_has_static_identity_canonical_and_alternates(self):
        source = (REPO / 'index.html').read_text(encoding='utf-8')
        page = build_site.render(source, True)
        self.assertIn('<html lang="en" class="lang-en">',page)
        self.assertIn('<title>' + build_site.EN_TITLE + '</title>',page)
        self.assertIn('rel="canonical" href="' + build_site.BASE + 'en/"',page)
        for language in ['zh-CN','en','x-default']:
            self.assertIn(f'hreflang="{language}"',page)
        self.assertIn('href="../assets/fonts/',page)
        schemas = [json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>',page,re.S)]
        self.assertTrue(schemas)
        self.assertEqual(schemas[0]['inLanguage'],'en')
        self.assertFalse(any(x.get('@type')=='FAQPage' for x in schemas))

    def test_artifact_contains_only_public_site_payload_and_font_license(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_site.build(root)
            self.assertEqual({p.name for p in root.iterdir()},
                             {'index.html','en','assets','og.jpg','llms.txt','sitemap.xml'})
            self.assertEqual((root/'assets/fonts/OFL.txt').read_bytes(), (REPO/'assets/fonts/OFL.txt').read_bytes())
            self.assertTrue((root/'en/index.html').is_file())
            self.assertIn(build_site.BASE+'en/',(root/'sitemap.xml').read_text())

    def test_refuses_nonempty_output_without_deleting_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'private.txt').write_text('retain')
            with self.assertRaises(ValueError):
                build_site.build(root)
            self.assertEqual((root/'private.txt').read_text(),'retain')

    def test_refuses_source_tree_as_output(self):
        for path in [REPO, REPO/'skills/generated-site',REPO/'docs/generated-site']:
            with self.assertRaises(ValueError):
                build_site.build(path)

    def test_refuses_symlink_output_without_writing_to_its_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / 'destination'
            destination.mkdir()
            alias = root / 'alias'
            alias.symlink_to(destination, target_is_directory=True)
            with self.assertRaises(ValueError):
                build_site.build(alias)
            self.assertEqual(list(destination.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
