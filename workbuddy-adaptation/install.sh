#!/usr/bin/env bash
set -euo pipefail

# webnovel-writer WorkBuddy 安装脚本
# 用法: bash install.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="webnovel-writer"
SKILL_DIR="$HOME/.workbuddy/skills/$SKILL_NAME"

echo "=== Webnovel Writer WorkBuddy 安装 ==="
echo ""

# 1. 检查 Python 环境
PYTHON_BIN="/Users/supersam/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
VENV_DIR="/Users/supersam/.workbuddy/binaries/python/envs/default"

if [ ! -f "$PYTHON_BIN" ]; then
    echo "ERROR: 未找到 managed Python 3.13.12"
    echo "  预期路径: $PYTHON_BIN"
    echo "  请确认 WorkBuddy 已安装 managed Python"
    exit 1
fi

echo "[1/4] Python 环境"
echo "  Python: $PYTHON_BIN"

# 2. 创建/更新 venv
if [ ! -d "$VENV_DIR" ]; then
    echo "  创建 venv..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

VENV_PYTHON="$VENV_DIR/bin/python3"
echo "  venv: $VENV_DIR"

# 3. 安装依赖
echo ""
echo "[2/4] 安装 Python 依赖..."
"$VENV_PYTHON" -m pip install --quiet --upgrade pip 2>/dev/null || true
"$VENV_PYTHON" -m pip install --quiet \
    aiohttp>=3.8.0 \
    filelock>=3.0.0 \
    "pydantic>=2.0.0" \
    "fastapi>=0.115.0" \
    "httpx>=0.27.0" \
    "uvicorn[standard]>=0.32.0" \
    "watchdog>=5.0.0" 2>&1 | tail -3
echo "  依赖安装完成"

# 4. 安装 skill
echo ""
echo "[3/4] 安装 skill 到 $SKILL_DIR"
if [ "$SCRIPT_DIR" != "$SKILL_DIR" ]; then
    mkdir -p "$SKILL_DIR"
    # 如果源目录和目标不同，复制文件
    if [ -f "$SCRIPT_DIR/SKILL.md" ]; then
        cp -R "$SCRIPT_DIR/"* "$SKILL_DIR/" 2>/dev/null || true
        echo "  已复制 skill 文件到 $SKILL_DIR"
    fi
else
    echo "  已在目标目录，跳过复制"
fi

# 5. 验证
echo ""
echo "[4/4] 验证安装..."
export PLUGIN_ROOT="$SKILL_DIR"
export SCRIPTS_DIR="${PLUGIN_ROOT}/scripts"
export PYTHON="$VENV_PYTHON"
export PYTHONPATH="${SCRIPTS_DIR}:${PYTHONPATH:-}"

if "$PYTHON" "$SCRIPTS_DIR/webnovel.py" --help >/dev/null 2>&1; then
    echo "  ✓ webnovel.py 可正常运行"
else
    echo "  ✗ webnovel.py 运行失败"
    exit 1
fi

if [ -f "$SKILL_DIR/SKILL.md" ]; then
    echo "  ✓ SKILL.md 存在"
else
    echo "  ✗ SKILL.md 缺失"
    exit 1
fi

COMMAND_COUNT=$(ls -1 "$SKILL_DIR/commands/"*.md 2>/dev/null | wc -l | tr -d ' ')
echo "  ✓ 命令文件: $COMMAND_COUNT 个"

AGENT_COUNT=$(ls -1 "$SKILL_DIR/agents/"*.md 2>/dev/null | wc -l | tr -d ' ')
echo "  ✓ Agent 文件: $AGENT_COUNT 个"

echo ""
echo "=== 安装完成 ==="
echo ""
echo "使用方法:"
echo "  在 WorkBuddy 对话中输入创作相关请求即可触发 skill，例如:"
echo "  - '帮我初始化一本网文'  → webnovel-init"
echo "  - '规划第一卷'          → webnovel-plan"
echo "  - '写第一章'            → webnovel-write"
echo "  - '审查第1-5章'         → webnovel-review"
echo "  - '查询伏笔状态'        → webnovel-query"
echo ""
echo "  或直接说: 初始化网文项目 / 规划卷纲 / 写章 / 审查 / 查询 / 打开面板 / 体检"
