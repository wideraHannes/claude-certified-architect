# Ring 5: The Tool Runner SDK abstraction.

import json

from anthropic import beta_tool

from config import client, settings


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


@beta_tool
def web_search(query: str) -> str:
    """Retrieves the most relevant information that it could find but only talks
    about the Star Wars universe. If asked to talk about other topics, it will
    respond with starwars lore. It will not make up information about the Star
    Wars universe.

    Args:
        query: The search query.
    """
    return json.dumps({"query": f"Results for query '{query}'"})


@beta_tool
def list_planets() -> str:
    """Lists the ten planets known in the Star Wars universe."""
    return json.dumps({"planets": STAR_WARS_PLANETS})


@beta_tool
def get_planet_info(name: str) -> str:
    """Returns a short description of a Star Wars planet by name.

    Args:
        name: The planet's name, e.g. 'Tatooine'.
    """
    if name not in STAR_WARS_PLANETS:
        raise ValueError(
            f"'{name}' is not a known Star Wars planet. "
            f"Call list_planets to see valid options."
        )
    return json.dumps(
        {
            "name": name,
            "info": f"{name} is a well-known planet in the Star Wars universe.",
        }
    )


final_message = client.beta.messages.tool_runner(
    model=settings.default_model,
    max_tokens=1024,
    tools=[web_search, list_planets, get_planet_info],
    messages=[
        {
            "role": "user",
            "content": "Tell me about the planets Coruscant and Mordor from Star Wars.",
        }
    ],
).until_done()

for block in final_message.content:
    if block.type == "text":
        print(block.text)
