from __future__ import annotations

from pathlib import Path


def test_agent_and_routes_do_not_bypass_gateway_or_registry():
    source_root = Path(__file__).parents[1] / "src" / "questpilot"
    agent_source = (source_root / "agent_runtime.py").read_text(encoding="utf-8")
    route_source = (source_root / "api" / "main.py").read_text(encoding="utf-8")
    assert "httpx." not in agent_source
    assert "httpx." not in route_source
    assert ".execute(" not in agent_source.replace("registry.execute(", "")
    assert "session.execute(" not in route_source
    assert "ModelGateway" in agent_source
    assert "ToolRegistry" in agent_source
