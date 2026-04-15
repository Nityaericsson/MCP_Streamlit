import asyncio
import os
from dotenv import load_dotenv
import sys
from mcp_client import MCPClient
from google import genai   # ✅ NEW SDK
import json, re, httpx, os

load_dotenv()

async def resolve_symbol(company: str, api_key: str):
    url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={company}&apikey={api_key}"

    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()

    if "bestMatches" in data and len(data["bestMatches"]) > 0:
        return data["bestMatches"][0]["1. symbol"]

    return None

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
        async with MCPClient(sys.executable, ["mcp_server1.py"]) as places_client, \
           MCPClient(sys.executable, ["mcp_server2.py"]) as weather_client:

            try:
                # -------------------------
                # Step 1: Decide tool
                # -------------------------

# -------- STEP 1: Extract structured data --------
                extraction_prompt = f"""
                Analyze this query:

                "{user_input}"

                Classify intent STRICTLY:

                - WEATHER → asking about weather
                - STOCK → asking about stocks
                - TRAVEL → asking where to go / vacation / suggestions
                - GENERAL → everything else
                - suggested_city: city mentioned by user if any

                For TRAVEL:
                - ALWAYS assign a travel_type
                - NEVER return null
                - Choose the closest match:
                - hill → for cool, pleasant, mountains
                - beach → for hot, sunny, sea
                - city → for urban travel
                - general → if nothing fits

                Return STRICT JSON:
                {{
                "intent": "...",
                "location": "...",
                "company_name": "...",
                "stock_symbol": "...",
                "travel_type": "..."
                "suggested_city": "..."
                }}
                """

                res = self.client.models.generate_content(
                    model=self.model,
                    contents=extraction_prompt
                )

                # -------- SAFE JSON PARSE --------
                json_text = re.search(r"\{.*\}", res.text, re.DOTALL).group()
                data = json.loads(json_text)

                print("🧠 Parsed:", data)

                # -------- HELPER: resolve symbol --------
                async def resolve_symbol(company: str):
                    url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={company}&apikey={os.getenv('ALPHA_VANTAGE_KEY')}"
                    
                    async with httpx.AsyncClient() as client:
                        res = await client.get(url)
                        d = res.json()

                    if "bestMatches" in d and len(d["bestMatches"]) > 0:
                        return d["bestMatches"][0]["1. symbol"]

                    return None


                # ================================
                # WEATHER
                # ================================
                if data["intent"] == "WEATHER":
                    location = data.get("location")

                    if not location:
                        return "❌ Please provide a valid city name."

                    result = await weather_client.call_tool(
                        "get_weather",
                        {"city": location},
                    )

                    tool_data = result.content[0].text

                    final_res = self.client.models.generate_content(
                        model=self.model,
                        contents=f"""
                        User question: {user_input}

                        Location: {location}

                        Weather data:
                        {tool_data}

                        Give a helpful, natural answer.
                        """
                    )

                    return final_res.text


                # ================================
                # STOCK
                # ================================
                elif data["intent"] == "STOCK":

                    company = data.get("company_name")
                    llm_symbol = data.get("stock_symbol")

                    symbol = await resolve_symbol(company)

                    if not symbol:
                        print("⚠️ API failed, using LLM fallback")
                        symbol = llm_symbol

                    if not symbol:
                        return "❌ Could not find stock symbol."

                    result = await weather_client.call_tool(
                        "get_stock_price",
                        {"symbol": symbol},
                    )

                    tool_data = result.content[0].text

                    final_res = self.client.models.generate_content(
                        model=self.model,
                        contents=f"""
                        User question: {user_input}

                        Company: {company}
                        Symbol: {symbol}

                        Stock data:
                        {tool_data}

                        Explain clearly in simple terms.
                        """
                    )

                    return final_res.text
                
                # ================================
                # travel
                # ================================

                elif data["intent"] == "TRAVEL":
                    travel_type = data.get("travel_type", "general")
                    suggested_city = data.get("suggested_city")

                    # -------------------------------
                    # CASE 1: User gave a city
                    # -------------------------------
                    if suggested_city:

                        # Step 1 → get weather
                        res = await weather_client.call_tool(
                            "get_weather",
                            {"city": suggested_city}
                        )

                        try:
                            weather = json.loads(res.content[0].text)
                        except:
                            return "❌ Could not fetch weather."

                        # Step 2 → ask LLM to evaluate
                        decision_prompt = f"""
                        You are a travel expert.

                        User wants to visit: {suggested_city}

                        Current weather:
                        {json.dumps(weather, indent=2)}

                        Decide:
                        - Is it a good time to visit?
                        - If yes → explain why
                        - If no → suggest 2–3 better similar places

                        Return natural response (not JSON).
                        """

                        final = self.client.models.generate_content(
                            model=self.model,
                            contents=decision_prompt
                        )

                        return final.text

                    # -------------------------------
                    # CASE 2: No city → normal flow
                    # -------------------------------

                    places_result = await places_client.call_tool(
                        "suggest_places",
                        {"preference": travel_type}
                    )

                    places_data = json.loads(places_result.content[0].text)
                    cities = places_data.get("places", [])

                    weather_data = []

                    for city in cities:
                        res = await weather_client.call_tool(
                            "get_weather",
                            {"city": city}
                        )

                        try:
                            weather = json.loads(res.content[0].text)
                        except:
                            continue

                        weather_data.append({
                            "city": city,
                            "weather": weather
                        })

                    decision_prompt = f"""
                    You are a travel expert.

                    User query:
                    {user_input}

                    Data:
                    {json.dumps(weather_data, indent=2)}

                    Choose BEST city for vacation.

                    Return JSON:
                    {{
                    "best_city": "...",
                    "reason": "..."
                    }}
                    """

                    final = self.client.models.generate_content(
                        model=self.model,
                        contents=decision_prompt
                    )

                    return final.text
                # ================================
                # GENERAL
                # ================================

                else:
                    res = self.client.models.generate_content(
                        model=self.model,
                        contents=user_input
                    )

                    return res.text or "No response generated."
            except Exception as e:
                return f"❌ Error: {str(e)}"
