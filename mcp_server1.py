from mcp.server.fastmcp import FastMCP

mcp = FastMCP("places-server", port=8000)

BEACH = ["Goa", "Maldives", "Bali", "Phuket"]
HILL = ["Manali", "Shimla", "Darjeeling", "Ooty"]
CITY = ["Dubai", "Singapore", "Paris", "Tokyo"]

@mcp.tool()
async def suggest_places(preference: str) -> dict:
    preference = preference.lower()

    if "beach" in preference:
        places = BEACH
    elif "hill" in preference or "mountain" in preference:
        places = HILL
    elif "city" in preference:
        places = CITY
    else:
        places = ["Kerala", "Bhutan", "Switzerland", "Bali"]

    return {
        "places": places   # 🔥 return ALL, not 2
    }

mcp.run()