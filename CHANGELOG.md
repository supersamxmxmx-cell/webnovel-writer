# 更新日志

这里记录每个正式版本对作者和维护者的影响。发布说明优先面向中文网文作者：先说写作体验有什么变化，再补维护者关心的技术细节。

## v6.2.3 - Codex 与 Dashboard 回到同一条稳定主线

发版范围：`v6.2.1..v6.2.3`。

### 给作者看的变化

- Claude Code 与 Codex 现在共用同一套写作 Skill、数据链和 `master` 主线，不会再出现安装了新版本却看不到另一宿主功能的情况。
- 只读 Dashboard 的文档浏览会直接渲染 Markdown；JSON 使用缩进格式化展示，每个字段单独成行，长篇设定和状态文件更容易阅读。
- Dashboard 新增「里程一览」，可以按“卷 → 阶段 → 章节”展开；详细卷纲中尚未写作的章节也会显示，并区分已完成、进行中和计划中。
- 人物、物品、能力等故事要素的进展集中展示，便于快速检查每卷推进情况。
- 同时纳入上游开放环聚合、文风记忆消费修复和 WorkBuddy 集成。

### 是否需要改旧项目

不需要。旧书项目无需迁移；Dashboard 会读取现有详细卷纲、索引、状态和数据库，缺失某类派生数据时会降级展示已有内容。

### 给维护者

- 在 Codex 插件清单、仓库 Marketplace、共用 Skill 及 `agents/openai.yaml` 的基础上完成双宿主适配，并保留写章全链路 gate。
- 新增 Dashboard `/api/milestones` 聚合接口、详细卷纲解析器、里程碑页面、Markdown/JSON 只读预览及相应测试和构建产物。
- 版本同步与插件包校验现在同时检查 Claude 和 Codex 清单，防止两个宿主再次出现版本漂移。

### 验证

- 全量 pytest、核心数据模块覆盖率、fast behavior eval 与 Codex 适配测试通过。
- Dashboard 前端构建、插件包校验、版本同步和发布说明校验通过。

## v6.2.1 - 修复 Windows 下写章提交偶发的「拒绝访问」

发版范围：`v6.2.0..v6.2.1`。

### 给作者看的变化

- 修复 Windows 上写章提交时偶发的 `WinError 5（拒绝访问）`：`.webnovel/` 下的故事资料文件被 VSCode、杀毒软件或同步盘短暂占用时，系统会自动等待并重试，不再直接失败（#125）。
- 建议 VSCode 用户把 `**/.webnovel/**` 加入 `files.watcherExclude`，项目尽量不放同步盘目录，可进一步降低占用冲突。

### 是否需要改旧项目

不需要。已有书项目继续使用，无需任何迁移。

### 给维护者

- `atomic_write_json` 的 `os.replace` 遇 `PermissionError` 改为指数退避重试（约 2.6 秒窗口），穷尽后如实抛错；全部 JSON 投影共用该写入函数，一并受益。
- 新增 4 个针对性测试，含 Windows 真实句柄占用复现。

### 验证

- 全量 pytest 通过（774 passed）。
- 版本同步、发布说明与插件包校验通过。

## v6.2.0 - 写章结果更清楚，失败后更好恢复

发版范围：`v6.1.0..v6.2.0`。

### 给作者看的变化

- 写章、审查、规划和初始化结束后，最终报告更像写作助手的汇报：会说明已完成、部分完成、需要你处理或未完成。
- `/webnovel-write` 中断后，重复执行同一章会优先检查可信断点，尽量从失败位置继续，减少重写和误覆盖。
- 写章过程减少技术细节打扰；只有创作方向、事实取舍、文件覆盖风险或阻断问题需要裁决时才询问。
- 写作流程的上下文读取更克制，初始化、规划、写章、审查、查询等命令更聚焦，减少无关资料塞满上下文。
- 章节提交前后的中间结果校验更稳，能更早发现缺失的审查、事实提取或故事资料同步结果。
- 文档补充了最终报告读法、恢复边界、日志用途和常见运维入口。

### 是否需要改旧项目

不需要。已有书项目可以继续使用，不需要迁移 `.story-system/` 或 `.webnovel/` 数据。

### 给维护者

- 新增作者术语表、异常目录、审查作者视图、最终报告 helper、写章 run ledger、脱敏 run log。
- 新增 `user-report`、`run-ledger`、`run-log` 统一 CLI 子命令。
- 收紧 commit artifacts、projection writers、write-gate 和 postcommit 的结构化校验。
- 轻量化多个 Skill / Agent 的提示词，补充 reference loading map 和 region-read 规则。
- 增加 prompt integrity、unit tests、behavior eval，覆盖 artifact ownership、最小写章模式、projection retry、blocking review、断点续跑和日志脱敏。
- `Plugin Release` 工作流改为推送到 `master` 后自动发版，并保留手动兜底入口。

### 验证

- 相关 pytest 通过。
- behavior eval 通过。
- `compileall` 通过。
- `git diff --check` 通过。
- 版本同步和插件包校验通过。

## v6.1.0 - 项目体检更稳，出问题更容易定位

- 增加 doctor、project-status、write-gate、projection 重放、hooks、行为评估和插件包校验。
- 强化 Story System 运行时健康检查和 Marketplace 发布校验。

## v6.0.0 - Story System 主链上线，长篇事实更不容易写乱

- 上线合同种子、运行时合同、章节提交、事件审计和投影链路。
- 补齐主链相关集成测试。
