# WorkBuddy 适配版

本项目是 [lingfengQAQ/webnovel-writer](https://github.com/lingfengQAQ/webnovel-writer) 的 WorkBuddy 适配版本。

原始项目是基于 Claude Code 的长篇网文创作系统（v6.2.1），本适配版将其转换为 WorkBuddy skill 格式。

## 适配内容

### 原始 Claude Code 插件 → WorkBuddy Skill

| Claude Code | WorkBuddy | 说明 |
|-------------|-----------|------|
| `.claude-plugin/plugin.json` | `SKILL.md` frontmatter | 插件元数据 → skill 元数据 |
| `skills/*/SKILL.md` (8个) | `commands/*/SKILL.md` (8个) | 命令文件，已适配环境变量和工具引用 |
| `agents/*.md` (4个) | `agents/*.md` (4个) | Agent 定义文件，作为参考文档使用 |
| `hooks/hooks.json` + Python | `hooks/` + README.md | Hook 脚本保留，hook 机制改为指令式 |
| `${CLAUDE_PLUGIN_ROOT}` | `${PLUGIN_ROOT}` | 环境变量替换 |
| `${CLAUDE_PROJECT_DIR}` | `$PWD` | 工作目录替换 |
| `python -X utf8` | `${PYTHON}` (managed Python) | Python 路径替换 |
| `webnovel-writer:agent-name` | `Agent` tool + read agent file | Agent 调用方式适配 |
| `allowed-tools` frontmatter | 移除 | WorkBuddy 不需要此字段 |

### 8 个命令

| 命令 | 触发关键词 | 说明 |
|------|-----------|------|
| `webnovel-init` | 初始化、新建书、创建项目 | 深度初始化网文项目 |
| `webnovel-plan` | 规划、卷纲、拆章、时间线 | 基于总纲生成卷纲和章纲 |
| `webnovel-write` | 写章、写正文、第N章 | 一条龙写完一章 |
| `webnovel-review` | 审查、检查、质量 | 多维度质量审查 |
| `webnovel-query` | 查询、伏笔、角色状态 | 查询项目信息 |
| `webnovel-learn` | 记住、学习、经验 | 保存写作模式 |
| `webnovel-dashboard` | 面板、可视化 | 启动只读 Web 面板 |
| `webnovel-doctor` | 体检、诊断 | 项目健康检查 |

### 4 个 Agent

| Agent | 文件 | 职责 |
|-------|------|------|
| context-agent | `agents/context-agent.md` | 写前 research，输出写作任务书 |
| reviewer | `agents/reviewer.md` | 质量审查，输出结构化 JSON |
| data-agent | `agents/data-agent.md` | 从正文提取事实 |
| deconstruction-agent | `agents/deconstruction-agent.md` | 参考作品拆解 |

## 安装

### 自动安装

```bash
bash install.sh
```

安装脚本会：
1. 创建 Python venv（使用 managed Python 3.13.12）
2. 安装所有依赖（aiohttp, pydantic, fastapi, uvicorn 等）
3. 将 skill 安装到 `~/.workbuddy/skills/webnovel-writer/`
4. 验证安装

### 手动安装

1. 复制所有文件到 `~/.workbuddy/skills/webnovel-writer/`
2. 创建 Python venv 并安装依赖：
   ```bash
   /Users/supersam/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -m venv /Users/supersam/.workbuddy/binaries/python/envs/default
   /Users/supersam/.workbuddy/binaries/python/envs/default/bin/pip install aiohttp filelock pydantic fastapi httpx "uvicorn[standard]" watchdog
   ```
3. 创建兼容符号链接：`ln -sf commands ~/.workbuddy/skills/webnovel-writer/skills`

## 使用

在 WorkBuddy 对话中直接说：

- "帮我初始化一本网文" → 触发 webnovel-init
- "规划第一卷" → 触发 webnovel-plan
- "写第一章" → 触发 webnovel-write
- "审查第1-5章" → 触发 webnovel-review
- "查询伏笔状态" → 触发 webnovel-query
- "打开可视化面板" → 触发 webnovel-dashboard
- "项目体检" → 触发 webnovel-doctor

## 环境变量

Skill 被触发时会自动设置以下环境变量：

| 变量 | 值 | 用途 |
|------|-----|------|
| `PLUGIN_ROOT` | `~/.workbuddy/skills/webnovel-writer` | Skill 安装目录 |
| `SCRIPTS_DIR` | `${PLUGIN_ROOT}/scripts` | Python 脚本目录 |
| `PYTHON` | managed Python venv 路径 | Python 解释器 |
| `PYTHONPATH` | `${SCRIPTS_DIR}` | Python 模块搜索路径 |
| `WORKSPACE_ROOT` | `$PWD` | 当前工作区 |

## 与原始 Claude Code 版本的区别

1. **Hook 机制**：Claude Code 使用 `hooks.json` 自动拦截 Write/Edit 操作；WorkBuddy 版本将保护规则转为 SKILL.md 中的指令，agent 必须遵守。
2. **Agent 调用**：Claude Code 使用 `webnovel-writer:agent-name` 格式；WorkBuddy 使用 `Agent` 工具 + 读取 agent 文件作为 prompt。
3. **Session Start**：Claude Code 自动运行；WorkBuddy 由主 SKILL.md 触发时主动调用。
4. **目录结构**：Claude Code 使用 `skills/`；WorkBuddy 使用 `commands/`（通过符号链接 `skills -> commands` 保持兼容）。

## 文件结构

```
workbuddy-adaptation/
├── SKILL.md                    # 主路由 skill（WorkBuddy 入口）
├── install.sh                  # 安装脚本
├── convert_to_workbuddy.py     # 转换脚本（Claude Code → WorkBuddy）
├── commands/                   # 8 个命令文件
│   ├── webnovel-init/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── webnovel-write/
│   │   ├── SKILL.md
│   │   └── references/
│   └── ...
├── agents/                     # 4 个 Agent 定义
├── hooks/                      # Hook 脚本 + 适配说明
└── (scripts/, references/,     # 从原始项目复用，不在此目录
     templates/, dashboard/)    # 安装时从原始项目复制
```

## 许可证

继承原始项目 GPL-3.0 许可证。
