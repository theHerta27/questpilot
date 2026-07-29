from __future__ import annotations

import pytest

from questpilot.infrastructure import LocalObjectStore, MemoryJsonCache


def test_memory_cache_and_local_object_store(tmp_path):
    cache = MemoryJsonCache()
    cache.set("plan", {"verified": True})
    assert cache.get("plan") == {"verified": True}
    store = LocalObjectStore(tmp_path)
    store.put("snapshots/test.json", b"{}", "application/json")
    assert store.get("snapshots/test.json") == b"{}"
    with pytest.raises(ValueError):
        store.put("../outside", b"x")
