from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("multi-tools", host="0.0.0.0", port=9000)

# 🌦️ Weather (GLOBAL - Open Meteo)
@mcp.tool()
async def get_weather(city: str) -> str:
    import httpx, json

    # Clean input
    city = city.lower().replace("weather", "").replace("in", "").strip()

    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"

    async with httpx.AsyncClient() as client:
        geo_res = await client.get(geo_url)
        geo_data = geo_res.json()

    if "results" not in geo_data or not geo_data["results"]:
        return f"Location not found for '{city}'"

    lat = geo_data["results"][0]["latitude"]
    lon = geo_data["results"][0]["longitude"]

    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"

    async with httpx.AsyncClient() as client:
        res = await client.get(weather_url)
        data = res.json()

    return json.dumps(data.get("current_weather", {}))
# 📈 Stock (Alpha Vantage)
@mcp.tool()
async def get_stock_price(symbol: str) -> str:
    """Get latest stock price for a symbol like AAPL, TSLA."""
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"

    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()

    return str(data["Global Quote"])


if __name__ == "__main__":
    mcp.run()