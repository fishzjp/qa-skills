#!/usr/bin/env bash
# 安装器行为冒烟（CI 与本地同一入口）：bash tests/install_smoke.sh
# bash -n 只保语法不保行为——本脚本锁住四条真实契约：
#   1. copy 安装完整（单元齐 + core 指纹文件 + 版本标识）
#   2. 重装幂等（覆盖自己装的目录不报错）
#   3. 防误删红线（目标里的同名外来目录必须拒绝覆盖，共享宿主目录的护身符）
#   4. --link 安装为软链且指向本仓库；双向卸载干净（copy 与 link 各一轮）
# 期望单元清单以首次 copy 安装的实际产物为准——install.sh 增删单元自动跟随；
# 仅对单元数设下限，防清单被误删时冒烟"安静地变绿"。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TD="$(mktemp -d)"
trap 'rm -rf "$TD"' EXIT

"$REPO_ROOT/install.sh" --target "$TD/copy" > /dev/null
ls "$TD/copy" | grep -v '^qa-skills.VERSION$' > "$TD/units.txt"
N_UNITS="$(wc -l < "$TD/units.txt" | tr -d ' ')"
[ "$N_UNITS" -ge 12 ] || { echo "❌ 安装单元数 $N_UNITS < 12（11 skill + core），install.sh 清单疑似缺损" >&2; exit 1; }
while IFS= read -r u; do
  [ -f "$TD/copy/$u/SKILL.md" ] || { echo "❌ copy 安装缺少 $u/SKILL.md" >&2; exit 1; }
done < "$TD/units.txt"
[ -f "$TD/copy/core/evidence.md" ] || { echo "❌ copy 安装缺少 core/evidence.md（core 指纹）" >&2; exit 1; }
[ -f "$TD/copy/qa-skills.VERSION" ] || { echo "❌ copy 安装缺少 qa-skills.VERSION 版本标识" >&2; exit 1; }

"$REPO_ROOT/install.sh" --target "$TD/copy" > /dev/null   # 重装幂等

mkdir -p "$TD/guard/qa"
echo "not ours" > "$TD/guard/qa/README.txt"
if "$REPO_ROOT/install.sh" --target "$TD/guard" > /dev/null 2>&1; then
  echo "❌ 防误删失效：覆盖了非本框架的 qa/ 目录" >&2
  exit 1
fi

# 自毁守卫（物理路径口径）：--target 为链进仓库 skills/ 的 symlink 必须拒绝，且源文件毫发无损
mkdir -p "$TD/danger"
ln -s "$REPO_ROOT/skills" "$TD/danger/into-repo"
SENTINEL="$REPO_ROOT/skills/qa/SKILL.md"
if "$REPO_ROOT/install.sh" --target "$TD/danger/into-repo" > /dev/null 2>&1; then
  echo "❌ 自毁守卫失效：symlink 指向仓库 skills/ 未被拒绝" >&2
  exit 1
fi
[ -f "$SENTINEL" ] || { echo "❌ 自毁守卫失效：仓库源文件已被破坏" >&2; exit 1; }
if "$REPO_ROOT/uninstall.sh" --target "$TD/danger/into-repo" > /dev/null 2>&1; then
  echo "❌ 自毁守卫失效：uninstall 对仓库内 symlink 目标未拒绝" >&2
  exit 1
fi
[ -f "$SENTINEL" ] || { echo "❌ 自毁守卫失效：uninstall 破坏了仓库源文件" >&2; exit 1; }

# 自毁守卫（别名路径口径）：仓库本体经 symlink 别名访问时，SRC_ROOT 与 TARGET 解析
# 必须落在同一路径口径上——2026-09-07 二轮审查实测逻辑/物理混用会绕过守卫
ln -s "$REPO_ROOT" "$TD/repo-alias"
if "$TD/repo-alias/install.sh" --target "$TD/repo-alias/skills" > /dev/null 2>&1; then
  echo "❌ 自毁守卫失效：经别名路径把安装目标指回仓库 skills/ 未被拒绝" >&2
  exit 1
fi
[ -f "$SENTINEL" ] || { echo "❌ 自毁守卫失效：别名路径下仓库源文件已被破坏" >&2; exit 1; }

"$REPO_ROOT/install.sh" --target "$TD/link" --link > /dev/null
while IFS= read -r u; do
  [ -L "$TD/link/$u" ] || { echo "❌ --link 安装 $u 不是软链" >&2; exit 1; }
  [ "$(readlink "$TD/link/$u")" = "$REPO_ROOT/skills/$u" ] || { echo "❌ --link 安装 $u 未指向本仓库" >&2; exit 1; }
done < "$TD/units.txt"

"$REPO_ROOT/uninstall.sh" --target "$TD/copy" > /dev/null
"$REPO_ROOT/uninstall.sh" --target "$TD/link" > /dev/null
while IFS= read -r u; do
  for mode in copy link; do
    { [ ! -e "$TD/$mode/$u" ] && [ ! -L "$TD/$mode/$u" ]; } || { echo "❌ 卸载残留 $mode/$u" >&2; exit 1; }
  done
done < "$TD/units.txt"
[ ! -f "$TD/copy/qa-skills.VERSION" ] || { echo "❌ 卸载残留版本标识" >&2; exit 1; }

echo "✅ 安装器冒烟通过（copy/link 安装、重装幂等、防误删拒绝、双向卸载干净，共 $N_UNITS 个单元）"
