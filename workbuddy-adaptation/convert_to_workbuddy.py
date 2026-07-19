#!/usr/bin/env python3
"""
Convert Claude Code webnovel-writer skills to WorkBuddy command format.

Handles:
- Frontmatter: remove allowed-tools, argument-hint; keep name, description
- Env vars: CLAUDE_PLUGIN_ROOT -> PLUGIN_ROOT, CLAUDE_PROJECT_DIR -> PWD
- Path refs: skills/webnovel-X -> commands/webnovel-X
- Python: python -X utf8 -> ${PYTHON}
- Agent refs: webnovel-writer:agent-name -> read agent file + Agent tool
"""
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent  # ~/.workbuddy/skills/webnovel-writer
SRC_ROOT = Path("/Users/supersam/Workbuddy/webnovel-writer进行workbuddy兼容/webnovel-writer/webnovel-writer/skills")

COMMANDS = [
    "webnovel-init",
    "webnovel-plan",
    "webnovel-write",
    "webnovel-review",
    "webnovel-query",
    "webnovel-learn",
    "webnovel-dashboard",
    "webnovel-doctor",
]

# Agent name -> description for the Agent tool prompt
AGENT_DESCRIPTIONS = {
    "context-agent": "上下文压缩器：先 research，再输出五段写作任务书",
    "data-agent": "数据提取器：从正文提取 fulfillment/disambiguation/extraction 三份 JSON",
    "deconstruction-agent": "参考作品拆解器：拆解参考作品并返回结构化 JSON",
    "reviewer": "质量审查器：输出严格 reviewer schema JSON",
}


def convert_frontmatter(content: str, cmd_name: str) -> str:
    """Remove allowed-tools and argument-hint from frontmatter."""
    lines = content.split("\n")
    if not lines[0].strip() == "---":
        return content

    result = ["---"]
    in_frontmatter = False
    for line in lines[1:]:
        if line.strip() == "---":
            result.append(line)
            break
        # Skip Claude Code-specific fields
        if line.startswith("allowed-tools:"):
            continue
        if line.startswith("argument-hint:"):
            continue
        result.append(line)

    # Add everything after frontmatter
    idx = lines.index("---", 1) if "---" in lines[1:] else len(lines)
    result.extend(lines[idx + 1:])
    return "\n".join(result)


def convert_env_vars(content: str) -> str:
    """Replace Claude Code environment variables with WorkBuddy equivalents."""
    # CLAUDE_PROJECT_DIR fallback
    content = content.replace('${CLAUDE_PROJECT_DIR:-$PWD}', '$PWD')
    content = content.replace('${CLAUDE_PROJECT_DIR:-"${PWD}"}', '$PWD')

    # CLAUDE_PLUGIN_ROOT references
    # ${CLAUDE_PLUGIN_ROOT:?} -> ${PLUGIN_ROOT}
    content = content.replace('${CLAUDE_PLUGIN_ROOT:?}', '${PLUGIN_ROOT}')
    # ${CLAUDE_PLUGIN_ROOT} -> ${PLUGIN_ROOT}
    content = content.replace('${CLAUDE_PLUGIN_ROOT}', '${PLUGIN_ROOT}')

    # CLAUDE_PLUGIN_ROOT in error messages
    content = content.replace('CLAUDE_PLUGIN_ROOT', 'PLUGIN_ROOT')

    # SKILL_ROOT path: was ${PLUGIN_ROOT}/skills/webnovel-X -> ${PLUGIN_ROOT}/commands/webnovel-X
    for cmd in COMMANDS:
        content = content.replace(
            f'${{PLUGIN_ROOT}}/skills/{cmd}',
            f'${{PLUGIN_ROOT}}/commands/{cmd}'
        )

    # Now fix SKILL_ROOT assignments
    # export SKILL_ROOT="${PLUGIN_ROOT}/skills/webnovel-X" -> export COMMAND_ROOT="${PLUGIN_ROOT}/commands/webnovel-X"
    for cmd in COMMANDS:
        content = content.replace(
            f'export SKILL_ROOT="${{PLUGIN_ROOT}}/commands/{cmd}"',
            f'export COMMAND_ROOT="${{PLUGIN_ROOT}}/commands/{cmd}"'
        )

    # Replace remaining SKILL_ROOT references with COMMAND_ROOT
    content = content.replace('${SKILL_ROOT}', '${COMMAND_ROOT}')
    content = content.replace('$SKILL_ROOT', '$COMMAND_ROOT')

    return content


def convert_python(content: str) -> str:
    """Replace python -X utf8 with ${PYTHON}."""
    # python -X utf8 "${SCRIPTS_DIR}/..." -> ${PYTHON} "${SCRIPTS_DIR}/..."
    content = content.replace('python -X utf8 ', '${PYTHON} ')
    # Standalone python calls that reference SCRIPTS_DIR
    content = re.sub(
        r'(?<![A-Za-z_])python ("|\')\$\{SCRIPTS_DIR\}',
        r'${PYTHON} \1${SCRIPTS_DIR}',
        content
    )
    # python -m dashboard.server -> ${PYTHON} -m dashboard.server
    content = re.sub(r'(?<![A-Za-z_])python -m dashboard', '${PYTHON} -m dashboard', content)
    # python -m pip install -> ${PYTHON} -m pip install
    content = re.sub(r'(?<![A-Za-z_])python -m pip', '${PYTHON} -m pip', content)

    return content


def convert_agent_refs(content: str) -> str:
    """Convert Claude Code agent references to WorkBuddy format."""
    for agent_name, desc in AGENT_DESCRIPTIONS.items():
        # "Use the Agent tool to run `webnovel-writer:agent-name`."
        old = f"Use the Agent tool to run `webnovel-writer:{agent_name}`."
        new = (
            f"Use the Agent tool (subagent_type=\"general-purpose\") to run a {agent_name} task. "
            f"Read `${{PLUGIN_ROOT}}/agents/{agent_name}.md` for the agent's full instructions, "
            f"then pass those instructions plus the task parameters below as the prompt."
        )
        content = content.replace(old, new)

        # "调用 `webnovel-writer:agent-name`"
        content = content.replace(
            f"`webnovel-writer:{agent_name}`",
            f"`{agent_name}` (see `${{PLUGIN_ROOT}}/agents/{agent_name}.md`)"
        )

        # "Agent` 工具调用 `webnovel-writer:agent-name`"
        content = content.replace(
            f"调用 `webnovel-writer:{agent_name}`",
            f"调用 `{agent_name}` (读取 `${{PLUGIN_ROOT}}/agents/{agent_name}.md`)"
        )

    return content


def add_env_setup(content: str, cmd_name: str) -> str:
    """Add WorkBuddy environment setup at the top of the command, after the first heading."""
    env_setup = f"""
## WorkBuddy 环境设置（必须先执行）

```bash
export PLUGIN_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"
# Fallback if readlink not available
if [ -z "${{PLUGIN_ROOT}}" ] || [ ! -d "${{PLUGIN_ROOT}}/scripts" ]; then
  export PLUGIN_ROOT="$HOME/.workbuddy/skills/webnovel-writer"
fi
export SCRIPTS_DIR="${{PLUGIN_ROOT}}/scripts"
export COMMAND_ROOT="${{PLUGIN_ROOT}}/commands/{cmd_name}"
export PYTHON="/Users/supersam/.workbuddy/binaries/python/envs/default/bin/python3"
export PYTHONPATH="${{PLUGIN_ROOT}}/scripts:${{PYTHONPATH:-}}"
export WORKSPACE_ROOT="$PWD"
```

> 以上环境变量由 webnovel-writer skill 设置。如果直接执行命令文件，请确保 PLUGIN_ROOT 指向 `~/.workbuddy/skills/webnovel-writer`。
"""

    # Find the first markdown heading after frontmatter
    lines = content.split("\n")
    insert_idx = 0
    in_frontmatter = False
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
            else:
                insert_idx = i + 1
                break

    if insert_idx == 0:
        insert_idx = 1

    # Find the first heading
    for i in range(insert_idx, len(lines)):
        if lines[i].startswith("#"):
            insert_idx = i + 1
            break

    lines.insert(insert_idx, env_setup)
    return "\n".join(lines)


def convert_command(cmd_name: str):
    """Convert a single command file."""
    src = SRC_ROOT / cmd_name / "SKILL.md"
    if not src.exists():
        print(f"  SKIP {cmd_name}: source not found")
        return

    content = src.read_text(encoding="utf-8")

    # Apply conversions
    content = convert_frontmatter(content, cmd_name)
    content = convert_env_vars(content)
    content = convert_python(content)
    content = convert_agent_refs(content)
    content = add_env_setup(content, cmd_name)

    # Write to commands directory
    dst = SKILL_ROOT / "commands" / f"{cmd_name}.md"
    dst.write_text(content, encoding="utf-8")
    print(f"  OK {cmd_name} -> {dst}")


def main():
    print("Converting Claude Code skills to WorkBuddy commands...")
    for cmd in COMMANDS:
        convert_command(cmd)
    print("Done!")


if __name__ == "__main__":
    main()
