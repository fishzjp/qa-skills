#!/usr/bin/env python3
"""Skills 架构红线校验（CI 核心，也可本地跑）.

对齐 CONTRIBUTING.md 的架构红线与提交前自检：
  1. 每个 skill 目录的 SKILL.md frontmatter 含 name（与目录名一致）与 description
  2. SKILL.md ≤ 500 行（L2 工作流红线）
  3. 每个 skill 必须有 "When NOT to Use" 段（反触发边界）
  4. core/ 不含 SKILL.md（纯共享引用目录）
  5. SKILL.md 与 core/*.md 中反引号引用的仓库内相对路径必须存在
     （识别 `../`、`references/`、`templates/`、`core/` 前缀；兼容 core 文件的
     skills 根相对写法；中文产物名与代码块内示例不在校验范围）
  6. eval/harness/*.json 与 eval/golden/*/annotation.json 必须是合法 JSON

用法：python3 scripts/validate_skills.py （仓库根或任意目录均可）
退出码：0 通过 / 1 有违规
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO / "skills"   # 产品本体（10 个 skill + core/ 共享库）统一在此
MAX_LINES = 500
REF_PATTERN = re.compile(r"`((?:\.\./|references/|templates/|core/)[\w./-]+\.(?:md|json|py|ts|tsx|ya?ml))`")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def skill_dirs():
    return sorted(d for d in SKILLS_ROOT.iterdir()
                  if d.is_dir() and (d / "SKILL.md").exists())


def check_frontmatter(text, dirname, errors):
    m = FRONTMATTER.match(text)
    if not m:
        errors.append(f"{dirname}/SKILL.md: 缺少 frontmatter（--- name/description ---）")
        return
    fm = m.group(1)
    name = re.search(r"^name:\s*(.+)$", fm, re.M)
    desc = re.search(r"^description:\s*(.+)$", fm, re.M)
    if not name:
        errors.append(f"{dirname}/SKILL.md: frontmatter 缺 name")
    elif name.group(1).strip() != dirname:
        errors.append(f"{dirname}/SKILL.md: name '{name.group(1).strip()}' 与目录名 '{dirname}' 不一致")
    if not desc or len(desc.group(1).strip()) < 20:
        errors.append(f"{dirname}/SKILL.md: frontmatter 缺 description 或过短（需含触发词与反触发，≥20 字）")


def check_references(md_path, errors):
    text = md_path.read_text()
    # 去掉代码围栏内容？——保留：架构树等代码块内的 references/ 引用同样应有效
    for m in REF_PATTERN.finditer(text):
        ref = m.group(1)
        if (md_path.parent / ref).resolve().exists():
            continue
        if (SKILLS_ROOT / ref).resolve().exists():  # core 文件内的 skills 根相对写法（core/xxx.md）
            continue
        errors.append(f"{md_path.relative_to(REPO)}: 引用的文件不存在 `{ref}`")


def main():
    errors = []

    # 红线 4：core/ 不含 SKILL.md
    if (SKILLS_ROOT / "core" / "SKILL.md").exists():
        errors.append("skills/core/SKILL.md 存在——core/ 必须是纯共享引用目录，不得含 SKILL.md")

    for d in skill_dirs():
        sk = d / "SKILL.md"
        text = sk.read_text()
        # 红线 1：frontmatter
        check_frontmatter(text, d.name, errors)
        # 红线 2：行数
        n = len(text.splitlines())
        if n > MAX_LINES:
            errors.append(f"{d.name}/SKILL.md: {n} 行超过 {MAX_LINES} 行红线（方法细节下沉 references/ 或 core/）")
        # 红线 3：When NOT to Use
        if "When NOT to Use" not in text:
            errors.append(f"{d.name}/SKILL.md: 缺 'When NOT to Use' 段（须指明交给哪个 skill）")
        check_references(sk, errors)

    # 红线 5：core/*.md 的引用
    for md in sorted((SKILLS_ROOT / "core").glob("*.md")):
        check_references(md, errors)

    # JSON 合法性（harness 配置 + golden 标注；归档运行结果不在此范围）
    for pattern in ("eval/harness/*.json", "eval/golden/*/annotation.json"):
        for f in REPO.glob(pattern):
            try:
                json.loads(f.read_text())
            except json.JSONDecodeError as e:
                errors.append(f"{f.relative_to(REPO)}: 非法 JSON（{e}）")

    skills = skill_dirs()
    print(f"校验 {len(skills)} 个 skill + core/ {len(list((SKILLS_ROOT / 'core').glob('*.md')))} 个共享文档")
    if errors:
        print(f"\n❌ {len(errors)} 处违规：")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("✅ 架构红线全部通过（frontmatter / ≤500 行 / When NOT to Use / core 纯引用 / 引用完整 / JSON 合法）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
