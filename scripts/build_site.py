#!/usr/bin/env python3
"""Build static Chinese/English pages from one source; never copy private files.

Usage: python3 scripts/build_site.py [--output _site]
The source remains bilingual for editing and validation. Each output has its own
initial language, title, canonical and alternates without depending on JavaScript.
"""
import argparse
import json
from pathlib import Path
import re
import shutil

REPO = Path(__file__).resolve().parents[1]
BASE = "https://fishzjp.github.io/qa-skills/"
EN_TITLE = "qa-skills — Testing skills for AI coding agents"
EN_DESCRIPTION = "Testing skills for AI coding agents: evidence-backed strategy, executable cases, Playwright/API testing, regression and QA memory. Installation and effect limits are documented."


def render(source, english=False):
    url = BASE + ("en/" if english else "")
    html = re.sub(r'<link rel="canonical"[^>]+>', f'<link rel="canonical" href="{url}">', source)
    html = html.replace('</head>', f'<link rel="alternate" hreflang="zh-CN" href="{BASE}">\n<link rel="alternate" hreflang="en" href="{BASE}en/">\n<link rel="alternate" hreflang="x-default" href="{BASE}">\n</head>')
    html = re.sub(r'(<meta property="og:url" content=")[^"]+', r'\g<1>' + url, html)
    if english:
        html = html.replace('<html lang="zh-CN">', '<html lang="en" class="lang-en">')
        html = re.sub(r'<title>.*?</title>', f'<title>{EN_TITLE}</title>', html)
        for name, value in [('name="description"', EN_DESCRIPTION), ('property="og:title"', EN_TITLE), ('property="og:description"', EN_DESCRIPTION), ('property="og:locale"','en_US')]:
            html = re.sub(r'(<meta ' + name + r' content=")[^"]*', lambda m: m[1] + value, html)
        html = html.replace('href="assets/', 'href="../assets/').replace('url("assets/', 'url("../assets/')
        html = html.replace('class="nav-lang" href="en/"', 'class="nav-lang" href="../"')
        # Avoid presenting a Chinese FAQ schema as the English page's answers.
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
