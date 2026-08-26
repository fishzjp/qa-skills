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

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 框架的全部安装单元：10 个 skill + core/（共享知识库，各 skill 相对引用，必须一起装）
# 源路径统一在 skills/ 下
SKILL_DIRS=(
  qa core
  requirement-analysis test-strategy test-case-writing test-case-review
  automated-e2e-testing api-testing exploratory-testing bug-analysis regression-testing
)
SRC_ROOT="$REPO_ROOT/skills"

# 归属校验：目标位置的单元确实是本框架装的才允许覆盖删除——
# ~/.agents/skills 是多 Agent 共享目录，不能无声吞掉其他框架或用户自己的同名目录。
# 判据与 uninstall.sh 对齐：软链精确指向本仓库；core 靠特有文件指纹；
# 其余 skill 要求 SKILL.md 且 frontmatter 的 slug 与目录名一致（本框架特有字段）
owns_unit() {
  local d="$1" dst="$TARGET/$1"
  if [ -L "$dst" ]; then
    [ "$(readlink "$dst")" = "$SRC_ROOT/$d" ]
  elif [ "$d" = "core" ]; then
    [ -f "$dst/evidence.md" ] && [ -f "$dst/report-template.md" ]
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
  exit 1
}

TARGET="" LINK=false MODE="interactive"
while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:?--target 需要一个目录参数}"; shift 2 ;;
    --auto) MODE="auto"; shift ;;
    --link) LINK=true; shift ;;
    -h|--help) usage ;;
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

mkdir -p "$TARGET"
# 防自毁：目标等于或位于本仓库 skills/ 源目录内时拒绝（src==dst 会先删源文件，随后复制失败）
TARGET_ABS="$(cd "$TARGET" && pwd)"
case "$TARGET_ABS" in
  "$SRC_ROOT"|"$SRC_ROOT"/*)
    echo "❌ 拒绝安装：目标目录位于本仓库的 skills/ 源目录内，会破坏源文件。请换一个安装目标。" >&2
    exit 1 ;;
esac
METHOD="拷贝"; $LINK && METHOD="软链"
echo "安装目标：${TARGET}（方式：${METHOD}）"
echo ""

for d in "${SKILL_DIRS[@]}"; do
  src="$SRC_ROOT/$d" dst="$TARGET/$d"
  [ -d "$src" ] || { echo "❌ 仓库缺少 ${d}（仓库不完整？）" >&2; exit 1; }
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    if owns_unit "$d"; then
      rm -rf "$dst"   # 重装 = 覆盖旧版本（仅覆盖确认属于本框架的目录）
      echo "  更新 $d"
    else
      echo "❌ 目标已存在同名 ${d}/，但不是本框架安装的目录，拒绝覆盖。" >&2
      echo "   （防误删：共享目录里可能有其他框架或你自己的同名内容）" >&2
      echo "   确认无用了可手动处理后再装：rm -rf \"$dst\"" >&2
      exit 1
    fi
  else
    echo "  安装 $d"
  fi
  if $LINK; then
    ln -s "$src" "$dst"
  else
    cp -R "$src" "$dst"
  fi
done

# 版本标识：装完能回答"我用的是哪一版"
VERSION="$(cd "$REPO_ROOT" && git describe --tags --always 2>/dev/null || echo unknown)"
if $LINK; then
  echo "$VERSION (repo: $REPO_ROOT)" > "$TARGET/qa-skills.VERSION"
else
  echo "$VERSION (installed: $(date +%Y-%m-%d))" > "$TARGET/qa-skills.VERSION"
fi

echo ""
echo "✅ 完成。版本：$VERSION"
echo "   验证：ls $TARGET | head；升级：git pull 后重跑本脚本"
echo "   下一步：对你的 Agent 说——\"帮我测试这个需求：{需求描述 + 仓库地址}\""