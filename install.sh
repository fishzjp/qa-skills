#!/usr/bin/env bash
# install.sh — 把 qa-skills 安装到你的 Agent skills 目录
#
# 用法：
#   ./install.sh                     交互模式：列出检测到的宿主目录供选择
#   ./install.sh --auto              自动安装到第一个检测到的目录（优先级见下）
#   ./install.sh --target <目录>     安装到指定目录
#   ./install.sh --target <目录> --link   用软链代替拷贝（git pull 后即更新，升级方便）
#
# 宿主目录检测优先级：
#   ~/.agents/skills   跨宿主共享目录（多 Agent 共读，推荐；DeepSeek Harness 也读这里）
#   ~/.claude/skills   Claude Code（用户级）
#   ~/.codex/skills    Codex CLI（用户级）
#   ~/.dsh/skills      DeepSeek Harness dsh（用户级）
#   ./.claude/skills   当前项目（Claude Code 项目级）
#
# 卸载：./uninstall.sh --target <目录>（或 --auto 自动选择检测到的安装目录）
set -euo pipefail

# pwd -P 取物理路径：仓库经 symlink 别名访问时逻辑路径与目标解析结果会分叉
# （macOS /tmp→/private/tmp 即系统级实例），防自毁守卫依赖两侧同一套路径口径
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# 安装单元单一真相源：skills/ 下凡含 SKILL.md 的目录即安装单元（含 core/）——
# 新增 / 下线 skill 不需要改本脚本与 uninstall.sh 的清单，消除"改一处漏一处"的失败模式
SKILL_DIRS=()
for d in "$REPO_ROOT"/skills/*/; do
  [ -f "${d}SKILL.md" ] && SKILL_DIRS+=("$(basename "$d")")
done
[ "${#SKILL_DIRS[@]}" -ge 13 ] || {
  echo "❌ skills/ 下仅识别到 ${#SKILL_DIRS[@]} 个安装单元（应 ≥13：12 个 skill + core）——仓库不完整？" >&2
  exit 1
}
SRC_ROOT="$REPO_ROOT/skills"

# 归属校验：目标位置的单元确实是本框架装的才允许覆盖删除——
# ~/.agents/skills 是多 Agent 共享目录，不能无声吞掉其他框架或用户自己的同名目录。
# 判据与 uninstall.sh 对齐：软链精确指向本仓库；core 靠特有文件指纹（通用名两件 +
# 框架独创命名二选一，双重大幅降低与第三方同名目录碰撞概率）；
# 其余 skill 要求 SKILL.md 且 frontmatter 的 slug 与目录名一致（本框架特有字段）
owns_unit() {
  local d="$1" dst="$TARGET/$1"
  if [ -L "$dst" ]; then
    [ "$(readlink "$dst")" = "$SRC_ROOT/$d" ]
  elif [ "$d" = "core" ]; then
    [ -f "$dst/evidence.md" ] && [ -f "$dst/report-template.md" ] \
      && { [ -f "$dst/test-type-matrix.md" ] || [ -f "$dst/clarify-pattern.md" ]; }
  else
    [ -f "$dst/SKILL.md" ] && grep -q "^slug: ${d}$" "$dst/SKILL.md" 2>/dev/null
  fi
}

# 检测候选目录（存在才算）
detect_candidates() {
  local cands=()
  [ -d "$HOME/.agents/skills" ] && cands+=("$HOME/.agents/skills")
  [ -d "$HOME/.claude/skills" ] && cands+=("$HOME/.claude/skills")
  [ -d "$HOME/.codex/skills" ] && cands+=("$HOME/.codex/skills")
  [ -d "$HOME/.dsh/skills" ] && cands+=("$HOME/.dsh/skills")
  [ -d "$REPO_ROOT/.claude/skills" ] && cands+=("$REPO_ROOT/.claude/skills")
  # 空数组直接展开在 bash 4.4+ 会输出空行、bash 3.2 + set -u 会报 unbound——先判长度
  if [ "${#cands[@]}" -gt 0 ]; then
    printf '%s\n' "${cands[@]}"
  fi
}

usage() {
  sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-1}"
}

TARGET="" LINK=false MODE="interactive"
while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:?--target 需要一个目录参数}"; shift 2 ;;
    --auto) MODE="auto"; shift ;;
    --link) LINK=true; shift ;;
    -h|--help) usage 0 ;;
    *) echo "未知参数: $1" >&2; usage ;;
  esac
done

# 解析目标目录
if [ -n "$TARGET" ]; then
  :
elif [ "$MODE" = "auto" ]; then
  TARGET="$(detect_candidates | head -1 || true)"
  if [ -z "$TARGET" ]; then
    echo "❌ 未检测到任何已存在的宿主 skills 目录。" >&2
    echo "   先创建一个（推荐跨宿主共享）：mkdir -p ~/.agents/skills" >&2
    echo "   或显式指定：./install.sh --target <目录>" >&2
    exit 1
  fi
else
  cands=()
  while IFS= read -r line; do cands+=("$line"); done < <(detect_candidates)
  if [ "${#cands[@]}" -eq 0 ]; then
    echo "未检测到任何宿主 skills 目录。"
    read -r -p "创建并安装到 ~/.agents/skills（跨宿主共享，推荐）? [Y/n] " ans || ans=""
    [ "${ans:-Y}" = "Y" ] || [ "${ans:-Y}" = "y" ] || exit 0
    mkdir -p "$HOME/.agents/skills"
    TARGET="$HOME/.agents/skills"
  elif [ "${#cands[@]}" -eq 1 ]; then
    TARGET="${cands[0]}"
    echo "检测到唯一宿主目录：$TARGET"
  else
    echo "检测到多个宿主目录，选择一个："
    i=1
    for c in "${cands[@]}"; do echo "  $i) $c"; i=$((i + 1)); done
    read -r -p "序号 [1]: " idx || idx=""
    idx="${idx:-1}"
    case "$idx" in ''|*[!0-9]*) echo "无效序号: $idx" >&2; exit 1 ;; esac
    if [ "$idx" -lt 1 ] || [ "$idx" -gt "${#cands[@]}" ]; then
      echo "序号超出范围: ${idx}（可选 1-${#cands[@]}）" >&2; exit 1
    fi
    TARGET="${cands[$((idx - 1))]}"
  fi
fi

# 防自毁：目标等于或位于本仓库 skills/ 源目录内时拒绝（src==dst 会先删源文件，随后复制失败）。
# pwd -P 解析物理路径：--target 若是链进仓库的 symlink，逻辑路径守卫会被绕过（2026-09-07 审查修复）。
# 守卫先于 mkdir（2026-10-10 审查修复：原顺序会在拒绝前先在源树内留下空目录）——目标尚不存在时
# 先按字符串前缀判定，mkdir 后再物理复核（覆盖 symlink 父目录的窄窗），复核拒绝时清掉刚建的空目录。
guard_target() {
  case "$1" in
    "$SRC_ROOT"|"$SRC_ROOT"/*) return 1 ;;
  esac
  return 0
}
deny_selfdestruct() {
  echo "❌ 拒绝安装：目标目录位于本仓库的 skills/ 源目录内，会破坏源文件。请换一个安装目标。" >&2
  exit 1
}
TARGET_ABS="$(cd "$TARGET" 2>/dev/null && pwd -P || true)"
guard_target "${TARGET_ABS:-$TARGET}" || deny_selfdestruct
mkdir -p "$TARGET"
TARGET_ABS="$(cd "$TARGET" && pwd -P)" || { echo "❌ 无法访问目标目录：$TARGET" >&2; exit 1; }
guard_target "$TARGET_ABS" || {
  # 只删空目录（rmdir 非空即失败），沿拼写路径向上清理本守卫刚创建的层级，
  # 删到非空 / 出源树 / 到根即停——多级新建路径同样零残留
  d="$TARGET"
  while [ -n "$d" ] && [ "$d" != "/" ] && [ "$d" != "." ] && [ "$d" != "$SRC_ROOT" ]; do
    rmdir "$d" 2>/dev/null || break
    d="$(dirname -- "$d")"
  done
  deny_selfdestruct
}
# A directory lock also serializes uninstall.sh. Never steal a stale lock automatically.
LOCK_DIR="$TARGET/.qa-skills.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "❌ Another install/uninstall is running, or an interrupted operation needs recovery: $LOCK_DIR" >&2
  exit 1
fi
TXN="" COMMITTED=false
TOUCHED=()
cleanup() {
  local rc=$? d i recovery_failed=false
  trap - EXIT HUP INT TERM
  if ! $COMMITTED && [ -n "$TXN" ]; then
    # Reverse only operations actually started. Existing entries are moved, never deleted first.
    i=${#TOUCHED[@]}
    while [ "$i" -gt 0 ]; do
      i=$((i - 1)); d="${TOUCHED[$i]}"
      if [ -e "$TXN/old/$d" ] || [ -L "$TXN/old/$d" ]; then
        rm -rf "$TARGET/$d" && mv "$TXN/old/$d" "$TARGET/$d" || recovery_failed=true
      elif [ ! -e "$TXN/new/$d" ] && [ ! -L "$TXN/new/$d" ]; then
        rm -rf "$TARGET/$d" || recovery_failed=true
      fi
    done
  fi
  if $recovery_failed; then
    echo "❌ Recovery failed. Keep the backup and lock; restore manually: $TXN/old" >&2
    exit 1
  fi
  [ -z "$TXN" ] || rm -rf "$TXN"
  rm -f "$LOCK_DIR/pid"
  rmdir "$LOCK_DIR"
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
printf '%s\n' "$$" > "$LOCK_DIR/pid"

# Preflight every unit before changing any installed content.
for d in "${SKILL_DIRS[@]}"; do
  [ -d "$SRC_ROOT/$d" ] && [ -f "$SRC_ROOT/$d/SKILL.md" ] || {
    echo "❌ Incomplete source unit: $d" >&2; exit 1;
  }
  if { [ -e "$TARGET/$d" ] || [ -L "$TARGET/$d" ]; } && ! owns_unit "$d"; then
    echo "❌ 目标已存在同名 ${d}/，但不是本框架安装的目录，拒绝覆盖。" >&2
    exit 1
  fi
done
if [ -e "$TARGET/qa-skills.VERSION" ] || [ -L "$TARGET/qa-skills.VERSION" ]; then
  [ -f "$TARGET/qa-skills.VERSION" ] && [ ! -L "$TARGET/qa-skills.VERSION" ] || {
    echo "❌ Version marker must be a regular file: $TARGET/qa-skills.VERSION" >&2; exit 1;
  }
fi

TXN="$(mktemp -d "$TARGET/.qa-skills.txn.XXXXXX")"
mkdir "$TXN/new" "$TXN/old"
METHOD="copy"; $LINK && METHOD="link"
echo "安装目标：${TARGET}（方式：${METHOD}）"
for d in "${SKILL_DIRS[@]}"; do
  if $LINK; then
    ln -s "$SRC_ROOT/$d" "$TXN/new/$d"
  else
    cp -R "$SRC_ROOT/$d" "$TXN/new/$d"
    find "$TXN/new/$d" -type d -name '__pycache__' -prune -exec rm -rf {} +
    find "$TXN/new/$d" -type f -name '*.pyc' -delete
  fi
done

# Include provenance in the same rollback boundary as the content.
VERSION="$(git -C "$REPO_ROOT" describe --tags --always --dirty 2>/dev/null || echo unknown)"
COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
{
  printf '%s (installed: %s)\n' "$VERSION" "$(date +%Y-%m-%d)"
  printf 'commit: %s\nmethod: %s\nsource: %s\n' "$COMMIT" "$METHOD" "$REPO_ROOT"
} > "$TXN/new/qa-skills.VERSION"

for d in "${SKILL_DIRS[@]}" qa-skills.VERSION; do
  TOUCHED+=("$d")
  if [ -e "$TARGET/$d" ] || [ -L "$TARGET/$d" ]; then
    mv "$TARGET/$d" "$TXN/old/$d"
  fi
  mv "$TXN/new/$d" "$TARGET/$d"
  echo "  Installed $d"
done
COMMITTED=true

echo ""
echo "✅ 完成。版本：$VERSION"
echo "   Commit: $COMMIT; method: $METHOD"
echo "   Verify: python3 scripts/verify_install.py \"$TARGET\""
echo "   已有本框架目录会整体替换；本地自定义请在仓库分支维护。"
