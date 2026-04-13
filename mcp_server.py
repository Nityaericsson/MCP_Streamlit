from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("multi-tools", host="0.0.0.0", port=8000)

# 🌦️ Weather (GLOBAL - Open Meteo)
@mcp.tool()
async def get_weather(latitude: float, longitude: float) -> str:
    """Get current weather using latitude & longitude."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"

    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()

    return str(data["current_weather"])


# 📈 Stock (Alpha Vantage)
@mcp.tool()
async def get_stock_price(symbol: str) -> str:
    """Get latest stock price for a symbol like AAPL, TSLA."""
    API_KEY = "3K9JJIROLT1OYZTC"
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"

    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()

    return str(data["Global Quote"])


if __name__ == "__main__":
    mcp.run()