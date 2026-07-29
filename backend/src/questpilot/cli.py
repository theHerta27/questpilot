from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from questpilot.config import get_settings
from questpilot.data_pipeline import AtlasClient, AtlasPipeline, SnapshotStore
from questpilot.database import SessionLocal, create_all
from questpilot.drop_rates import DropDatasetPublisher, load_manifest
from questpilot.evaluation import EvaluationRunner, default_gap_cases
from questpilot.seed import seed_demo


def seed() -> None:
    create_all()
    with SessionLocal() as session:
        print(json.dumps(seed_demo(session), ensure_ascii=False, indent=2))


def atlas() -> None:
    parser = argparse.ArgumentParser(description="Sync selected Atlas CN servants")
    parser.add_argument("--collection-no", type=int, nargs="+")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    create_all()
    with SessionLocal() as session:
        pipeline = AtlasPipeline(
            session,
            AtlasClient(settings.atlas_base_url),
            SnapshotStore(settings.data_dir),
        )
        if not args.full and not args.collection_no:
            parser.error("provide --collection-no or --full")
        result = pipeline.sync_full() if args.full else pipeline.sync_demo(args.collection_no)
        print(json.dumps(result, ensure_ascii=False, indent=2))


def drop_data() -> None:
    parser = argparse.ArgumentParser(description="Publish a pinned community drop dataset")
    parser.add_argument("data_file", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    content = args.data_file.read_bytes()
    import hashlib

    if hashlib.sha256(content).hexdigest() != manifest["content_sha256"]:
        raise ValueError("community dataset hash does not match the manifest")
    create_all()
    with SessionLocal() as session:
        dataset = DropDatasetPublisher(session).publish(
            content,
            source_url=manifest["source_url"],
            upstream_commit=manifest["upstream_commit"],
            allowed_quest_ids=set(manifest.get("allowed_quest_ids") or []),
            minimum_sample_runs=int(manifest.get("minimum_sample_runs") or 1),
        )
        print(json.dumps({"version": dataset.version, "id": dataset.id}, ensure_ascii=False))


def evaluate() -> None:
    parser = argparse.ArgumentParser(description="Run the versioned offline evaluation suite")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = EvaluationRunner().run(
        default_gap_cases(),
        lambda value: {"gap": max(value["required"] - value["owned"], 0)},
    )
    report["suite_version"] = "gap-v1"
    report["generated_at"] = datetime.now(UTC).isoformat()
    output = args.output or (
        Path("../reports/generated")
        / f"evaluation-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "pass_rate": report["pass_rate"]}, ensure_ascii=False))
