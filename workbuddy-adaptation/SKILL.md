---
name: webnovel-writer
description: 长篇网文创作系统——解决 AI 写作中的「遗忘」和「幻觉」问题，支持 200 万字量级连载创作。覆盖初始化设定、规划卷纲、写章、审查、沉淀记忆、查询状态、可视化面板全流程。当用户需要创作网文/小说、初始化网文项目、规划卷纲、写章节、审查章节、查询设定/伏笔/角色状态、或打开可视化面板时触发。
---

# Webnovel Writer — 长篇网文创作系统

## 概述

这是一套面向长篇连载的一致性创作系统。它让 AI 写到几百章依然记得住设定、接得住伏笔、守得住大纲。

核心能力：动笔前先查资料，写完后把新发生的事实记下来、做一致性审查，再把最新状态同步进检索索引、章节摘要、长期记忆和 Dashboard。边写边攒，不是写完就忘。

## 环境设置（每次触发必须先执行）

```bash
export PLUGIN_ROOT="$HOME/.workbuddy/skills/webnovel-writer"
export SCRIPTS_DIR="${PLUGIN_ROOT}/scripts"
export PYTHON="/Users/supersam/.workbuddy/binaries/python/envs/default/bin/python3"
export PYTHONPATH="${PLUGIN_ROOT}/scripts:${PYTHONPATH:-}"
export WORKSPACE_ROOT="$PWD"

# 确认 Python 环境就绪
if [ ! -f "${PYTHON}" ]; then
  echo "ERROR: Python 环境未就绪。请运行 install.sh 安装依赖。" >&2
fi

# 确认脚本目录存在
if [ ! -d "${SCRIPTS_DIR}" ]; then
  echo "ERROR: 脚本目录不存在: ${SCRIPTS_DIR}" >&2
fi
```

## 命令路由

根据用户意图，读取对应的命令文件并按其指令执行。每个命令文件包含完整的执行流程、环境设置和验证规则。

| 用户意图 | 命令文件 | 说明 |
|---------|---------|------|
| 初始化新书、创建项目骨架、设定集、总纲 | `commands/webnovel-init/SKILL.md` | 深度初始化：分阶段问答收集信息，生成可直接进入规划与写作的项目骨架 |
| 规划卷纲、拆章、时间线 | `commands/webnovel-plan/SKILL.md` | 基于总纲生成卷纲、时间线和章纲，并把新增设定增量写回设定集 |
| 写章节、写正文 | `commands/webnovel-write/SKILL.md` | 一条龙写完一章：备上下文→起草→审查→润色→记录事实→自动备份 |
| 审查章节、质量检查 | `commands/webnovel-review/SKILL.md` | 从爽点、一致性、节奏、OOC、连贯性、追读力等维度审查章节 |
| 查询角色/伏笔/设定/状态 | `commands/webnovel-query/SKILL.md` | 查询角色、伏笔、节奏、实体关系和运行时信息 |
| 记录写作经验、学习模式 | `commands/webnovel-learn/SKILL.md` | 把这本书里好用的写法记下来，存进项目长期记忆 |
| 打开面板、可视化、Dashboard | `commands/webnovel-dashboard/SKILL.md` | 启动只读 Web 面板，查看项目状态、实体图谱与章节内容 |
| 体检、诊断、检查项目健康 | `commands/webnovel-doctor/SKILL.md` | 阶段感知检查目录、文件、数据库、RAG、依赖和 Dashboard 产物 |

## 路由规则

1. **识别命令**：根据用户输入的关键词匹配上表。
2. **读取命令文件**：用 `Read` 工具读取 `${PLUGIN_ROOT}/commands/<command>/SKILL.md`。
3. **执行命令**：严格按照命令文件中的流程执行。命令文件中的环境设置已包含在文件内，但主路由设置的环境变量同样有效。
4. **按需加载参考**：命令文件会指引何时读取 `references/`、`templates/` 下的文件，不要预读全部。

### 关键词速查

- **init**：初始化、新建书、创建项目、开始写新书、`/webnovel-init`
- **plan**：规划、卷纲、拆章、时间线、大纲、`/webnovel-plan`
- **write**：写章、写正文、第N章、更新章节、`/webnovel-write`
- **review**：审查、检查、质量、评分、`/webnovel-review`
- **query**：查询、伏笔、角色状态、设定、境界、`/webnovel-query`
- **learn**：记住、学习、经验、模式、`/webnovel-learn`
- **dashboard**：面板、可视化、Dashboard、看进度、`/webnovel-dashboard`
- **doctor**：体检、诊断、检查健康、`/webnovel-doctor`

## 系统架构

```
用户 → 主 Skill (路由) → 8 个命令文件 → Agent (context/reviewer/data/deconstruction)
                                           ↓
                                    .story-system/ (合同与提交链)
                                           ↓
                            .webnovel/state.json + index.db + summaries/ + memory/
                                           ↓
                                    Dashboard (只读面板)
```

**Story System 主链**：
- `.story-system/`：唯一的事实源头，动笔前的"合同"和写完后的"提交"都存在这里
- accepted 的 `CHAPTER_COMMIT`：一章写完，新事实从这里入账
- `.webnovel/state.json`、`index.db`、`summaries/`、`memory_scratchpad.json`：都是从主链派生出的只读视图

## Agent 使用说明

本系统有 4 个专用 Agent，定义在 `${PLUGIN_ROOT}/agents/` 目录：

| Agent | 文件 | 职责 |
|-------|------|------|
| context-agent | `agents/context-agent.md` | 写前 research，输出五段写作任务书 |
| reviewer | `agents/reviewer.md` | 质量审查，输出严格 reviewer schema JSON |
| data-agent | `agents/data-agent.md` | 从正文提取事实，产出三份 JSON artifact |
| deconstruction-agent | `agents/deconstruction-agent.md` | 参考作品拆解，返回结构化 JSON |

**调用方式**：使用 WorkBuddy 的 `Agent` 工具（subagent_type="general-purpose"），先 `Read` 对应的 agent 文件获取完整指令，然后将指令和任务参数一起作为 prompt 传入。

## 首次使用

如果是第一次使用，需要确保 Python 环境已安装依赖：

```bash
${PYTHON} -m pip install aiohttp filelock pydantic fastapi httpx "uvicorn[standard]" watchdog
```

然后从初始化开始：
1. 读取 `commands/webnovel-init.md` 并执行 → 创建书项目
2. 读取 `commands/webnovel-plan.md` 并执行 → 规划第一卷
3. 读取 `commands/webnovel-write.md` 并执行 → 写第一章
4. 读取 `commands/webnovel-review.md` 并执行 → 审查章节
5. 读取 `commands/webnovel-dashboard.md` 并执行 → 查看可视化面板

## 项目目录结构

初始化完成后会创建：

```
project-root/
├── .story-system/        # 合同、章节提交和事件审计
├── .webnovel/            # 状态、索引、摘要、备份和长期记忆
├── 正文/                  # 章节正文
├── 大纲/                  # 总纲、卷纲、时间线和章纲
├── 设定集/                # 世界观、角色、力量体系等设定
└── 审查报告/              # 章节审查报告
```

## 写入保护规则（必须遵守）

以下文件只能通过 `webnovel.py` 运行时命令修改，**禁止**用 Write/Edit 工具直接写入：

- `.story-system/commits/*` — 只能通过 `webnovel.py chapter-commit` 写入
- `.webnovel/index.db` — 投影链自动写入
- `.webnovel/vectors.db` — 投影链自动写入
- `.webnovel/memory_scratchpad.json` — 记忆模块自动写入
- `.webnovel/projection_log.jsonl` — 投影链自动写入

> `.webnovel/state.json` 不在保护清单中（审计可能需要直接修复）。详见 `hooks/README.md`。

## 注意事项

- Python 脚本入口：`${PYTHON} "${SCRIPTS_DIR}/webnovel.py"`
- 参考文件路径：共享参考在 `${PLUGIN_ROOT}/references/`，命令专属参考在 `${PLUGIN_ROOT}/commands/<command>/references/`
- 模板文件在 `${PLUGIN_ROOT}/templates/`
- Dashboard 前端已预构建，在 `${PLUGIN_ROOT}/dashboard/frontend/dist/`
- RAG 配置可选：未配置 Embedding Key 时自动退回 BM25 关键词检索
