# WorkBuddy Hooks 适配说明

本目录包含从 Claude Code 迁移的 hook 脚本。WorkBuddy 的 hook 机制与 Claude Code 不同，以下说明适配方式。

## Claude Code Hooks → WorkBuddy 适配

### 1. SessionStart Hook → 项目状态检查

**Claude Code 方式**：`hooks.json` 配置 `SessionStart` 事件，自动运行 `session_start.py`。

**WorkBuddy 方式**：WorkBuddy 没有 SessionStart hook。改为在主 SKILL.md 被触发时，由 agent 主动调用：

```bash
${PYTHON} "${PLUGIN_ROOT}/hooks/session_start.py"
```

或者直接运行状态检查命令：

```bash
${PYTHON} "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" project-status --format summary
```

### 2. PreToolUse Guard → 写入保护规则

**Claude Code 方式**：`hooks.json` 配置 `PreToolUse` 事件，拦截 Write/Edit/Bash 操作，阻止直接修改 Story System / read-model 文件。

**WorkBuddy 方式**：WorkBuddy 目前没有 PreToolUse hook。以下规则以指令形式嵌入 SKILL.md，agent 必须遵守。

#### 受保护文件清单（禁止直接 Write/Edit）

以下文件只能通过 `webnovel.py` 的运行时命令修改，不得用 Write/Edit 工具直接写入：

| 文件/路径 | 允许的修改方式 |
|----------|-------------|
| `.story-system/commits/*` | `webnovel.py chapter-commit` |
| `.webnovel/index.db` | `webnovel.py` 投影链自动写入 |
| `.webnovel/vectors.db` | `webnovel.py` 投影链自动写入 |
| `.webnovel/memory_scratchpad.json` | `webnovel.py` 记忆模块自动写入 |
| `.webnovel/projection_log.jsonl` | `webnovel.py` 投影链自动写入 |

> 注意：`.webnovel/state.json` **不在**保护清单中。审计经常需要批量修复 `update-state.py` 无法表达的标记，且 `state.json` 有独立的备份+重建路径。

#### Bash 命令保护规则

以下 Bash 模式会被阻止（对应 `guard_runtime_write.py` 的逻辑）：

- 直接用 `>` 重定向写入受保护文件
- 直接调用 `chapter_commit.py` 而非 `webnovel.py chapter-commit`
- 绕过 `webnovel.py` 直接操作投影文件

**允许的安全命令**（包含 `webnovel.py` 且包含以下之一）：
- `chapter-commit`
- `projections retry`
- `projections replay`
- `write-gate`

### 3. 手动运行 Guard 检查

如果需要验证某个路径是否受保护，可以手动调用：

```bash
echo '{"tool_name": "Write", "tool_input": {"file_path": ".story-system/commits/test.json"}}' | ${PYTHON} "${PLUGIN_ROOT}/hooks/guard_runtime_write.py"
```

返回 exit code 2 表示被拒绝。

## 环境变量

hook 脚本支持以下环境变量（优先级从高到低）：

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `PLUGIN_ROOT` | skill 安装目录 | `$HOME/.workbuddy/skills/webnovel-writer` |
| `WORKSPACE_ROOT` | 当前工作区 | `$PWD` |
| `PYTHON` | Python 解释器路径 | `sys.executable` |
| `WEBNOVEL_DISABLE_SESSION_STATUS_HOOK` | 禁用 session status | 未设置 |
| `WEBNOVEL_DISABLE_RUNTIME_GUARD_HOOK` | 禁用写入保护 | 未设置 |
