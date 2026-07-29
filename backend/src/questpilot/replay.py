from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from questpilot.agent_runtime import AgentRuntime
from questpilot.harness.context import ExecutionContext
from questpilot.harness.gateway import FakeModel, ModelResponse
from questpilot.harness.tools import ToolRegistry
from questpilot.models import AgentCheckpoint, AgentRun, PromptRecord


class PromptRegistry:
    def __init__(self, session: Session) -> None:
        self.session = session

    def register(self, prompt_id: str, version: str, node_name: str, content: str) -> PromptRecord:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        existing = self.session.scalar(
            select(PromptRecord).where(
                PromptRecord.prompt_id == prompt_id,
                PromptRecord.version == version,
            )
        )
        if existing:
            if existing.content_sha256 != digest:
                raise ValueError("a released prompt version is immutable")
            return existing
        record = PromptRecord(
            prompt_id=prompt_id,
            version=version,
            node_name=node_name,
            content=content,
            content_sha256=digest,
        )
        self.session.add(record)
        self.session.commit()
        return record

    def get(self, prompt_id: str, version: str | None = None) -> PromptRecord:
        statement = select(PromptRecord).where(PromptRecord.prompt_id == prompt_id)
        if version:
            statement = statement.where(PromptRecord.version == version)
        else:
            statement = statement.where(PromptRecord.active.is_(True)).order_by(
                PromptRecord.id.desc()
            )
        record = self.session.scalar(statement)
        if not record:
            raise KeyError(f"unknown prompt: {prompt_id}@{version or 'active'}")
        return record


@dataclass(frozen=True)
class DriftReport:
    input_drift: bool
    model_drift: bool
    prompt_drift: bool
    data_drift: bool
    details: dict[str, Any]


class ReplayService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def bundle(self, run_id: str) -> dict[str, Any]:
        run = self.session.get(AgentRun, run_id)
        if not run:
            raise KeyError(f"unknown run: {run_id}")
        checkpoints = list(
            self.session.scalars(
                select(AgentCheckpoint)
                .where(AgentCheckpoint.run_id == run_id)
                .order_by(AgentCheckpoint.created_at)
            )
        )
        return {
            "run_id": run.id,
            "input": run.input_json,
            "output": run.output_json,
            "model": run.model_name,
            "prompt": {"id": run.prompt_id, "version": run.prompt_version},
            "checkpoints": [
                {
                    "node": item.node_name,
                    "version": item.version,
                    "state": item.state_json,
                }
                for item in checkpoints
            ],
        }

    def compare(self, original: dict[str, Any], replayed: dict[str, Any]) -> DriftReport:
        original_data = self._data_versions(original)
        replayed_data = self._data_versions(replayed)
        return DriftReport(
            input_drift=original.get("input") != replayed.get("input"),
            model_drift=original.get("model") != replayed.get("model"),
            prompt_drift=original.get("prompt") != replayed.get("prompt"),
            data_drift=original_data != replayed_data,
            details={"original_data": original_data, "replayed_data": replayed_data},
        )

    @staticmethod
    def _data_versions(bundle: dict[str, Any]) -> list[str]:
        versions: list[str] = []
        for checkpoint in bundle.get("checkpoints") or []:
            state = checkpoint.get("state") or {}
            result = state.get("result") or {}
            if result.get("dataset_version"):
                versions.append(str(result["dataset_version"]))
        return sorted(set(versions))

    async def replay_fake(
        self,
        run_id: str,
        responses: list[ModelResponse | dict[str, Any]],
        registry: ToolRegistry,
    ):
        bundle = self.bundle(run_id)
        recorded = (bundle.get("output") or {}).get("tool_results") or []
        replay_registry = RecordedToolRegistry(registry, recorded)
        context = ExecutionContext(
            user_id=(bundle.get("input") or {}).get("user_id", "demo"),
            metadata={"replay_of": run_id},
        )
        runtime = AgentRuntime(FakeModel(responses), replay_registry)
        return await runtime.run(str((bundle.get("input") or {}).get("query") or ""), context)


class RecordedToolRegistry:
    """Validate and replay historical tool outputs without touching current data."""

    def __init__(self, base: ToolRegistry, recorded: list[dict[str, Any]]) -> None:
        self.base = base
        self.recorded = list(recorded)

    def model_schemas(self) -> list[dict[str, Any]]:
        return self.base.model_schemas()

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
        *,
        version: str | None = None,
    ):
        match_index = next(
            (
                index
                for index, item in enumerate(self.recorded)
                if item.get("name") == name
            ),
            None,
        )
        if match_index is None:
            raise KeyError(f"recorded replay is missing tool output: {name}")
        item = self.recorded.pop(match_index)
        spec = self.base.get(name, version).spec
        spec.input_model.model_validate(arguments)
        result = spec.output_model.model_validate(item["result"])
        context.emit(
            "tool.replayed",
            name,
            "completed",
            payload_summary={"recorded": True},
            finished=True,
        )
        return result
