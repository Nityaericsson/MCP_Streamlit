import sys
import asyncio
from typing import Optional, Any
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import json


class MCPClient:
    def __init__(self, command: str, args: list[str], env: Optional[dict] = None):
        self._command = command
        self._args = args
        self._env = env
        self._session: Optional[ClientSession] = None
        self._exit_stack: AsyncExitStack = AsyncExitStack()

    async def connect(self):
        server_params = StdioServerParameters(
            command=self._command,
            args=self._args,
            env=self._env,
        )

        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        read_stream, write_stream = stdio_transport

        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        await self._session.initialize()

    def session(self) -> ClientSession:
        if self._session is None:
            raise ConnectionError("Session not initialized")
        return self._session

    # ✅ YOUR FUNCTIONS (completed)

    async def list_tools(self) -> list[types.Tool]:
        result = await self.session().list_tools()
        return result.tools

    async def call_tool(
        self, tool_name: str, tool_input: dict
    ) -> types.CallToolResult | None:
        result = await self.session().call_tool(tool_name, tool_input)
        return result

    async def list_prompts(self) -> list[types.Prompt]:
        result = await self.session().list_prompts()
        return result.prompts

    async def get_prompt(self, prompt_name, args: dict[str, str]):
        result = await self.session().get_prompt(prompt_name, args)
        return result

    async def read_resource(self, uri: str) -> Any:
        result = await self.session().read_resource(uri)
        return result

    async def cleanup(self):
        await self._exit_stack.aclose()
        self._session = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    
# For testing
async def main():
    async with MCPClient(command="python", args=["mcp_server1.py"]) as places_client, \
               MCPClient(command="python", args=["mcp_server2.py"]) as weather_client:

        travel_type = "hill"

        # Step 1 → MCP1
        places_result = await places_client.call_tool(
            "suggest_places",
            {"preference": travel_type}
        )

        places_data = json.loads(places_result.content[0].text)
        cities = places_data.get("places", [])

        weather_data = []

        # Step 2 → MCP2
        for city in cities:
            res = await weather_client.call_tool(
                "get_weather",
                {"city": city}
            )

            weather = json.loads(res.content[0].text)

            weather_data.append({
                "city": city,
                "weather": weather
            })

        return str(weather_data)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())