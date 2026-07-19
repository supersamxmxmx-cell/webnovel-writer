# Webnovel Writer 仓库指南

## 环境

- 默认开发环境为 macOS 与 zsh，Python 要求 3.10 或更高版本。
- 从仓库根目录运行命令；插件根目录是 `webnovel-writer/`。
- 安装依赖时使用 `python3 -m pip`，不要假设系统存在 `python` 别名。
- 不读取、打印或提交 `.env` 中的 API Key；示例配置只写占位值。

## 架构边界

- `.story-system/` 与 accepted `CHAPTER_COMMIT` 是书项目事实源。
- `.webnovel/state.json`、索引、摘要、长期记忆和 Dashboard 都是派生视图。
- `webnovel-writer/skills/` 是 Claude Code 与 Codex 共用的 Skill 单一来源；不要复制一套 Codex 专用流程。
- Codex 插件清单位于 `webnovel-writer/.codex-plugin/plugin.json`，仓库 Marketplace 位于 `.agents/plugins/marketplace.json`。
- Claude 专属 Hook 不应直接注册到 Codex；需要跨宿主的行为应放在共用 Skill 或 Python 数据链中。

## 修改约束

- 修改 Skill 时保留 YAML frontmatter 的 `name` 与 `description`，并同步检查 `agents/openai.yaml`。
- Python 命令默认通过 `PYTHON_BIN`（默认 `python3`）执行，插件资源通过 `PLUGIN_ROOT` 解析。
- 写章主链必须保留 prewrite、precommit、postcommit gate，以及 review、data、commit、projection、backup 阶段。
- 不通过降低覆盖率阈值、排除核心模块或伪造 artifact 来让测试通过。

## 验证

提交前至少从仓库根目录运行：

```bash
python3 -m pytest
python3 webnovel-writer/scripts/run_behavior_evals.py --suite fast
```

测试要求全部通过且核心数据模块覆盖率不低于 90%。修改 Codex 入口时还要运行：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -c /dev/null \
  --confcutdir=webnovel-writer/scripts/tests \
  webnovel-writer/scripts/tests/test_codex_adaptation.py -q
```
