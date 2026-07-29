from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from questpilot.asset_cache import cache_manifest_assets
from questpilot.config import get_settings
from questpilot.data_pipeline import AtlasClient, AtlasPipeline, SnapshotStore
from questpilot.database import SessionLocal, create_all
from questpilot.drop_rates import DropDatasetPublisher, load_manifest
from questpilot.evaluation import EvaluationRunner, default_material_gap_unit_cases
from questpilot.seed import seed_demo


def seed() -> None:
    create_all()
    with SessionLocal() as session:
        print(json.dumps(seed_demo(session), ensure_ascii=False, indent=2))


def atlas() -> None:
    parser = argparse.ArgumentParser(description="Sync selected Atlas CN servants")
    parser.add_argument("--collection-no", type=int, nargs="+")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--wars-only", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    create_all()
    with SessionLocal() as session:
        pipeline = AtlasPipeline(
            session,
            AtlasClient(settings.atlas_base_url),
            SnapshotStore(settings.data_dir),
        )
        selected_modes = int(args.full) + int(args.wars_only) + int(bool(args.collection_no))
        if selected_modes != 1:
            parser.error("provide exactly one of --collection-no, --full, or --wars-only")
        if args.full:
            result = pipeline.sync_full()
        elif args.wars_only:
            result = pipeline.sync_wars()
        else:
            result = pipeline.sync_demo(args.collection_no)
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
    raw = json.loads(content)
    if str(raw.get("domusVer")) != str(manifest["domus_version"]):
        raise ValueError("community dataset domusVer does not match the manifest")
    create_all()
    with SessionLocal() as session:
        dataset = DropDatasetPublisher(session).publish(
            content,
            source_url=manifest["source_url"],
            upstream_commit=manifest["upstream_commit"],
            allowed_quest_ids=set(manifest.get("allowed_quest_ids") or []),
            allowed_item_ids={
                int(item["game_id"]) for item in manifest.get("selected_materials") or []
            },
            minimum_sample_runs=int(manifest.get("minimum_sample_runs") or 1),
            license_status=manifest["license_status"],
            enforce_demo_scope=True,
        )
        print(json.dumps({"version": dataset.version, "id": dataset.id}, ensure_ascii=False))


def evaluate() -> None:
    parser = argparse.ArgumentParser(description="Run the material-gap unit evaluation suite")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = EvaluationRunner().run(
        default_material_gap_unit_cases(),
        lambda value: {"gap": max(value["required"] - value["owned"], 0)},
    )
    report["suite_name"] = "材料缺口单元评测"
    report["suite_version"] = "material-gap-unit-v1"
    report["generated_at"] = datetime.now(UTC).isoformat()
    output = args.output or (
        Path("../reports/generated")
        / f"material-gap-unit-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "pass_rate": report["pass_rate"]}, ensure_ascii=False))


def assets() -> None:
    parser = argparse.ArgumentParser(description="Cache licensed local demo assets")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/asset-manifest.json"),
    )
    args = parser.parse_args()
    settings = get_settings()
    result = cache_manifest_assets(args.manifest, settings.data_dir / "assets")
    print(json.dumps(result, ensure_ascii=False, indent=2))
