"""The Part 1 coding agent: fix a software issue and submit a git patch."""

from __future__ import annotations

import json
from typing import Any

from assignment.agent.base import (
    DEFAULT_COMPACTION_KEEP_RECENT_STEPS,
    DEFAULT_COMPACTION_MAX_TOKENS,
    Agent,
    format_tool_output,
)
from assignment.agent.tools import EXECUTE_TOOL, SEND_MESSAGE_TOOL
from assignment.env import Environment

class CodeAgent(Agent):
    """An agent that fixes a software issue and submits a git patch."""

    def __init__(
        self,
        task: str,
        environment: Environment,
        model: str | None = None,
        logs_save_path: str | None = None,
        step_limit: int = 100,
        skills_path: str | None = None,
        auto_stop_environment: bool = True,
        compact_threshold_tokens: int | None = None,
        compaction_keep_recent_steps: int = DEFAULT_COMPACTION_KEEP_RECENT_STEPS,
        compaction_max_tokens: int = DEFAULT_COMPACTION_MAX_TOKENS,
    ):
        super().__init__(
            environment=environment,
            model=model,
            logs_save_path=logs_save_path,
            step_limit=step_limit,
            skills_path=skills_path,
            auto_stop_environment=auto_stop_environment,
            compact_threshold_tokens=compact_threshold_tokens,
            compaction_keep_recent_steps=compaction_keep_recent_steps,
            compaction_max_tokens=compaction_max_tokens,
        )
        self.task = task
        self.submitted_patch = ""

        # TODO(Part 1.3): Make the `execute` and `send_message` tools available
        # to the agent.
        self.tools.append(EXECUTE_TOOL)
        self.tools.append(SEND_MESSAGE_TOOL)

        # TODO(1.1.b): Construct the system prompt and task_prompt. These
        # should be usable by the `Agent.build_prompt` method.
        system_information = json.dumps(
            {
                "machine": self.env.machine,
                "release": self.env.release,
                "system": self.env.system,
                "version": self.env.version,
            },
            indent=2,
        )
        self.system_prompt = f"""You are a software engineering agent working in a terminal.
Use the available tools to investigate and fix the issue.
Do not stop until the issue is resolved.

<system_information>
{system_information}
</system_information>
"""
        self.task_prompt = self.task
        # TODO(1.4): If any skills are available to the agent, make their
        # descriptions/metadata available to the agent in the prompt.
        if self.skills:
            catalog = "\n".join(skill["metadata"] for skill in self.skills.values())
            self.system_prompt += (
                "\n\nReusable skills are available. Call `invoke_skill` with a "
                "skill's name to load its instructions, and follow them in place "
                f"of your default approach.\n\n<skills>\n{catalog}\n</skills>\n"
            )

    def execute_tool_calls(
        self, tool_calls: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """Execute ``execute`` and ``send_message`` calls in the code sandbox."""

        # TODO(Part 1.3): Parse each call, execute recognized tools, and return
        # one message per call (there may be multiple tool calls in one agent
        # response!). Malformed JSON and unknown tools must become recoverable
        # observations relayed to the agent instead of exceptions.
        observations = []
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]
            tool_id = tool_call["id"]

            try:
                args = json.loads(tool_args)
            except json.JSONDecodeError as exc:
                observations.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": f"Malformed tool arguments: {exc}",
                })
                continue

            if tool_name == "execute":
                output = self.env.execute(
                    args.get("command"),
                    timeout=args.get("timeout"),
                    cwd=args.get("cwd"),
                    env=args.get("env"),
                    shell=args.get("shell"),
                )
                content = format_tool_output(output)
            elif tool_name == "send_message":
                self.finished = True
                content = args.get("summary", "")
            elif tool_name == "invoke_skill":
                skill_name = args.get("name")
                if skill_name not in self.skills:
                    content = f"Unknown skill: {skill_name}"
                else:
                    content = self.skills[skill_name]["content"]
            else:
                content = f"Unknown tool: {tool_name}"

            observations.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": content,
            })

        return observations