import asyncio
import os
from dotenv import load_dotenv

from mcp_client import MCPClient
from google import genai   # ✅ NEW SDK

load_dotenv()


class AIService:
    def __init__(self):
        self.command = "python"
        self.args = ["mcp_server.py"]

        # ✅ Gemini client (correct way)
        self.client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )

        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    async def process_query(self, user_input: str) -> str:
        async with MCPClient(command=self.command, args=self.args) as client:

            try:
                # -------------------------
                # Step 1: Decide tool
                # -------------------------
                decision_prompt = f"""
                User query: {user_input}

                Classify into ONE of:

                WEATHER → if question is about:
                - rain
                - temperature
                - umbrella
                - climate
                - forecast
                - hot/cold
                - today weather

                STOCK → if about stocks, price, market

                GENERAL → everything else

                Return ONLY:
                WEATHER <lat> <lon>
                OR
                STOCK <symbol>
                OR
                GENERAL
                """

                decision_res = self.client.models.generate_content(
                    model=self.model,
                    contents=decision_prompt
                )

                decision = (decision_res.text or "").strip().upper()

                # -------------------------
                # Step 2: Route
                print("🧠 Decision:", decision)

                print("🧠 Decision:", decision)

                if "WEATHER" in decision:
                    print("🔧 USING MCP TOOL: WEATHER")

                elif "STOCK" in decision:
                    print("🔧 USING MCP TOOL: STOCK")

                else:
                    print("🧠 USING GEMINI DIRECT")
                # -------------------------

                if "WEATHER" in decision:
                    lat, lon = 12.97, 77.59  # Bangalore

                    result = await client.call_tool(
                        "get_weather",
                        {"latitude": lat, "longitude": lon},
                    )

                    tool_data = result.content[0].text

                    final_res = self.client.models.generate_content(
                        model=self.model,
                        contents=f"""
                        User question: {user_input}

                        Weather data:
                        {tool_data}

                        Give a helpful, natural answer. Do NOT return JSON.
                        """
                    )

                    return final_res.text

                elif "STOCK" in decision:
                    parts = decision.split()
                    symbol = parts[1] if len(parts) > 1 else "AAPL"

                    result = await client.call_tool(
                        "get_stock_price",
                        {"symbol": symbol},
                    )

                    tool_data = result.content[0].text

                    final_res = self.client.models.generate_content(
                        model=self.model,
                        contents=f"""
                        User question: {user_input}

                        Stock data:
                        {tool_data}

                        Explain the stock situation clearly in simple terms.
                        Do NOT return raw JSON.
                        """
                    )

                    return final_res.text

                else:
                    res = self.client.models.generate_content(
                        model=self.model,
                        contents=user_input
                    )

                    return res.text or "No response generated."

            except Exception as e:
                return f"❌ Error: {str(e)}"