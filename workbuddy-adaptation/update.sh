#!/usr/bin/env bash
set -euo pipefail

# webnovel-writer WorkBuddy 更新脚本
# 用法:
#   bash update.sh              # 从本地仓库更新（你已经 git pull 过）
#   bash update.sh --sync       # 先从你的 fork 拉取最新，再更新 skill
#   bash update.sh --upstream   # 先从原仓库同步到 fork，再更新 skill
#
# 安全策略:
#   - 不删除整个 skill 目录，用 cp -R 覆盖同名文件
#   - 对带 content hash 的构建产物目录（dist）先清空再复制
#   - WorkBuddy 适配文件放在不会被覆盖的位置，更新后自动保留
#   - 更新前自动备份，只保留最近 3 个备份
#   - 清理 __pycache__ 防止旧 .pyc 干扰

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
echo "[1/6] 检查环境"
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
echo "[2/6] 备份当前 skill"
BACKUP_DIR="$HOME/.workbuddy/skills/.webnovel-writer-backup-$(date +%Y%m%d-%H%M%S)"
if [ -d "$SKILL_DIR" ]; then
    mkdir -p "$(dirname "$BACKUP_DIR")"
    cp -R "$SKILL_DIR" "$BACKUP_DIR"
    info "已备份到: $BACKUP_DIR"

    # 清理旧备份，只保留最近 3 个
    BACKUP_COUNT=$(ls -1d "$HOME/.workbuddy/skills/.webnovel-writer-backup-"* 2>/dev/null | wc -l | tr -d ' ')
    if [ "$BACKUP_COUNT" -gt 3 ]; then
        REMOVE_COUNT=$((BACKUP_COUNT - 3))
        info "发现 $BACKUP_COUNT 个备份，清理最旧的 $REMOVE_COUNT 个"
        ls -1dt "$HOME/.workbuddy/skills/.webnovel-writer-backup-"* | tail -n "$REMOVE_COUNT" | while read old_backup; do
            rm -rf "$old_backup"
        done
    fi
else
    warn "skill 目录不存在，跳过备份"
fi
echo ""

# ============ Step 3: 覆盖更新源文件 ============
echo "[3/6] 更新源文件"

# 临时保存 WorkBuddy 适配文件
TMP_WB_FILES=$(mktemp -d)
for f in SKILL.md convert_to_workbuddy.py install.sh update.sh; do
    [ -f "$SKILL_DIR/$f" ] && cp "$SKILL_DIR/$f" "$TMP_WB_FILES/"
done
[ -f "$SKILL_DIR/hooks/README.md" ] && cp "$SKILL_DIR/hooks/README.md" "$TMP_WB_FILES/hooks_README.md"

# 覆盖复制原始项目的核心目录
for dir in scripts references templates dashboard agents hooks; do
    if [ -d "$SRC_DIR/$dir" ]; then
        mkdir -p "$SKILL_DIR/$dir"

        # dashboard/frontend/dist: Vite 构建产物，文件名带 content hash，必须先清空
        if [ "$dir" = "dashboard" ] && [ -d "$SKILL_DIR/dashboard/frontend/dist" ]; then
            rm -f "$SKILL_DIR/dashboard/frontend/dist/index.html"
            rm -rf "$SKILL_DIR/dashboard/frontend/dist/assets"
            info "  已清理旧的 dashboard/frontend/dist 构建产物"
        fi

        # agents: 只复制 .md 文件，不复制 evals 子目录（Claude Code 专用，WorkBuddy 不需要）
        if [ "$dir" = "agents" ]; then
            # 清理可能存在的 evals 子目录（旧版 update.sh 可能复制了进来）
            if [ -d "$SKILL_DIR/agents/evals" ]; then
                rm -rf "$SKILL_DIR/agents/evals"
                info "  已清理旧的 agents/evals 目录"
            fi
            cp "$SRC_DIR/agents/"*.md "$SKILL_DIR/agents/"
        else
            cp -R "$SRC_DIR/$dir/"* "$SKILL_DIR/$dir/"
        fi

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

# 覆盖复制每个 skill 的 references 和 evals（不复制 agents 子目录，那是 Claude Code 专用）
for skill in webnovel-init webnovel-plan webnovel-write webnovel-review webnovel-query webnovel-learn webnovel-dashboard webnovel-doctor; do
    if [ -d "$SRC_DIR/skills/$skill/references" ]; then
        mkdir -p "$SKILL_DIR/commands/$skill/references"
        cp -R "$SRC_DIR/skills/$skill/references/"* "$SKILL_DIR/commands/$skill/references/" 2>/dev/null || true
    fi
    if [ -d "$SRC_DIR/skills/$skill/evals" ]; then
        mkdir -p "$SKILL_DIR/commands/$skill/evals"
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
echo "[4/6] 重新转换为 WorkBuddy 格式"

if [ -f "$SKILL_DIR/convert_to_workbuddy.py" ]; then
    # 先清理转换脚本上次生成的顶层 .md 文件（防止残留）
    for cmd in webnovel-init webnovel-plan webnovel-write webnovel-review webnovel-query webnovel-learn webnovel-dashboard webnovel-doctor; do
        if [ -f "$SKILL_DIR/commands/$cmd.md" ]; then
            rm -f "$SKILL_DIR/commands/$cmd.md"
        fi
    done

    "$VENV_PYTHON" "$SKILL_DIR/convert_to_workbuddy.py"

    # 修复转换后文件中的残留引用
    find "$SKILL_DIR/commands" -name "*.md" -exec sed -i '' \
        's|${CLAUDE_PLUGIN_ROOT}/skills/webnovel-query/references/|${PLUGIN_ROOT}/commands/webnovel-query/references/|g' {} + 2>/dev/null || true
    find "$SKILL_DIR/commands" -name "*.md" -exec sed -i '' \
        's|${CLAUDE_PLUGIN_ROOT}|${PLUGIN_ROOT}|g' {} + 2>/dev/null || true

    # 把转换生成的 commands/*.md 移到 commands/*/SKILL.md
    for cmd in webnovel-init webnovel-plan webnovel-write webnovel-review webnovel-query webnovel-learn webnovel-dashboard webnovel-doctor; do
        if [ -f "$SKILL_DIR/commands/$cmd.md" ]; then
            mkdir -p "$SKILL_DIR/commands/$cmd"
            # 覆盖旧的 SKILL.md
            mv -f "$SKILL_DIR/commands/$cmd.md" "$SKILL_DIR/commands/$cmd/SKILL.md"
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

# ============ Step 5: 清理 Python 缓存 + 杀旧 dashboard 进程 ============
echo "[5/6] 清理 Python 缓存 + 停止旧 dashboard 进程"

# 清理 __pycache__
find "$SKILL_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$SKILL_DIR" -name "*.pyc" -delete 2>/dev/null || true
info "已清理 __pycache__ 和 .pyc 文件"

# 停止旧 dashboard 进程（Python 进程加载的是旧代码，磁盘更新后不会自动重载）
DASHBOARD_PID=$(lsof -ti :8765 -sTCP:LISTEN 2>/dev/null || true)
if [ -n "$DASHBOARD_PID" ]; then
    kill "$DASHBOARD_PID" 2>/dev/null || true
    sleep 1
    info "已停止旧 dashboard 进程 (PID: $DASHBOARD_PID，端口 8765)"
    warn "请重新启动 dashboard 以加载最新代码"
else
    info "无运行中的 dashboard 进程"
fi
echo ""

# ============ Step 6: 检查依赖并验证 ============
echo "[6/6] 检查依赖并验证"

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

# 验证关键文件完整性
VERIFY_PASS=true

# 验证适配文件
for f in SKILL.md convert_to_workbuddy.py install.sh update.sh hooks/README.md; do
    if [ ! -f "$SKILL_DIR/$f" ]; then
        error "适配文件缺失: $f"
        VERIFY_PASS=false
    fi
done

# 验证命令文件
COMMAND_COUNT=$(find "$SKILL_DIR/commands" -name "SKILL.md" | wc -l | tr -d ' ')
if [ "$COMMAND_COUNT" -ne 8 ]; then
    error "命令文件数量异常: $COMMAND_COUNT (应为 8)"
    VERIFY_PASS=false
fi

# 验证 Agent 文件
AGENT_COUNT=$(ls -1 "$SKILL_DIR/agents/"*.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$AGENT_COUNT" -ne 4 ]; then
    error "Agent 文件数量异常: $AGENT_COUNT (应为 4)"
    VERIFY_PASS=false
fi

# 验证 dashboard 前端
if [ ! -f "$SKILL_DIR/dashboard/frontend/dist/index.html" ]; then
    error "dashboard 前端构建产物缺失"
    VERIFY_PASS=false
fi

# 验证无残留的顶层 .md 文件
STALE_MD=$(find "$SKILL_DIR/commands" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
if [ "$STALE_MD" -ne 0 ]; then
    warn "发现 $STALE_MD 个残留的顶层命令文件，清理中..."
    find "$SKILL_DIR/commands" -maxdepth 1 -name "*.md" -delete
fi

if [ "$VERIFY_PASS" = true ]; then
    info "命令文件: $COMMAND_COUNT 个 ✓"
    info "Agent 文件: $AGENT_COUNT 个 ✓"
    info "dashboard 前端: 正常 ✓"
    info "适配文件: 完整 ✓"
else
    error "验证发现问题，请检查上方日志"
    echo "  可从备份恢复: cp -R $BACKUP_DIR/* $SKILL_DIR/"
    exit 1
fi

# 最终清理：验证步骤运行 webnovel.py 会生成 __pycache__，最后清一次
find "$SKILL_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$SKILL_DIR" -name "*.pyc" -delete 2>/dev/null || true

# 获取新版本
NEW_VERSION=""
if [ -f "$SKILL_DIR/scripts/data_modules/config.py" ]; then
    NEW_VERSION=$(grep -o 'VERSION.*=.*"[^"]*"' "$SKILL_DIR/scripts/data_modules/config.py" 2>/dev/null | head -1 | sed 's/.*"\(.*\)"/\1/' || echo "")
fi

echo ""
echo "=== 更新完成 ==="
echo ""
echo "版本变化: ${CURRENT_VERSION:-未知} → ${NEW_VERSION:-未知}"
echo "备份位置: $BACKUP_DIR"
echo ""
if [ "$CURRENT_VERSION" != "$NEW_VERSION" ] && [ -n "$CURRENT_VERSION" ] && [ -n "$NEW_VERSION" ]; then
    warn "版本已变更，建议查看更新日志:"
    echo "  https://github.com/lingfengQAQ/webnovel-writer/blob/master/CHANGELOG.md"
fi
