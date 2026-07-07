import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage


"""
TRY OUT

"Add docstrings to all functions in utils.py"
"Add type hints to all functions in utils.py"
"Create a README.md documenting the functions in utils.py"

"""


async def main():
    # Agentic loop: streams messages as Claude works
    async for message in query(
        prompt="add a new function to utils.py that calculates fibonacci numbers develop it test driven run them and fix any failures",
        options=ClaudeAgentOptions(
            allowed_tools=[
                "Read",
                "Edit",
                "Glob",
                "WebSearch",
                "Bash",
            ],  # Auto-approve these tools
            permission_mode="acceptEdits",  # Auto-approve file edits
            system_prompt="You are a senior Python developer. Always follow PEP 8 style guidelines.",
        ),
    ):
        # Print human-readable output
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)  # Claude's reasoning
                elif hasattr(block, "name"):
                    print(f"Tool: {block.name}")  # Tool being called
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")  # Final result


asyncio.run(main())
