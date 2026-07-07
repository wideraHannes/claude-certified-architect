"""
Agent SDK Hooks — minimal walkthrough (section 1.5).

Three built-in tools (Bash, Write, Read), three hook patterns. No MCP, no
custom tools — just the smallest possible code that shows WHERE a hook plugs
in and WHAT it can return.

  1. PreToolUse + deny        — block Write to a .env file.
  2. PreToolUse + updatedInput — rewrite a Bash `rm -rf /` into `echo blocked`.
  3. PostToolUse + updatedToolOutput — append a compliance banner to Bash output.

Every callback has the same shape:

    async def hook(input_data, _tool_use_id, _context) -> dict:
        ...
        return {"hookSpecificOutput": {...}}   # or return {}

Registration lives in ClaudeAgentOptions.hooks — one entry per event type,
each pointing to a HookMatcher whose `matcher` filters by tool name.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)


# Per-run trace so we can prove each hook fired.
events: list[str] = []


# ---------------------------------------------------------------------------
# Hook 1 — PreToolUse, DENY.
#
# Fires before Write executes. If the target path ends in ".env", return
# permissionDecision="deny". The tool never runs; the model sees the reason
# and moves on. This is the canonical "block dangerous op" pattern.
# ---------------------------------------------------------------------------
async def block_env_writes(
    input_data: dict[str, Any], _tool_use_id: str | None, _context: Any
) -> dict[str, Any]:
    _ = (_tool_use_id, _context)  # reserved by the SDK signature
    file_path = input_data["tool_input"].get("file_path", "")
    if Path(file_path).name == ".env":
        events.append(f"DENIED Write to {file_path}")
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "deny",
                "permissionDecisionReason": ".env files are read-only in this session.",
            }
        }
    return {}


# ---------------------------------------------------------------------------
# Hook 2 — PreToolUse, MODIFY INPUT.
#
# Fires before Bash executes. If the command contains "rm -rf", swap it for
# a harmless echo. `updatedInput` goes inside hookSpecificOutput, and MUST be
# paired with permissionDecision="allow" or the modification is silently
# dropped.
# ---------------------------------------------------------------------------
async def defang_rm_rf(
    input_data: dict[str, Any], _tool_use_id: str | None, _context: Any
) -> dict[str, Any]:
    _ = (_tool_use_id, _context)
    command = input_data["tool_input"].get("command", "")
    if "rm -rf" in command:
        events.append(f"DEFANGED bash: {command!r}")
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "allow",
                "updatedInput": {
                    **input_data["tool_input"],
                    "command": "echo 'blocked by hook: rm -rf disallowed'",
                },
            }
        }
    return {}


# ---------------------------------------------------------------------------
# Hook 3 — PostToolUse, REWRITE OUTPUT.
#
# Fires after Bash returns, before the model reads the result. Append a
# banner so the model always sees a compliance footer. In real code this is
# where you'd normalize dates, redact secrets, or unify status codes across
# heterogeneous tools.
# ---------------------------------------------------------------------------
async def annotate_bash_output(
    input_data: dict[str, Any], _tool_use_id: str | None, _context: Any
) -> dict[str, Any]:
    _ = (_tool_use_id, _context)
    response = input_data.get("tool_response")
    # Built-in Bash returns a dict with stdout/stderr fields; MCP tools return
    # a content-block list. Support both by extracting a text payload.
    text = ""
    if isinstance(response, dict):
        if "stdout" in response or "stderr" in response:
            text = (response.get("stdout") or "") + (response.get("stderr") or "")
        else:
            blocks = response.get("content") or []
            if blocks and isinstance(blocks[0], dict):
                text = blocks[0].get("text", "")
    elif isinstance(response, list) and response:
        first = response[0]
        text = first.get("text", "") if isinstance(first, dict) else getattr(first, "text", "")
    if not text:
        events.append(f"PostToolUse saw unrecognized response shape: {type(response).__name__}")
        return {}
    events.append(f"ANNOTATED Bash output ({len(text)} chars)")
    return {
        "hookSpecificOutput": {
            "hookEventName": input_data["hook_event_name"],
            "updatedToolOutput": f"{text}\n---\n[audit] reviewed by post-tool hook",
        }
    }


# ---------------------------------------------------------------------------
# Wire the three hooks into options. Read this as the "table of contents":
#   event -> matcher (which tool) -> callback.
# ---------------------------------------------------------------------------
def _build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model="sonnet",
        allowed_tools=["Bash", "Write", "Read"],
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Write", hooks=[block_env_writes]),
                HookMatcher(matcher="Bash",  hooks=[defang_rm_rf]),
            ],
            "PostToolUse": [
                HookMatcher(matcher="Bash", hooks=[annotate_bash_output]),
            ],
        },
        permission_mode="acceptEdits",
        tool_choice
    )


async def _run(label: str, prompt: str) -> None:
    events.clear()
    async with ClaudeSDKClient(options=_build_options()) as client:
        await client.query(prompt)
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, ToolUseBlock):
                        print(f"  [tool] {b.name}({b.input})")
                    elif isinstance(b, TextBlock) and b.text.strip():
                        print(f"  [say ] {b.text.strip()[:160]}")
            elif isinstance(msg, ResultMessage) and msg.result:
                print(f"  [final] {msg.result[:200]}")
    print(f"=== {label} ===")
    for e in events:
        print(f"  [event] {e}")


async def main() -> None:
    await _run(
        "hook 1: PreToolUse deny",
        "Use the Write tool to create the file '/tmp/hooks-demo/.env' with the "
        "content 'SECRET=1'. Do not check whether it exists first — just call "
        "Write directly. If the tool is denied, report the reason and stop.",
    )
    assert any(e.startswith("DENIED") for e in events), events

    await _run(
        "hook 2: PreToolUse modify input",
        "Run this exact shell command with the Bash tool: rm -rf /tmp/does-not-exist",
    )
    assert any(e.startswith("DEFANGED") for e in events), events

    await _run(
        "hook 3: PostToolUse rewrite output",
        "Run `echo hello` with the Bash tool and repeat back everything the tool returned verbatim.",
    )
    assert any(e.startswith("ANNOTATED") for e in events), events

    print("\nall three hook patterns fired.")


if __name__ == "__main__":
    asyncio.run(main())
