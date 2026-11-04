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
        faq = next(x for x in schemas if x.get('@type') == 'FAQPage')
        self.assertEqual(faq['inLanguage'], 'en')
        self.assertEqual(len(faq['mainEntity']), 6)
        self.assertEqual(faq['mainEntity'][0]['name'], 'What is qa-skills? Does it cost money?')

    def test_localized_content_and_sharing_metadata_match_each_route(self):
        source = (REPO / 'index.html').read_text(encoding='utf-8')
        for english in (False, True):
            page = build_site.render(source, english)
            parser = build_site.FAQContent()
            parser.feed(page[page.index('<section class="section" id="faq">'):page.index('<section class="section" id="install">')])
            schemas = [json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>',page,re.S)]
            faq = next(x for x in schemas if x.get('@type') == 'FAQPage')
            self.assertEqual([q['acceptedAnswer']['text'] for q in faq['mainEntity']], parser.answers)
            self.assertEqual([q['name'] for q in faq['mainEntity']], parser.questions)
            self.assertEqual(len(parser.answers), 6)
            self.assertNotRegex(page, r'class="[^\"]*\b' + ('zh-only' if english else 'en-only') + r'\b')
            if english:
                self.assertIn('name="twitter:title" content="' + build_site.EN_TITLE, page)
                self.assertIn('name="twitter:description" content="' + build_site.EN_DESCRIPTION, page)
                self.assertIn('property="og:locale:alternate" content="zh_CN"', page)
            for skill in (REPO / 'skills').glob('*/SKILL.md'):
                if skill.parent.name != 'core':
                    self.assertIn('https://github.com/fishzjp/qa-skills/tree/main/skills/' + skill.parent.name + '"', page)

    def test_localization_preserves_nested_markup_entities_void_elements_and_scripts(self):
        parser = build_site.LocalizedHTML(True)
        parser.feed('<!DOCTYPE html><div class="zh-only"><b>隐藏</b><br><img src="x"></div><p class="en-only">API &amp; QA<br><svg><path /></svg></p><script>if (a < b) x();</script>')
        self.assertEqual(''.join(parser.output), '<!DOCTYPE html><p class="en-only">API &amp; QA<br><svg><path /></svg></p><script>if (a < b) x();</script>')

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
