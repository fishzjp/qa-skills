#!/usr/bin/env python3
"""Build static Chinese/English pages from one source; never copy private files.

Usage: python3 scripts/build_site.py [--output _site]
The source remains bilingual for editing and validation. Each output has its own
initial language, title, canonical and alternates without depending on JavaScript.
"""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil

REPO = Path(__file__).resolve().parents[1]
BASE = "https://fishzjp.github.io/qa-skills/"
EN_TITLE = "qa-skills — Testing skills for AI coding agents"
EN_DESCRIPTION = "13 open-source testing skills for Claude Code, Codex and AI agents. Design test cases, review coverage, automate Playwright and API tests. Explore examples and install."


class LocalizedHTML(HTMLParser):
    """Keep the source bilingual, but ship only each route's own language.

    Preserve raw markup, scripts, SVG and entities; skip whole inactive subtrees.
    """
    VOID = set('area base br col embed hr img input link meta param source track wbr'.split())

    def __init__(self, english):
        super().__init__(convert_charrefs=False)
        self.inactive = 'zh-only' if english else 'en-only'
        self.depth = 0
        self.output = []

    def handle_starttag(self, tag, attrs):
        skip = self.inactive in (dict(attrs).get('class') or '').split()
        if self.depth or skip:
            if tag not in self.VOID:
                self.depth += 1
        else:
            self.output.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if self.depth:
            if tag not in self.VOID:
                self.depth -= 1
        else:
            self.output.append(f'</{tag}>')

    def handle_startendtag(self, tag, attrs):
        if not self.depth and self.inactive not in (dict(attrs).get('class') or '').split():
            self.output.append(self.get_starttag_text())

    def handle_data(self, data):
        if not self.depth:
            self.output.append(data)

    def handle_entityref(self, name):
        self.handle_data('&' + name + ';')

    def handle_charref(self, name):
        self.handle_data('&#' + name + ';')

    def handle_comment(self, data):
        if not self.depth:
            self.output.append('<!--' + data + '-->')

    def handle_decl(self, data):
        self.output.append('<!' + data + '>')


class FAQContent(HTMLParser):
    """Extract the localized visible FAQ, so schema never drifts from the copy."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.questions = []
        self.answers = []
        self.capture = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'summary' or 'faq-a' in (dict(attrs).get('class') or '').split():
            self.capture = tag
            self.parts = []

    def handle_data(self, data):
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == self.capture:
            target = self.questions if tag == 'summary' else self.answers
            target.append(' '.join(''.join(self.parts).split()))
            self.capture = None


def render(source, english=False):
    url = BASE + ("en/" if english else "")
    html = re.sub(r'<link rel="canonical"[^>]+>', f'<link rel="canonical" href="{url}">', source)
    html = html.replace('</head>', f'<link rel="alternate" hreflang="zh-CN" href="{BASE}">\n<link rel="alternate" hreflang="en" href="{BASE}en/">\n<link rel="alternate" hreflang="x-default" href="{BASE}">\n</head>')
    html = re.sub(r'(<meta property="og:url" content=")[^"]+', r'\g<1>' + url, html)
    if english:
        html = html.replace('<html lang="zh-CN">', '<html lang="en" class="lang-en">')
        html = re.sub(r'<title>.*?</title>', f'<title>{EN_TITLE}</title>', html)
        for name, value in [('name="description"', EN_DESCRIPTION), ('property="og:title"', EN_TITLE), ('property="og:description"', EN_DESCRIPTION), ('name="twitter:title"', EN_TITLE), ('name="twitter:description"', EN_DESCRIPTION), ('property="og:locale"','en_US'), ('property="og:locale:alternate"','zh_CN')]:
            html = re.sub(r'(<meta ' + name + r' content=")[^"]*', lambda m: m[1] + value, html)
        html = html.replace('href="assets/', 'href="../assets/').replace('url("assets/', 'url("../assets/')
        html = html.replace('class="nav-lang" href="en/"', 'class="nav-lang" href="../"')
        html = html.replace('示意图：AI 助手装载 qa-skills 后，把需求一步步转成可执行的测试用例文件',
                            'Workflow illustration: an AI agent uses qa-skills to turn requirements into test case files')
        # Localize software metadata; FAQ is derived from visible copy below.
        def schema(match):
            data = json.loads(match[1])
            if data.get('@type') == 'FAQPage':
                return ''
            data['url'] = url
            data['description'] = EN_DESCRIPTION
            data['inLanguage'] = 'en'
            # Keep Chinese-only feature strings out of English structured data.
            data.pop('featureList', None)
            return '<script type="application/ld+json">\n' + json.dumps(data,ensure_ascii=False,indent=2) + '\n</script>'
        html = re.sub(r'<script type="application/ld\+json">(.*?)</script>', schema, html, flags=re.S)
    localized = LocalizedHTML(english)
    localized.feed(html)
    html = ''.join(localized.output)
    faq = FAQContent()
    faq.feed(html[html.index('<section class="section" id="faq">'):html.index('<section class="section" id="install">')])
    if len(faq.questions) != len(faq.answers) or not faq.questions:
        raise ValueError('FAQ questions and answers must be paired.')
    data = {'@context': 'https://schema.org', '@type': 'FAQPage', 'inLanguage': 'en' if english else 'zh-CN',
            'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}}
                           for q, a in zip(faq.questions, faq.answers)]}
    html = html.replace('</head>', '<script type="application/ld+json">\n' + json.dumps(data, ensure_ascii=False).replace('<', '\\u003c') + '\n</script>\n</head>')
    return html


def build(output):
    if output.is_symlink():
        raise ValueError('Output must not be a symlink.')
    output = output.resolve()
    if output == REPO or REPO in output.parents and output != REPO / '_site':
        raise ValueError('Use the default _site or an output directory outside the checkout.')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be empty; use a fresh directory to avoid stale/private artifacts.')
    output.mkdir(parents=True,exist_ok=True)
    (output / 'en').mkdir(exist_ok=True)
    source = (REPO / 'index.html').read_text(encoding='utf-8')
    (output / 'index.html').write_text(render(source),encoding='utf-8')
    (output / 'en/index.html').write_text(render(source,True),encoding='utf-8')
    (output / 'llms.txt').write_bytes((REPO / 'llms.txt').read_bytes())
    (output / 'og.jpg').write_bytes((REPO / 'assets/og.jpg').read_bytes())
    (output / 'assets').mkdir(exist_ok=True)
    shutil.copytree(REPO / 'assets/fonts', output / 'assets/fonts', dirs_exist_ok=True)
    (output / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'<url><loc>{BASE}{suffix}</loc></url>\n' for suffix in ['', 'en/']) + '</urlset>\n',encoding='utf-8')
    print(f'Built static zh/en pages, sitemap, llms and licensed fonts: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=REPO / '_site')
    build(parser.parse_args().output)
