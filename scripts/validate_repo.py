#!/usr/bin/env python3
"""仓库面守门（CI 第二道门，与 skills 内容红线 validate_skills.py 分工）.

validate_skills 守 skills/ 内容架构；本脚本守"仓库机体"——5 个此前无人机查、坏了照绿的面：
  1. Python 语法：git 跟踪的全部 .py 可编译（此前只有被单测导入的脚本被覆盖，
     新增脚本写错语法 CI 照绿）
  2. YAML 合法性：git 跟踪的全部 .yml/.yaml 可解析（ci/pages workflow、labeler、
     ISSUE 模板、dsh cordis 补丁）。语法坏掉的 pages.yml 这类 paths 触发的 workflow
     会静默不跑且没有红叉——最典型的骗绿形态
  3. JSON 合法性：git 跟踪的全部 .json（package.json）
  4. 根目录门面文档相对链接：README 双语 / CONTRIBUTING / RELEASING / CHANGELOG / AGENTS
     的 ](...) 链接与 <img src> / <source srcset> 的本地目标必须存在（外链、锚点、
     data: 跳过）。README 是仓库门面，404 直接面向每个访客
  5. 落地页资产：index.html 引用的本地 src/href/srcset 必须存在。pages.yml 只负责搬运
     （cp 不校验引用完整性），引用了不存在的配图 = CI 绿、线上破图

无 git 环境时 git 类校验显式打印跳过（不静默假绿）；未装 PyYAML 时 YAML 门降级跳过并提示
（CI 中由"安装测试依赖"步骤保证全量运行）。
用法：python3 scripts/validate_repo.py（仓库根或任意目录均可）
退出码：0 通过 / 1 有违规
"""
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # 本地裸环境降级；CI 由 workflow 安装 pyyaml 保证全量
    yaml = None

REPO = Path(__file__).resolve().parents[1]

MD_LINK_PATTERN = re.compile(r'\]\(([^()\s]+)(?:\s+"[^"]*")?\)')
HTML_ATTR_PATTERN = re.compile(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']')
SRCSET_PATTERN = re.compile(r'srcset\s*=\s*["\']([^"\']+)["\']')
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#", "data:")


def _find_git():
    """定位 git 可执行文件：优先 PATH，退化到 macOS 常见绝对路径；均不存在返回 None。"""
    git = shutil.which("git")
    if git:
        return git
    for cand in ("/usr/bin/git", "/usr/local/bin/git", "/opt/homebrew/bin/git"):
        if Path(cand).exists():
            return cand
    return None


def tracked_files(suffixes, errors):
    """git ls-files 枚举跟踪文件并按后缀过滤；无 git 返回 None（调用方显式跳过）。"""
    git = _find_git()
    if not git:
        return None
    r = subprocess.run([git, "ls-files", "-z"], cwd=REPO, capture_output=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        errors.append(f"git ls-files 执行失败（{r.stderr.strip()}）")
        return None
    # -z：NUL 分隔输出，关闭 core.quotePath 的非 ASCII 八进制转义（中文路径可读）
    return [f for f in r.stdout.split("\0") if f and f.endswith(tuple(suffixes))]


def check_python(root, files, errors):
    """跟踪 .py 全部可编译；统一 UTF-8（utf-8-sig 容忍 BOM）。"""
    n = 0
    for f in files:
        try:
            text = (root / f).read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as e:
            errors.append(f"{f}: 非 UTF-8 编码（{e}）——Python 源码统一 UTF-8")
            continue
        try:
            compile(text, str(root / f), "exec")
        except SyntaxError as e:
            errors.append(f"{f}: Python 语法错误（行 {e.lineno}：{e.msg}）")
        n += 1
    return n


def check_yaml(files, errors):
    n = 0
    if yaml is None:
        print("(i) 未安装 PyYAML——YAML 合法性校验跳过（pip install pyyaml 启用）")
        return 0
    for f in files:
        try:
            text = (REPO / f).read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as e:
            errors.append(f"{f}: 非 UTF-8 编码（{e}）")
            continue
        try:
            list(yaml.safe_load_all(text))
        except yaml.YAMLError as e:
            errors.append(f"{f}: YAML 解析失败（{str(e).splitlines()[0]}）")
        n += 1
    return n


def check_json(files, errors):
    n = 0
    for f in files:
        try:
            json.loads((REPO / f).read_text(encoding="utf-8-sig"))
        except UnicodeDecodeError as e:
            errors.append(f"{f}: 非 UTF-8 编码（{e}）")
        except json.JSONDecodeError as e:
            errors.append(f"{f}: 非法 JSON（{e}）")
        n += 1
    return n


def local_targets(text):
    """提取文本中的本地相对目标：[(原文, 剥离锚点/查询串并 URL 解码的路径)]。

    外链、锚点、data: 跳过；srcset 值按逗号拆候选、取每个候选的首个 URL（ descriptors 丢弃）。
    """
    refs = []
    refs.extend(m.group(1) for m in MD_LINK_PATTERN.finditer(text))
    refs.extend(m.group(1) for m in HTML_ATTR_PATTERN.finditer(text))
    for m in SRCSET_PATTERN.finditer(text):
        for cand in m.group(1).split(","):
            cand = cand.strip()
            if cand:
                refs.append(cand.split()[0])
    out = []
    for ref in refs:
        if ref.startswith(SKIP_PREFIXES):
            continue
        path = ref.split("#", 1)[0].split("?", 1)[0]
        if not path:
            continue
        out.append((ref, urllib.parse.unquote(path)))
    return out


def check_md_links(root, errors):
    """根目录 *.md 的本地链接 / 图片目标存在性（相对基准 = 仓库根，与站内 ./x.md 写法一致）。"""
    n = 0
    for md in sorted(root.glob("*.md")):
        for raw, path in local_targets(md.read_text(encoding="utf-8-sig")):
            n += 1
            if not (root / path.lstrip("/")).exists():
                errors.append(f"{md.name}: 链接目标不存在 ({raw})")
    return n


def check_html_assets(root, errors):
    """index.html 引用的本地资源存在性（落地页只发布 index.html + assets/，引用断了就是线上破图）。"""
    page = root / "index.html"
    if not page.exists():
        print("(i) 未检出 index.html——跳过落地页资产校验")
        return 0
    n = 0
    for raw, path in local_targets(page.read_text(encoding="utf-8-sig")):
        n += 1
        if not (root / path.lstrip("/")).exists():
            errors.append(f"index.html: 引用的资源不存在 ({raw})")
    return n


def main():
    errors = []
    n_py = n_yml = n_json = n_md = n_html = 0

    py_files = tracked_files((".py",), errors)
    if py_files is None:
        if not _find_git():
            print("(i) 未检出 git——Python 语法校验跳过")
    else:
        n_py = check_python(REPO, py_files, errors)

    yml_files = tracked_files((".yml", ".yaml"), errors)
    if yml_files is not None:
        n_yml = check_yaml(yml_files, errors)

    json_files = tracked_files((".json",), errors)
    if json_files is not None:
        n_json = check_json(json_files, errors)

    n_md = check_md_links(REPO, errors)
    n_html = check_html_assets(REPO, errors)

    print(f"仓库面守门：py {n_py} 个 / yml {n_yml} 个 / json {n_json} 个 / "
          f"门面文档链接目标 {n_md} 个 / 落地页引用 {n_html} 个")
    if errors:
        print(f"\n❌ {len(errors)} 处违规：")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("✅ 仓库面守门全部通过（py 语法 / yml 合法性 / json 合法性 / 门面文档链接 / 落地页资产）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
