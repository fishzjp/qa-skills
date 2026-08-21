#!/usr/bin/env bash
# uninstall.sh — 卸载 install.sh 安装的 qa-skills
#
# 用法：
#   ./uninstall.sh --target <目录>    卸载指定目录下的 qa-skills
#   ./uninstall.sh                    交互选择（同 install 的检测逻辑）
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIRS=(
  qa core
  requirement-analysis test-strategy test-case-writing test-case-review
  automated-e2e-testing api-testing exploratory-testing bug-analysis regression-testing
)
SRC_ROOT="$REPO_ROOT/skills"

usage() { sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

TARGET=""
while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:?--target 需要一个目录参数}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "未知参数: $1" >&2; usage ;;
  esac
done

if [ -z "$TARGET" ]; then
  cands=()
  [ -d "$HOME/.agents/skills/qa" ] && cands+=("$HOME/.agents/skills")
  [ -d "$HOME/.claude/skills/qa" ] && cands+=("$HOME/.claude/skills")
  [ -d "$HOME/.codex/skills/qa" ] && cands+=("$HOME/.codex/skills")
  [ -d "$REPO_ROOT/.claude/skills/qa" ] && cands+=("$REPO_ROOT/.claude/skills")
  if [ "${#cands[@]}" -eq 0 ]; then echo "未发现已安装的 qa-skills。"; exit 0; fi
  if [ "${#cands[@]}" -eq 1 ]; then TARGET="${cands[0]}"; else
    echo "检测到多处安装，选择要卸载的："
    i=1; for c in "${cands[@]}"; do echo "  $i) $c"; i=$((i + 1)); done
    read -r -p "序号 [1]: " idx; TARGET="${cands[$((${idx:-1} - 1))]}"
  fi
fi

[ -d "$TARGET" ] || { echo "❌ 目录不存在: $TARGET" >&2; exit 1; }

echo "将从 $TARGET 卸载："
for d in "${SKILL_DIRS[@]}"; do
  [ -e "$TARGET/$d" ] || [ -L "$TARGET/$d" ] || continue
  # 防误删：确认是我们装的（软链指向本仓库，或目录里有 SKILL.md/为 core）
  if [ -L "$TARGET/$d" ]; then
    [ "$(readlink "$TARGET/$d")" = "$SRC_ROOT/$d" ] || { echo "  跳过 ${d}（软链不指向本仓库）"; continue; }
  elif [ "$d" = "core" ]; then
    :
  elif [ ! -f "$TARGET/$d/SKILL.md" ]; then
    echo "  跳过 ${d}（非 skill 目录）"; continue
  fi
  rm -rf "$TARGET/$d"; echo "  移除 $d"
done
[ -f "$TARGET/qa-skills.VERSION" ] && rm -f "$TARGET/qa-skills.VERSION"
echo "✅ 卸载完成（其余 skill 未动）"