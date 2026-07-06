import json

from config import client, settings


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
    },
    {
        "name": "list_planets",
        "description": "Lists the ten planets known in the Star Wars universe.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


STAR_WARS_PLANETS = [
    "Tatooine",
    "Naboo",
    "Coruscant",
    "Alderaan",
    "Hoth",
    "Dagobah",
    "Bespin",
    "Endor",
    "Kamino",
    "Mustafar",
]


def run_tool(name, tool_input):
    if name == "web_search":
        return {
            "query": f"Results for query '{tool_input['query']}'",
        }
    if name == "list_planets":
        return {"planets": STAR_WARS_PLANETS}
    return {"error": f"Unknown tool: {name}"}


messages = [
    {
        "role": "user",
        "content": "How will be the weather today and which planets exist in the Star Wars universe?",
    }
]


response = client.messages.create(
    model=settings.default_model,
    tools=tools,
    max_tokens=1024,
    messages=messages,
)


## Building the Agentic loop

while response.stop_reason == "tool_use":
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            result = run_tool(block.name, block.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            )
            print("=======Tool result======:", result)

    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": tool_results})

    response = client.messages.create(
        model=settings.default_model,
        max_tokens=1024,
        tools=tools,
        messages=messages,
    )


final_text = next(block for block in response.content if block.type == "text")
print(final_text.text)
