#!/usr/bin/env bash
set -euo pipefail

# webnovel-writer WorkBuddy 更新脚本
# 用法:
#   bash update.sh              # 从本地仓库更新（你已经 git pull 过）
#   bash update.sh --sync       # 先从你的 fork 拉取最新，再更新 skill
#   bash update.sh --upstream   # 先从原仓库同步到 fork，再更新 skill
#
# 安全策略:
#   - 不删除任何目录，只用 cp -R 覆盖同名文件
#   - WorkBuddy 适配文件（SKILL.md、convert_to_workbuddy.py、install.sh、update.sh、hooks/README.md）
#     放在不会被源文件覆盖的位置，更新后自动保留
#   - 更新前自动备份整个 skill 目录

# ============ 配置 ============
REPO_DIR="/Users/supersam/Workbuddy/webnovel-writer进行workbuddy兼容/webnovel-writer"
SRC_DIR="${REPO_DIR}/webnovel-writer"
SKILL_DIR="$HOME/.workbuddy/skills/webnovel-writer"
VENV_PYTHON="/Users/supersam/.workbuddy/binaries/python/envs/default/bin/python3"
ORIGINAL_REPO="lingfengQAQ/webnovel-writer"

# ============ 颜色输出 ============
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }

echo "=== Webnovel Writer WorkBuddy 更新 ==="
echo ""

# ============ Step 0: 可选 - 从远程拉取 ============
if [ "${1:-}" = "--sync" ] || [ "${1:-}" = "--upstream" ]; then
    cd "$REPO_DIR"

    if [ "${1:-}" = "--upstream" ]; then
        # 添加 upstream remote（如果不存在）
        if ! git remote get-url upstream >/dev/null 2>&1; then
            info "添加 upstream remote: $ORIGINAL_REPO"
            git remote add upstream "https://github.com/${ORIGINAL_REPO}.git"
        fi

        echo ""
        echo "--- 从原仓库拉取最新代码 ---"
        git fetch upstream
        git merge upstream/master --no-edit || {
            warn "合并有冲突，请手动解决后重新运行: bash update.sh"
            exit 1
        }
    else
        echo "--- 从你的 fork 拉取最新代码 ---"
        git fetch origin
        git pull origin master
    fi
    info "远程代码已更新"
    echo ""
fi

# ============ Step 1: 检查环境 ============
echo "[1/5] 检查环境"
if [ ! -d "$REPO_DIR" ]; then
    error "本地仓库不存在: $REPO_DIR"
    exit 1
fi

if [ ! -d "$SRC_DIR" ]; then
    error "源目录不存在: $SRC_DIR"
    exit 1
fi

if [ ! -f "$VENV_PYTHON" ]; then
    error "Python venv 不存在: $VENV_PYTHON"
    echo "  请先运行: bash install.sh"
    exit 1
fi

# 获取当前版本
CURRENT_VERSION=""
if [ -f "$SKILL_DIR/scripts/data_modules/config.py" ]; then
    CURRENT_VERSION=$(grep -o 'VERSION.*=.*"[^"]*"' "$SKILL_DIR/scripts/data_modules/config.py" 2>/dev/null | head -1 | sed 's/.*"\(.*\)"/\1/' || echo "")
fi

info "当前安装版本: ${CURRENT_VERSION:-未知}"
info "本地仓库: $REPO_DIR"
echo ""

# ============ Step 2: 备份当前 skill ============
echo "[2/5] 备份当前 skill"
BACKUP_DIR="$HOME/.workbuddy/skills/.webnovel-writer-backup-$(date +%Y%m%d-%H%M%S)"
if [ -d "$SKILL_DIR" ]; then
    mkdir -p "$(dirname "$BACKUP_DIR")"
    cp -R "$SKILL_DIR" "$BACKUP_DIR"
    info "已备份到: $BACKUP_DIR"
else
    warn "skill 目录不存在，跳过备份"
fi
echo ""

# ============ Step 3: 覆盖更新源文件 ============
echo "[3/5] 更新源文件"

# 临时保存 WorkBuddy 适配文件（这些文件不在原始项目的对应位置，不会被覆盖，
# 但为保险起见，先存到临时位置）
TMP_WB_FILES=$(mktemp -d)
for f in SKILL.md convert_to_workbuddy.py install.sh update.sh; do
    [ -f "$SKILL_DIR/$f" ] && cp "$SKILL_DIR/$f" "$TMP_WB_FILES/"
done
[ -f "$SKILL_DIR/hooks/README.md" ] && cp "$SKILL_DIR/hooks/README.md" "$TMP_WB_FILES/hooks_README.md"

# 覆盖复制原始项目的核心目录（cp -R 会覆盖同名文件，新增文件自动加入，不删除已有文件）
for dir in scripts references templates dashboard agents hooks; do
    if [ -d "$SRC_DIR/$dir" ]; then
        mkdir -p "$SKILL_DIR/$dir"
        cp -R "$SRC_DIR/$dir/"* "$SKILL_DIR/$dir/"
        info "已更新 $dir/"
    fi
done

# 恢复 WorkBuddy 适配文件
for f in SKILL.md convert_to_workbuddy.py install.sh update.sh; do
    if [ -f "$TMP_WB_FILES/$f" ]; then
        cp "$TMP_WB_FILES/$f" "$SKILL_DIR/$f"
    fi
done
[ -f "$TMP_WB_FILES/hooks_README.md" ] && cp "$TMP_WB_FILES/hooks_README.md" "$SKILL_DIR/hooks/README.md"
rm -rf "$TMP_WB_FILES"

# 覆盖复制每个 skill 的 references 和 evals
for skill in webnovel-init webnovel-plan webnovel-write webnovel-review webnovel-query webnovel-learn webnovel-dashboard webnovel-doctor; do
    if [ -d "$SRC_DIR/skills/$skill/references" ]; then
        mkdir -p "$SKILL_DIR/commands/$skill"
        cp -R "$SRC_DIR/skills/$skill/references/"* "$SKILL_DIR/commands/$skill/references/" 2>/dev/null || true
    fi
    if [ -d "$SRC_DIR/skills/$skill/evals" ]; then
        mkdir -p "$SKILL_DIR/commands/$skill"
        cp -R "$SRC_DIR/skills/$skill/evals/"* "$SKILL_DIR/commands/$skill/evals/" 2>/dev/null || true
    fi
done

# 确保符号链接存在
if [ ! -L "$SKILL_DIR/skills" ]; then
    ln -sf commands "$SKILL_DIR/skills"
    info "已重建 skills -> commands 符号链接"
fi

echo ""

# ============ Step 4: 重新转换为 WorkBuddy 格式 ============
echo "[4/5] 重新转换为 WorkBuddy 格式"

if [ -f "$SKILL_DIR/convert_to_workbuddy.py" ]; then
    "$VENV_PYTHON" "$SKILL_DIR/convert_to_workbuddy.py"

    # 修复转换后文件中的残留引用
    find "$SKILL_DIR/commands" -name "*.md" -exec sed -i '' \
        's|${CLAUDE_PLUGIN_ROOT}/skills/webnovel-query/references/|${PLUGIN_ROOT}/commands/webnovel-query/references/|g' {} + 2>/dev/null || true
    find "$SKILL_DIR/commands" -name "*.md" -exec sed -i '' \
        's|${CLAUDE_PLUGIN_ROOT}|${PLUGIN_ROOT}|g' {} + 2>/dev/null || true

    # 重新整理目录结构：转换脚本生成 commands/*.md，需要移到 commands/*/SKILL.md
    for cmd in webnovel-init webnovel-plan webnovel-write webnovel-review webnovel-query webnovel-learn webnovel-dashboard webnovel-doctor; do
        if [ -f "$SKILL_DIR/commands/$cmd.md" ] && [ ! -f "$SKILL_DIR/commands/$cmd/SKILL.md" ]; then
            mkdir -p "$SKILL_DIR/commands/$cmd"
            mv "$SKILL_DIR/commands/$cmd.md" "$SKILL_DIR/commands/$cmd/SKILL.md"
        fi
    done

    info "转换完成"
else
    warn "转换脚本不存在，跳过（仅更新了源文件）"
fi

# 更新 agents（替换 python -X utf8，清理 frontmatter）
for agent_file in "$SKILL_DIR"/agents/*.md; do
    if [ -f "$agent_file" ]; then
        sed -i '' 's/python -X utf8 /${PYTHON} /g' "$agent_file"
        sed -i '' '/^tools:/d; /^model:/d; /^color:/d' "$agent_file"
    fi
done

# 更新 hooks（确保 session_start.py 使用 PLUGIN_ROOT 环境变量）
if [ -f "$SKILL_DIR/hooks/session_start.py" ]; then
    if ! grep -q 'PLUGIN_ROOT' "$SKILL_DIR/hooks/session_start.py" 2>/dev/null; then
        sed -i '' 's/CLAUDE_PLUGIN_ROOT/PLUGIN_ROOT/g' "$SKILL_DIR/hooks/session_start.py"
        sed -i '' 's/CLAUDE_PROJECT_DIR/WORKSPACE_ROOT/g' "$SKILL_DIR/hooks/session_start.py"
    fi
fi

echo ""

# ============ Step 5: 检查依赖并验证 ============
echo "[5/5] 检查依赖并验证"

# 检查 requirements.txt 是否有变化
REINSTALL_DEPS=false
if [ -f "$SRC_DIR/scripts/requirements.txt" ]; then
    if ! diff -q "$SRC_DIR/scripts/requirements.txt" "$SKILL_DIR/scripts/requirements.txt" >/dev/null 2>&1; then
        REINSTALL_DEPS=true
        warn "requirements.txt 有变化，需要重新安装依赖"
    fi
fi

if [ "$REINSTALL_DEPS" = true ]; then
    echo "  重新安装 Python 依赖..."
    "$VENV_PYTHON" -m pip install --quiet \
        aiohttp filelock pydantic fastapi httpx "uvicorn[standard]" watchdog 2>&1 | tail -3
    info "依赖已更新"
else
    info "依赖无变化，跳过"
fi

# 验证
echo ""
echo "--- 验证 ---"
export PLUGIN_ROOT="$SKILL_DIR"
export SCRIPTS_DIR="${PLUGIN_ROOT}/scripts"
export PYTHON="$VENV_PYTHON"
export PYTHONPATH="${SCRIPTS_DIR}"

if "$PYTHON" "$SCRIPTS_DIR/webnovel.py" --help >/dev/null 2>&1; then
    info "webnovel.py 运行正常"
else
    error "webnovel.py 运行失败！"
    echo "  可从备份恢复: cp -R $BACKUP_DIR/* $SKILL_DIR/"
    exit 1
fi

COMMAND_COUNT=$(find "$SKILL_DIR/commands" -name "SKILL.md" | wc -l | tr -d ' ')
AGENT_COUNT=$(ls -1 "$SKILL_DIR/agents/"*.md 2>/dev/null | wc -l | tr -d ' ')

info "命令文件: $COMMAND_COUNT 个"
info "Agent 文件: $AGENT_COUNT 个"

# 获取新版本
NEW_VERSION=""
if [ -f "$SKILL_DIR/scripts/data_modules/config.py" ]; then
    NEW_VERSION=$(grep -o 'VERSION.*=.*"[^"]*"' "$SKILL_DIR/scripts/data_modules/config.py" 2>/dev/null | head -1 | sed 's/.*"\(.*\)"/\1/' || echo "")
fi

echo ""
echo "=== 更新完成 ==="
echo ""
echo "版本变化: ${CURRENT_VERSION:-未知} → ${NEW_VERSION:-未知}"
echo ""
echo "备份位置: $BACKUP_DIR"
echo ""
if [ "$CURRENT_VERSION" != "$NEW_VERSION" ] && [ -n "$CURRENT_VERSION" ] && [ -n "$NEW_VERSION" ]; then
    warn "版本已变更，建议查看更新日志:"
    echo "  https://github.com/lingfengQAQ/webnovel-writer/blob/master/CHANGELOG.md"
fi
