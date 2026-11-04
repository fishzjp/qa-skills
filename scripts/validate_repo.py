#!/usr/bin/env python3
"""仓库面守门（CI 第二道门，与 skills 内容红线 validate_skills.py 分工）.

validate_skills 守 skills/ 内容架构；本脚本守"仓库机体"——5 个此前无人机查、坏了照绿的面：
  1. Python 语法：git 跟踪的全部 .py 可编译（此前只有被单测导入的脚本被覆盖，
     新增脚本写错语法 CI 照绿）
  2. YAML 合法性：git 跟踪的全部 .yml/.yaml 可解析（ci/pages workflow、labeler、
     ISSUE 模板、dsh cordis 补丁）。语法坏掉的 pages.yml 这类 paths 触发的 workflow
     会静默不跑且没有红叉——最典型的骗绿形态
  3. JSON 合法性：git 跟踪的全部 .json（package.json）
  4. 门面文档相对链接：git 跟踪的全部 .md（README 双语 / CONTRIBUTING / RELEASING /
     CHANGELOG / AGENTS / examples / .github 模板）的 ](...) 链接与 <img src> /
     <source srcset> 的本地目标必须存在（外链、锚点、data: 跳过；此前只扫根目录
     *.md，examples/ 与 .github/ 处于门禁真空——2026-10-10 对抗审查）
  5. 落地页资产：index.html 引用的本地 src/href/srcset 必须存在。pages.yml 只负责搬运
     （cp 不校验引用完整性），引用了不存在的配图 = CI 绿、线上破图
  6. 落地页静态双语对：index.html 的 zh-only / en-only 计数相等且序列相邻交替
     （成对性此前只活在提交信息里的人工实测，缺一半照绿——2026-10-10 对抗审查）
  7. 落地页 JSON-LD softwareVersion 与 package.json version 一致
     （GEO 层机器可读事实不得陈旧，曾停更两个版本）

无 git 环境时 git 类校验显式打印跳过（不静默假绿）；未装 PyYAML 时 YAML 门 **FAIL 而非跳过**
（2026-09-03 骗绿事故后的纪律：门禁缺依赖 = 门没跑 = 不能绿。CI 由「安装测试依赖」步骤保证）。
用法：python3 scripts/validate_repo.py（仓库根或任意目录均可）
退出码：0 通过 / 1 有违规
"""
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gate_common import extract_local_refs, fence_error, find_git  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def tracked_files(suffixes, errors):
    """git ls-files 枚举跟踪文件并按后缀过滤；无 git 返回 None（调用方显式跳过）。"""
    git = find_git()
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
        # 门禁缺依赖 = 门没跑 = 不能绿（2026-09-03 validate_schema 降级骗绿事故同族）。
        # CI 由「安装测试依赖」步骤保证；本地裸环境 pip install pyyaml 后重跑。
        errors.append("未安装 PyYAML——YAML 合法性门无法执行（pip install pyyaml 后重跑；"
                      "workflow 由「安装测试依赖」步骤保证）")
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


def check_md_links(root, files, errors):
    """git 跟踪全部 .md 的本地链接 / 图片目标存在性（相对基准 = 文件所在目录；
    前导 / 的目标按仓库根基准——GitHub 渲染语义，此前误按文件所在目录误报；
    无 git 时退化只扫根目录 *.md，显式打印跳过面）。
    附带围栏闭合自检：未闭合围栏会让其后链接静默逃检（本批扩面自带的缺口，
    2026-10-10 二轮对抗审查实测构造确认）。"""
    if files is None:
        files = [p.name for p in sorted(root.glob("*.md"))]
        print("(i) 未检出 git——md 链接校验只扫根目录（examples/、.github/ 等不在范围）")
    n = 0
    for rel in files:
        md = root / rel
        text = md.read_text(encoding="utf-8-sig")
        fe = fence_error(text)
        if fe:
            errors.append(f"{rel}:{fe[0]}: 未闭合的 fenced code block（{fe[1]}）"
                          "——其后链接静默逃检，先修围栏")
        for line_no, raw, path in extract_local_refs(text):
            n += 1
            base = root if path.startswith("/") else md.parent
            if not (base / path.lstrip("/")).exists():
                errors.append(f"{rel}:{line_no}: 链接目标不存在 ({raw})")
    return n


def check_html_assets(root, errors):
    """index.html 引用的本地资源存在性（落地页只发布 index.html + assets/，引用断了就是线上破图）。"""
    page = root / "index.html"
    if not page.exists():
        print("(i) 未检出 index.html——跳过落地页资产校验")
        return 0
    n = 0
    for line_no, raw, path in extract_local_refs(page.read_text(encoding="utf-8-sig")):
        n += 1
        # Static language route is generated from index.html by the site builder.
        if path == "en/" and (root / "scripts/build_site.py").is_file():
            continue
        if not (root / path.lstrip("/")).exists():
            errors.append(f"index.html:{line_no}: 引用的资源不存在 ({raw})")
    return n


def check_bilingual_pairs(root, errors):
    """落地页静态双语对：zh-only / en-only 元素计数相等且序列相邻交替。

    成对性是"切到 EN 无中文残留"的结构前提——此前只活在发版提交信息里的人工实测，
    缺一半照绿（2026-10-10 对抗审查实测构造确认）。序列按文档出现顺序提取，
    相邻交替破坏（连续两个同类）即报——当前页面全部为相邻兄弟形态，本规则同时
    钉住"新增成对元素必须相邻"的既有设计约定。返回检查的元素总数。
    """
    page = root / "index.html"
    if not page.exists():
        return 0

    class PairScan(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.seq = []
            self.ambiguous = []

        def handle_starttag(self, tag, attrs):
            classes = (dict(attrs).get("class") or "").split()
            kinds = {"zh-only", "en-only"} & set(classes)
            if len(kinds) > 1:
                self.ambiguous.append(self.getpos()[0])
            elif kinds:
                self.seq.append((kinds.pop(), self.getpos()[0]))

    scan = PairScan()
    scan.feed(page.read_text(encoding="utf-8-sig"))
    for line in scan.ambiguous:
        errors.append(f"index.html:{line}: 同一元素同时挂 zh-only 与 en-only（显隐语义自相矛盾）")
    zh = [x for x in scan.seq if x[0] == "zh-only"]
    en = [x for x in scan.seq if x[0] == "en-only"]
    if len(zh) != len(en):
        errors.append(f"index.html: 静态双语对不完整（zh-only {len(zh)} 个 / en-only {len(en)} 个）——"
                      "缺一半时切换语言会残留另一语言内容")
        return len(scan.seq)
    if not zh:
        errors.append("index.html: 未检出 zh-only/en-only 静态双语对（落地页双语结构缺失或被重构）")
        return 0
    for (k1, l1), (k2, l2) in zip(scan.seq, scan.seq[1:]):
        if k1 == k2:
            errors.append(f"index.html:{l2}: 双语对相邻性破坏——连续两个 {k2}（前一个在第 {l1} 行）")
            break
    return len(scan.seq)


def check_jsonld_version(root, errors):
    """index.html JSON-LD softwareVersion 与 package.json version 一致。

    GEO 层的机器可读版本事实不得陈旧（该字段曾停更两个版本——RELEASING §2 已列为
    发版检查项，本门把它从人工检查单机制化为常驻校验）。返回是否执行了比对。
    """
    page = root / "index.html"
    pkg = root / "package.json"
    if not page.exists() or not pkg.exists():
        return False
    # 只在 application/ld+json 块内取值：全文件首个命中会被前方 JS 字面量遮蔽
    # （2026-10-10 二轮对抗审查实测构造：注入 const cfg={"softwareVersion":...} 即骗绿）
    blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        page.read_text(encoding="utf-8-sig"), re.S | re.I)
    found = [v for b in blocks
             for v in re.findall(r'"softwareVersion"\s*:\s*"([^"]+)"', b)]
    try:
        pkg_version = json.loads(pkg.read_text(encoding="utf-8"))["version"]
    except (json.JSONDecodeError, KeyError) as e:
        errors.append(f"package.json: 无法读取版本号（{e}）")
        return True
    if not found:
        errors.append("index.html: 缺 JSON-LD softwareVersion 字段（GEO 层机器可读版本事实）")
    elif len(found) > 1 and len(set(found)) > 1:
        errors.append(f"index.html: 多个 JSON-LD 块的 softwareVersion 不一致（{sorted(set(found))}）")
    elif found[0] != pkg_version:
        errors.append(f"index.html: JSON-LD softwareVersion '{found[0]}' 与 package.json '{pkg_version}'"
                      " 不一致（定版时随版本号同步）")
    return True


def main():
    errors = []
    n_py = n_yml = n_json = n_md = n_html = n_pair = 0

    py_files = tracked_files((".py",), errors)
    if py_files is None:
        if not find_git():
            print("(i) 未检出 git——Python 语法校验跳过")
    else:
        n_py = check_python(REPO, py_files, errors)

    yml_files = tracked_files((".yml", ".yaml"), errors)
    if yml_files is not None:
        n_yml = check_yaml(yml_files, errors)

    json_files = tracked_files((".json",), errors)
    if json_files is not None:
        n_json = check_json(json_files, errors)

    md_files = tracked_files((".md",), errors)
    n_md = check_md_links(REPO, md_files, errors)
    n_html = check_html_assets(REPO, errors)
    n_pair = check_bilingual_pairs(REPO, errors)
    check_jsonld_version(REPO, errors)

    print(f"仓库面守门：py {n_py} 个 / yml {n_yml} 个 / json {n_json} 个 / "
          f"门面文档链接目标 {n_md} 个 / 落地页引用 {n_html} 个 / 双语对元素 {n_pair} 个")
    if errors:
        print(f"\n❌ {len(errors)} 处违规：")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("✅ 仓库面守门全部通过（py 语法 / yml 合法性 / json 合法性 / 全量 md 链接 / "
          "落地页资产 / 静态双语对 / JSON-LD 版本一致）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
