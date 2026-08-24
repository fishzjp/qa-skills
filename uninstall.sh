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

usage() { sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

TARGET=""
while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:?--target 需要一个目录参数}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "未知参数: $1" >&2; usage ;;
  esac
done

if [ -z "$TARGET" ]; then
  # 与 install 检测口径对称：qa / core / 版本标记任一存在即视为装过（防"删了 qa 留下其余"后无法卸载）
  installed_in() { [ -d "$1/qa" ] || [ -d "$1/core" ] || [ -f "$1/qa-skills.VERSION" ]; }
  cands=()
  installed_in "$HOME/.agents/skills" && cands+=("$HOME/.agents/skills")
  installed_in "$HOME/.claude/skills" && cands+=("$HOME/.claude/skills")
  installed_in "$HOME/.codex/skills" && cands+=("$HOME/.codex/skills")
  installed_in "$REPO_ROOT/.claude/skills" && cands+=("$REPO_ROOT/.claude/skills")
  if [ "${#cands[@]}" -eq 0 ]; then echo "未发现已安装的 qa-skills。"; exit 0; fi
  if [ "${#cands[@]}" -eq 1 ]; then TARGET="${cands[0]}"; else
    echo "检测到多处安装，选择要卸载的："
    i=1; for c in "${cands[@]}"; do echo "  $i) $c"; i=$((i + 1)); done
    read -r -p "序号 [1]: " idx || idx=""; idx="${idx:-1}"
    case "$idx" in ''|*[!0-9]*) echo "无效序号: $idx" >&2; exit 1 ;; esac
    if [ "$idx" -lt 1 ] || [ "$idx" -gt "${#cands[@]}" ]; then
      echo "序号超出范围: ${idx}（可选 1-${#cands[@]}）" >&2; exit 1
    fi
    TARGET="${cands[$((idx - 1))]}"
  fi
fi

[ -d "$TARGET" ] || { echo "❌ 目录不存在: $TARGET" >&2; exit 1; }

# 防自毁：目标是本仓库 skills/ 源目录（或其内）时直接拒绝
TARGET_ABS="$(cd "$TARGET" && pwd)"
case "$TARGET_ABS" in
  "$SRC_ROOT"|"$SRC_ROOT"/*)
    echo "❌ 拒绝：目标目录是本仓库的 skills/ 源目录。" >&2; exit 1 ;;
esac

# 防误删：显式 --target 且目录内无版本标识时要求确认（交互检测路径已由 installed_in 把关）
if [ ! -f "$TARGET/qa-skills.VERSION" ]; then
  echo "注意：${TARGET} 下未发现 qa-skills.VERSION 版本标识（手动 cp 安装，或该目录本就不含 qa-skills）。"
  echo "将移除以下同名目录（存在且通过归属校验时）：${SKILL_DIRS[*]}"
  read -r -p "继续卸载? [y/N] " ans || ans=""
  case "${ans:-N}" in [yY]) ;; *) echo "已取消。"; exit 0 ;; esac
fi

echo "将从 $TARGET 卸载："
for d in "${SKILL_DIRS[@]}"; do
  [ -e "$TARGET/$d" ] || [ -L "$TARGET/$d" ] || continue
  # 防误删：确认是我们装的（软链指向本仓库，或目录里有 SKILL.md/为 core）
  if [ -L "$TARGET/$d" ]; then
    [ "$(readlink "$TARGET/$d")" = "$SRC_ROOT/$d" ] || { echo "  跳过 ${d}（软链不指向本仓库）"; continue; }
  elif [ "$d" = "core" ]; then
    # core 无 SKILL.md，用本框架特有文件识别，防误删目标目录下同名无关目录
    if [ ! -f "$TARGET/$d/evidence.md" ] || [ ! -f "$TARGET/$d/report-template.md" ]; then
      echo "  跳过 ${d}（非本框架 core 目录）"; continue
    fi
  elif [ ! -f "$TARGET/$d/SKILL.md" ]; then
    echo "  跳过 ${d}（非 skill 目录）"; continue
  fi
  rm -rf "$TARGET/$d"; echo "  移除 $d"
done
[ -f "$TARGET/qa-skills.VERSION" ] && rm -f "$TARGET/qa-skills.VERSION"
echo "✅ 卸载完成（其余 skill 未动）"