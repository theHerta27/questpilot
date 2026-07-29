from __future__ import annotations

import os

import pytest

from questpilot.data_pipeline import AtlasClient


@pytest.mark.online
@pytest.mark.skipif(
    os.getenv("ATLAS_ONLINE_TEST") != "1",
    reason="set ATLAS_ONLINE_TEST=1 to run live Atlas CN contracts",
)
def test_atlas_cn_live_contracts():
    client = AtlasClient()
    info = client.info()
    assert {"hash", "serverHash", "dataVer"}.issubset(info)
    servant = client.fetch("/basic/CN/servant/search?name=阿尔托莉雅").content
    assert b"collectionNo" in servant
    item = client.fetch("/nice/CN/item/search?name=英雄之证").content
    assert b'"id"' in item
