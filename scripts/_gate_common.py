#!/usr/bin/env python3
"""守门脚本共享件：git 定位与 markdown/html 本地引用提取.

validate_skills.py 与 validate_repo.py 的单一实现——链接提取逻辑此前在两个脚本各写一份，
宽严已经漂移过一次（query 剥离与 URL 解码只有仓库面有）；再出现第三种引用形态时只改这里。
"""
import re
import shutil
from pathlib import Path
from urllib.parse import unquote

MD_LINK_PATTERN = re.compile(r'\]\(([^()\s]+)(?:\s+"[^"]*")?\)')
# 引用式链接定义：行首（≤3 空格）[label]: target——两个校验器此前都漏查这种形态。
# 排除脚注（[^1]: …）与 wiki 外的误匹配；容许可选 ! 前缀（图片定义）与尾随 title
MD_REF_DEF_PATTERN = re.compile(
    r'^ {0,3}!?\[(?!\^)[^\]]+\]:\s*<?(\S+?)>?(?:\s+"[^"]*")?\s*$', re.M)
HTML_ATTR_PATTERN = re.compile(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']')
SRCSET_PATTERN = re.compile(r'srcset\s*=\s*["\']([^"\']+)["\']')
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#", "data:")
_FENCE_OPEN = re.compile(r'^ {0,3}(```|~~~)')


def mask_fenced(text):
    """把 fenced code block（``` / ~~~）内的行替换为空行（保留行号），返回掩码后文本。

    docstring 承诺"代码块内示例不在校验范围"——引用提取与反引号引用检查都应基于
    掩码文本，否则围栏内的示例链接/路径定义会被误报。
    """
    out, in_fence = [], None
    for line in text.split("\n"):
        m = _FENCE_OPEN.match(line)
        if in_fence is None:
            if m:
                in_fence = m.group(1)
                out.append("")
            else:
                out.append(line)
        else:
            out.append("")
            if m and m.group(1) == in_fence:
                in_fence = None
    return "\n".join(out)


def visible_lines(text):
    """[(行号, 行)]——跳过 fenced code block 内的行（行号保持原文位置）。"""
    out, in_fence = [], None
    for i, line in enumerate(text.split("\n"), 1):
        m = _FENCE_OPEN.match(line)
        if in_fence is None:
            if m:
                in_fence = m.group(1)
            else:
                out.append((i, line))
        elif m and m.group(1) == in_fence:
            in_fence = None
    return out


def find_git():
    """定位 git 可执行文件：优先 PATH，退化到 macOS 常见绝对路径；均不存在返回 None。"""
    git = shutil.which("git")
    if git:
        return git
    for cand in ("/usr/bin/git", "/usr/local/bin/git", "/opt/homebrew/bin/git"):
        if Path(cand).exists():
            return cand
    return None


def extract_local_refs(text):
    """提取文本中的本地相对引用 → [(行号, 原文, 路径)].

    覆盖四种形态：md 行内链接 ](...)、md 引用式定义 [x]: path、html src/href、
    srcset（按逗号拆候选取每个候选的首个 URL，分辨率描述符丢弃）。
    fenced code block 内的内容一律跳过；外链 / 锚点 / data: 跳过；
    路径剥离锚点与查询串并做 URL 解码（%20 等空格路径）。
    """
    text = mask_fenced(text)
    hits = []
    for pattern in (MD_LINK_PATTERN, MD_REF_DEF_PATTERN, HTML_ATTR_PATTERN, SRCSET_PATTERN):
        for m in pattern.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            if pattern is SRCSET_PATTERN:
                cands = [c.strip().split()[0] for c in m.group(1).split(",") if c.strip()]
            else:
                cands = [m.group(1)]
            for c in cands:
                hits.append((line, c))
    out = []
    for line, ref in hits:
        if ref.startswith(SKIP_PREFIXES):
            continue
        path = unquote(ref.split("#", 1)[0].split("?", 1)[0])
        if not path:
            continue
        out.append((line, ref, path))
    return out
