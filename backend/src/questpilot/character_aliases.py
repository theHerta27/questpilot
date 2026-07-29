"""Small, reviewed alias set for M1 natural-language resolution.

Atlas remains the source of canonical CN names. These aliases are local search
metadata and are intentionally explicit rather than model-generated.
"""

CURATED_CHARACTER_ALIASES: dict[int, tuple[str, ...]] = {
    2: ("蓝呆", "呆毛王", "剑阶阿尔托莉雅"),
    189: ("杀刑部", "宅姬"),
    254: ("杰森",),
    262: ("弓刑部", "水刑部"),
    324: ("莫莱", "雅克莫莱"),
}
