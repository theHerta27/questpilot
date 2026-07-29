from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GenericMaterial:
    external_id: int
    name: str


@dataclass(frozen=True)
class GenericCharacter:
    external_id: int
    name: str
    class_name: str


class MockRpgAdapter:
    """A deliberately fictional source proving the domain core is not FGO-bound."""

    source = "mock-rpg"

    def characters(self) -> list[GenericCharacter]:
        return [
            GenericCharacter(1001, "星穹领航员", "Navigator"),
            GenericCharacter(1002, "赤砂守望者", "Warden"),
        ]

    def materials(self) -> list[GenericMaterial]:
        return [
            GenericMaterial(9001, "星屑齿轮"),
            GenericMaterial(9002, "赤砂结晶"),
        ]
