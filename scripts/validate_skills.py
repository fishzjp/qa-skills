#!/usr/bin/env python3
"""Skills 架构红线校验（CI 核心，也可本地跑）.

对齐 CONTRIBUTING.md 的架构红线与提交前自检：
  1. 每个 skill 目录的 SKILL.md frontmatter 含 name（与目录名一致）与 description（≤300 字符）
  2. SKILL.md ≤ 500 行（L2 工作流红线）
  3. 每个 skill 必须有 "When NOT to Use" 段（反触发边界）
  4. core/ 为纯共享引用层：SKILL.md 仅作安装依赖单元，必须声明不独立触发
  5. 引用的仓库内路径必须存在。识别三种形态：
     a) 反引号 + 前缀引用：`../`、`references/`、`templates/`、`core/`（SKILL.md 与全库），
        兼容 core 文件的 skills 根相对写法
     b) 反引号 + 文件相对裸引用：core/**/*.md 内的 `x.md`、`methods/x.md`、`../x.md`
     c) markdown 链接 / 图片：](path.md) 形态（全 skills 范围；外链与纯锚点跳过）
     中文产物名与代码块内示例不在校验范围
  6. 禁止跨 skill 引用：任何 skill 的文件不得引用兄弟 skill 目录内的文件——
     被多 skill 消费的方法/格式/规则一律下沉 core/（skill 自包含红线）
  7. 各 SKILL.md frontmatter 的 version 必须与 package.json 一致（三处同步的机械防线）
  8. eval/harness/*.json 与 eval/golden/*/annotation.json 必须是合法 JSON
  9. 产品自包含：skills/ 内不得引用 eval/ 等本地评测链路路径（公开分发面 = skills 产品本体）
 10. 跟踪面白名单：git 跟踪的每个文件必须落在白名单内（根目录既有文件 + 产品目录前缀 + docs 三例外）——
     临时文件、测试数据、实验报告、开发报告、开发计划等与 skills 无关的内容不得入库

用法：python3 scripts/validate_skills.py （仓库根或任意目录均可）
退出码：0 通过 / 1 有违规
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO / "skills"   # 产品本体（10 个 skill + core/ 共享库）统一在此
MAX_LINES = 500
MAX_DESC_CHARS = 300
REF_PATTERN = re.compile(r"`((?:\.\./|references/|templates/|core/)[\w./-]+\.(?:md|json|py|ts|tsx|ya?ml))`")
CORE_BARE_PATTERN = re.compile(r"`((?:\.\./)?(?:[\w-]+/)*[\w-]+\.(?:md|py))`")
MD_LINK_PATTERN = re.compile(r'\]\(([^()\s]+)(?:\s+"[^"]*")?\)')
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
MD_EXTS = (".md", ".json", ".py", ".ts", ".tsx", ".yml", ".yaml")

# 红线 10 白名单：白名单制而非黑名单关键词——临时文件命名不可枚举，
# 且 test-case-writing、report-template 等合法文件名含 test/report 字样会被关键词误杀。
# 新增合法产品路径时：同步扩展此处常量并登记 CONTRIBUTING.md 架构红线 8
# docs/ 整目录本地维护（规划文档与设计稿不入库，.gitignore 隔离），不设白名单
ALLOWED_ROOT_FILES = {
    ".gitignore", ".npmignore", "AGENTS.md", "CHANGELOG.md", "CONTRIBUTING.md",
    "LICENSE", "README.en.md", "README.md", "RELEASING.md", "index.html",
    "install.sh", "og.jpg", "package.json", "uninstall.sh",
}
ALLOWED_DIR_PREFIXES = ("skills/", "scripts/", ".github/", ".dsh/", "assets/", "examples/")


def skill_dirs():
    return sorted(d for d in SKILLS_ROOT.iterdir()
                  if d.is_dir() and (d / "SKILL.md").exists())


def owning_skill_dir(path: Path):
    """文件所属的 skill 目录（向上最近的含 SKILL.md 祖先）；core/ 等非 skill 路径返回 None。"""
    for p in path.parents:
        if p == SKILLS_ROOT:
            return None
        if (p / "SKILL.md").exists():
            return p
    return None


def check_frontmatter(text, dirname, errors):
    m = FRONTMATTER.match(text)
    if not m:
        errors.append(f"{dirname}/SKILL.md: 缺少 frontmatter（--- name/description ---）")
        return None
    fm = m.group(1)
    name = re.search(r"^name:\s*(.+)$", fm, re.M)
    desc = re.search(r"^description:\s*(.+)$", fm, re.M)
    if not name:
        errors.append(f"{dirname}/SKILL.md: frontmatter 缺 name")
    elif name.group(1).strip() != dirname:
        errors.append(f"{dirname}/SKILL.md: name '{name.group(1).strip()}' 与目录名 '{dirname}' 不一致")
    if not desc or len(desc.group(1).strip()) < 20:
        errors.append(f"{dirname}/SKILL.md: frontmatter 缺 description 或过短（需含触发词与反触发，≥20 字）")
    elif len(desc.group(1)) > MAX_DESC_CHARS:
        errors.append(f"{dirname}/SKILL.md: description {len(desc.group(1))} 字符超过 {MAX_DESC_CHARS} 上限"
                      "（description 常驻每个会话上下文，机制细节移入正文 When to Use）")
    ver = re.search(r"^version:\s*(.+)$", fm, re.M)
    return ver.group(1).strip() if ver else None


def check_target(md_path, ref, errors):
    """引用目标存在性 + 跨 skill 红线（红线 6）。"""
    src_owner = owning_skill_dir(md_path)
    target = (md_path.parent / ref)
    if not target.exists():
        target = (SKILLS_ROOT / ref)  # core 文件内的 skills 根相对写法（历史兼容）
    if not target.exists():
        errors.append(f"{md_path.relative_to(REPO)}: 引用的文件不存在 `{ref}`")
        return
    target = target.resolve()
    if not target.is_relative_to(SKILLS_ROOT):
        return
    if target.is_relative_to(SKILLS_ROOT / "core"):
        return  # core 共享层：其 SKILL.md 仅为安装依赖单元，不算跨引用
    tgt_owner = owning_skill_dir(target)
    if tgt_owner is not None and tgt_owner != src_owner:
        bad = f"{md_path.relative_to(REPO)}: 跨 skill 引用 `{ref}`（属于 {tgt_owner.name}/）——被多 skill 消费的内容应下沉 core/"
        if bad not in errors:
            errors.append(bad)


def check_references(md_path, errors):
    """反引号引用（前缀形态全库 + 裸相对形态仅 core）。"""
    text = md_path.read_text()
    for m in REF_PATTERN.finditer(text):
        check_target(md_path, m.group(1), errors)
    in_core = md_path.resolve().is_relative_to((SKILLS_ROOT / "core").resolve())
    if in_core:
        for m in CORE_BARE_PATTERN.finditer(text):
            ref = m.group(1)
            if "/" not in ref and not ref.startswith("../"):
                continue  # 纯文件名提及（无路径成分）不强制视为引用，避免误伤术语
            check_target(md_path, ref, errors)


def check_md_links(md_path, errors):
    """markdown 链接 / 图片目标的本地存在性（外链、锚点、含占位符的模板串跳过）。"""
    rel = md_path.relative_to(REPO)
    for m in MD_LINK_PATTERN.finditer(md_path.read_text()):
        raw = m.group(1)
        if raw.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path_part = raw.split("#", 1)[0]
        if not path_part.lower().endswith(MD_EXTS):
            continue
        if any(ch in path_part for ch in "{}<>:*|"):
            continue  # 模板占位符 / 通配描述不在校验范围
        if not (md_path.parent / path_part).exists():
            errors.append(f"{rel}: 链接目标不存在 ({raw})")


def check_versions(errors, versions):
    """红线 7：SKILL.md frontmatter version ↔ package.json 三处同步。

    versions 为 (skill 目录名, frontmatter version 或 None)，由 main 循环
    解析 frontmatter 时顺带收集，避免二次解析。
    """
    pkg = REPO / "package.json"
    if not pkg.exists():
        print("(i) 未检出 package.json——跳过版本一致性校验")
        return
    try:
        pkg_version = json.loads(pkg.read_text())["version"]
    except (json.JSONDecodeError, KeyError) as e:
        errors.append(f"package.json: 无法读取版本号（{e}）")
        return
    for name, v in versions:
        if v != pkg_version:
            errors.append(f"{name}/SKILL.md: frontmatter version '{v}' 与 package.json '{pkg_version}' 不一致"
                          "（发版时三处同步：全部 SKILL.md / package.json / CHANGELOG）")


def _find_git():
    """定位 git 可执行文件：优先 PATH，退化到 macOS 常见绝对路径；均不存在返回 None。"""
    git = shutil.which("git")
    if git:
        return git
    for cand in ("/usr/bin/git", "/usr/local/bin/git", "/opt/homebrew/bin/git"):
        if Path(cand).exists():
            return cand
    return None


def check_tracked_files(errors):
    """红线 10：仓库跟踪面白名单——git ls-files 全量枚举，白名单外即违规。

    无 git 环境时显式打印跳过并明示，避免静默空转假绿。
    """
    git = _find_git()
    if not git:
        print("(i) 未检出 git——跳过跟踪面白名单校验")
        return
    r = subprocess.run([git, "ls-files"], cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        errors.append(f"跟踪面白名单: git ls-files 执行失败（{r.stderr.strip()}）")
        return
    for f in r.stdout.splitlines():
        f = f.strip()
        if not f:
            continue
        if f in ALLOWED_ROOT_FILES or f.startswith(ALLOWED_DIR_PREFIXES):
            continue
        errors.append(f"{f}: 不在跟踪面白名单内——临时文件 / 测试数据 / 实验报告 / 开发报告 / 开发计划"
                      "等与 skills 无关内容禁止入库（确属产品内容：扩展 validate_skills.py 白名单常量"
                      "并在 CONTRIBUTING.md 架构红线 8 登记）")


def main():
    errors = []

    # 红线 4：core/ 是纯共享引用层——SKILL.md 允许存在（作为安装器可识别的依赖单元），
    # 但必须声明"不独立触发"，防止共享知识库被当成面向任务的 skill 使用
    core_sk = SKILLS_ROOT / "core" / "SKILL.md"
    if core_sk.exists():
        core_text = core_sk.read_text()
        if ("不要独立触发" not in core_text) or ("When NOT to Use" not in core_text):
            errors.append("skills/core/SKILL.md: 必须声明不独立触发（description + When NOT to Use 段）")

    versions = []
    for d in skill_dirs():
        sk = d / "SKILL.md"
        text = sk.read_text()
        # 红线 1：frontmatter（返回的 version 供红线 7 一致性检查复用）
        versions.append((d.name, check_frontmatter(text, d.name, errors)))
        # 红线 2：行数
        n = len(text.splitlines())
        if n > MAX_LINES:
            errors.append(f"{d.name}/SKILL.md: {n} 行超过 {MAX_LINES} 行红线（方法细节下沉 references/ 或 core/）")
        # 红线 3：When NOT to Use——锚定真实二级标题形态，
        # 防 code fence 示例或正文顺带提及骗过朴素子串闸
        if not re.search(r"^## +When NOT to Use\s*$", text, re.M):
            errors.append(f"{d.name}/SKILL.md: 缺 '## When NOT to Use' 二级标题段（须指明交给哪个 skill）")
        check_references(sk, errors)

    # 红线 5/6：core/**/*.md 的引用与跨 skill 引用检查
    core_mds = sorted((SKILLS_ROOT / "core").rglob("*.md"))
    for md in core_mds:
        check_references(md, errors)

    # 红线 5c：全库 markdown 链接存在性
    for md in sorted(SKILLS_ROOT.rglob("*.md")):
        check_md_links(md, errors)

    # 红线 7：版本一致性
    check_versions(errors, versions)

    # 红线 9：产品自包含——skills/ 内不得引用 eval/ 等本地评测链路路径
    #（\b 收紧：evaluation / retrieval / medieval 等词不触发）
    for md in sorted(SKILLS_ROOT.rglob("*.md")):
        for i, line in enumerate(md.read_text().splitlines(), 1):
            if re.search(r"\beval/", line, re.IGNORECASE):
                errors.append(f"{md.relative_to(REPO)}:{i}: 引用本地评测链路路径 eval/"
                               "（skills 必须自包含，评测依赖不得进产品）")

    # JSON 合法性（harness 配置 + golden 标注；归档运行结果不在此范围）
    # eval/ 为维护者本地评测链路，公开检出中不存在则跳过并明示，避免静默空转假绿
    checked_json = 0
    for pattern in ("eval/harness/*.json", "eval/golden/*/annotation.json"):
        for f in REPO.glob(pattern):
            checked_json += 1
            try:
                json.loads(f.read_text())
            except json.JSONDecodeError as e:
                errors.append(f"{f.relative_to(REPO)}: 非法 JSON（{e}）")
    if checked_json == 0 and not (REPO / "eval").exists():
        print("(i) 未检出 eval/（本地评测链路不随仓库分发）——跳过 JSON 校验")

    # 红线 10：跟踪面白名单——临时文件 / 测试数据 / 实验·开发报告 / 开发计划等不得入库
    check_tracked_files(errors)

    skills = [d for d in skill_dirs() if d.name != "core"]
    print(f"校验 {len(skills)} 个 skill + core/ {len(core_mds)} 个共享文档")
    if errors:
        print(f"\n❌ {len(errors)} 处违规：")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("✅ 架构红线全部通过（frontmatter / ≤500 行 / When NOT to Use / core 依赖单元声明 / "
          "引用完整含 md 链接 / 无跨 skill 引用 / 版本一致 / JSON 合法 / 无 eval 越界引用 / 跟踪面白名单）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
