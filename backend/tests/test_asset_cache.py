from __future__ import annotations

import json

import httpx

from questpilot.asset_cache import cache_manifest_assets


def test_asset_cache_is_local_and_failure_tolerant(tmp_path):
    manifest = tmp_path / "assets.json"
    manifest.write_text(
        json.dumps(
            {
                "permission_status": "user-confirmed-local-demo-portfolio",
                "assets": [
                    {
                        "name": "可用图片",
                        "source_url": "https://assets.test/ok.png",
                        "local_path": "characters/1.png",
                    },
                    {
                        "name": "缺失图片",
                        "source_url": "https://assets.test/missing.png",
                        "local_path": "materials/2.png",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ok.png":
            return httpx.Response(200, content=b"png", headers={"content-type": "image/png"})
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = cache_manifest_assets(manifest, tmp_path / "cache", client=client)

    assert result["requested"] == 2
    assert result["cached"] == ["characters/1.png"]
    assert len(result["failed"]) == 1
    assert (tmp_path / "cache/characters/1.png").read_bytes() == b"png"
