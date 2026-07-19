# Codex 使用指南

## 适配范围

Codex 原生插件入口位于 [`webnovel-writer/.codex-plugin/plugin.json`](../../webnovel-writer/.codex-plugin/plugin.json)，仓库插件目录位于 [`.agents/plugins/marketplace.json`](../../.agents/plugins/marketplace.json)，技能位于 `webnovel-writer/skills/`。Codex 与 Claude Code 共用同一份完整 Skill、`scripts/`、`agents/`、`references/`、`templates/` 与 `dashboard/`，因此不会出现双份流程漂移，也操作同一套书项目数据。

Skill 在 Claude Code 中优先使用其宿主环境变量，在 Codex 中把 `<plugin root>` 解析为当前插件的绝对目录；Codex manifest 不注册 Claude Hook。书项目根目录始终从当前工作目录经 `webnovel.py where` 解析；初始化新书是唯一例外，因为目标目录尚不存在。

## 安装

从 GitHub 仓库添加 Marketplace 并安装插件：

```bash
codex plugin marketplace add supersamxmxmx-cell/webnovel-writer
codex plugin add webnovel-writer@webnovel-writer-marketplace
```

开发本地检出版本时，在仓库根目录运行：

```bash
codex plugin marketplace add .
codex plugin add webnovel-writer@webnovel-writer-marketplace
```

安装或更新后新建 Codex 任务，以重新加载插件技能。若使用 ChatGPT 桌面端，也可以在 Plugins Directory 中选择该 Marketplace 后安装。

## 工作流

| 意图 | Codex 技能 | 关键约束 |
| --- | --- | --- |
| 初始化新书 | `webnovel-init` | 先采集并确认故事核，后写 canon |
| 规划卷纲 | `webnovel-plan` | 时间线、节点承接与合同必须通过 |
| 创作章节 | `webnovel-write` | 预写/提交前/提交后 gate 全部通过 |
| 独立审查 | `webnovel-review` | reviewer 只产 JSON，pipeline 生成报告 |
| 查询资料 | `webnovel-query` | 最窄查询、全程只读 |
| 沉淀经验 | `webnovel-learn` | 仅记录作者明确认可的模式 |
| 诊断 | `webnovel-doctor` | 只读，不自动修复或安装依赖 |
| 可视化 | `webnovel-dashboard` | 只读本地面板 |

当工作流需要 context、reviewer、data 或 deconstruction agent 时，Codex 将原代理提示词交给隔离子任务；若当前表面没有子任务能力，则按同一提示词内联执行，并在最终报告中明确标注降级。审查 JSON、事实 artifact 与 Story System 投影的写入所有权不因执行方式改变。

## 运行时

插件会使用当前 `python3`，也可通过 `PYTHON_BIN` 指向已安装项目依赖的 Python。首次使用前可按项目原有依赖清单安装：

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -r webnovel-writer/scripts/requirements.txt
```

每个会写入书项目的流程以 `user-report` 结束，并向作者交付完成文件、自动处理项、必须裁决的问题及下一步任务。技术日志保留在书项目的 `.webnovel/logs/run_last.log`，不作为常规输出。

## 开发校验

Codex 适配至少检查四件事：插件 manifest 指向标准 `skills/`；八个 Skill 的 YAML frontmatter 合法；每个 Skill 都能独立解析插件根与 Python；所有 Skill 保留完整原流程。对应回归测试：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -c /dev/null \
  --confcutdir=webnovel-writer/scripts/tests \
  webnovel-writer/scripts/tests/test_codex_adaptation.py -q
```
