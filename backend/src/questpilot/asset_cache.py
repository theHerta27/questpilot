from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import httpx


def cache_manifest_assets(
    manifest_path: Path,
    cache_root: Path,
    *,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("permission_status") != "user-confirmed-local-demo-portfolio":
        raise ValueError("asset manifest permission_status is not approved")
    assets = manifest.get("assets") or []
    if not assets:
        raise ValueError("asset manifest must contain at least one asset")

    owned_client = client is None
    http = client or httpx.Client(timeout=30, follow_redirects=True)
    cached: list[str] = []
    failed: list[dict[str, str]] = []
    try:
        for asset in assets:
            relative = Path(str(asset["local_path"]))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"unsafe asset path: {relative}")
            target = cache_root / relative
            try:
                response = http.get(str(asset["source_url"]))
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    raise ValueError(f"unexpected content type: {content_type}")
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(f"{target.suffix}.part")
                temporary.write_bytes(response.content)
                temporary.replace(target)
                cached.append(str(relative).replace("\\", "/"))
            except (httpx.HTTPError, OSError, ValueError) as exc:
                failed.append({"asset": str(asset.get("name") or relative), "error": str(exc)})
    finally:
        if owned_client:
            http.close()
    return {"requested": len(assets), "cached": cached, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Cache licensed local demo assets")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/asset-manifest.json"),
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path("data/assets"),
    )
    args = parser.parse_args()
    print(
        json.dumps(
            cache_manifest_assets(args.manifest, args.cache_root),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
