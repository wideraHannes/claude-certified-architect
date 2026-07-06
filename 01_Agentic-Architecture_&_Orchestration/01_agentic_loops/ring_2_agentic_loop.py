import json

from config import client, settings


"""Ring 1 assumed Claude would call the tool exactly once. Real tasks often need several calls: Claude might create an event, read the confirmation, then create another. The fix is a while loop that keeps running tools and feeding results back until stop_reason is no longer "tool_use".

The other change is conversation history. Instead of rebuilding the messages array from scratch on each request, keep a running list and append to it. Every turn sees the complete prior context."""

tools = [
    {
        "name": "web_search",
        "description": "Retrieves the most releveant information that it could find but only talks about the Star Wars universe. If asked to talk about other topics, it will respond with starwars lore. It will not make up information about the Star Wars universe.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                }
            },
            "required": ["query"],
        },
    }
]


def run_tool(name, tool_input):
    if name == "web_search":
        return {
            "query": f"Results for query '{tool_input['query']}'",
        }
    return {"error": f"Unknown tool: {name}"}


messages = [{"role": "user", "content": "How will be the weather today?"}]


response = client.messages.create(
    model=settings.default_model,
    tools=tools,
    max_tokens=1024,
    messages=messages,
)


## Building the Agentic loop

while response.stop_reason == "tool_use":
    tool_use = next(block for block in response.content if block.type == "tool_use")
    result = run_tool(tool_use.name, tool_use.input)
    print("=======Tool result======:", result)
    messages.append({"role": "assistant", "content": response.content})
    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps(result),
                }
            ],
        }
    )
    response = client.messages.create(
        model=settings.default_model,
        max_tokens=1024,
        tools=tools,
        tool_choice={"type": "auto", "disable_parallel_tool_use": True},
        messages=messages,
    )


final_text = next(block for block in response.content if block.type == "text")
print(final_text.text)
