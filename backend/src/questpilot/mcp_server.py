from __future__ import annotations

from questpilot.database import SessionLocal, create_all
from questpilot.domain_tools import build_tool_registry
from questpilot.harness.context import ExecutionContext
from questpilot.repositories import GameRepository
from questpilot.services import GameService


def build_server():
    from mcp.server import MCPServer

    server = MCPServer("QuestPilot")

    @server.tool()
    async def search_character(query: str, limit: int = 10) -> dict:
        """Search a character through QuestPilot's registered ToolSpec."""
        with SessionLocal() as session:
            registry = build_tool_registry(GameService(GameRepository(session)))
            result = await registry.execute(
                "search_character",
                {"query": query, "limit": limit},
                ExecutionContext(),
            )
            return result.model_dump(mode="json")

    @server.tool()
    async def calculate_material_gap(user_id: str, goals: list[dict]) -> dict:
        """Calculate deterministic material gaps through the shared registry."""
        with SessionLocal() as session:
            registry = build_tool_registry(GameService(GameRepository(session)))
            result = await registry.execute(
                "calculate_material_gap",
                {"user_id": user_id, "goals": goals},
                ExecutionContext(user_id=user_id),
            )
            return result.model_dump(mode="json")

    return server


def main() -> None:
    create_all()
    build_server().run()
