import json

from config import client, settings

"""
Tools fail. A calendar API might reject an event with too many attendees, or a date might be malformed. When a tool raises an error, send the error message back with is_error: true instead of crashing. Claude reads the error and can retry with corrected input, ask the user for clarification, or explain the limitation.
"""


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
    {
        "name": "get_planet_info",
        "description": "Returns a short description of a Star Wars planet by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The planet's name, e.g. 'Tatooine'.",
                }
            },
            "required": ["name"],
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
    if name == "get_planet_info":
        planet = tool_input["name"]
        if planet not in STAR_WARS_PLANETS:
            raise ValueError(
                f"'{planet}' is not a known Star Wars planet. "
                f"Call list_planets to see valid options."
            )
        return {"name": planet, "info": f"{planet} is a well-known planet in the Star Wars universe."}
    raise ValueError(f"Unknown tool: {name}")


messages = [
    {
        "role": "user",
        "content": "Tell me about the planets Coruscant and Mordor from Star Wars.",
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
            try:
                result = run_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    }
                )
                print("=======Tool result======:", result)
            except Exception as exc:
                # Signal failure so Claude can retry or ask for clarification.
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(exc),
                        "is_error": True,
                    }
                )
                print("=======Tool error=======:", exc)

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
