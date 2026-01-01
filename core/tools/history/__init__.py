"""
pkg/history - 사용 이력 관리

최근 사용, 즐겨찾기, 사용 통계 관리
"""

__all__ = [
    "RecentHistory",
    "RecentItem",
    "FavoritesManager",
    "FavoriteItem",
]

# Lazy imports
_IMPORT_MAPPING = {
    "RecentHistory": (".recent", "RecentHistory"),
    "RecentItem": (".recent", "RecentItem"),
    "FavoritesManager": (".favorites", "FavoritesManager"),
    "FavoriteItem": (".favorites", "FavoriteItem"),
}


def __getattr__(name: str):
    """Lazy import"""
    if name in _IMPORT_MAPPING:
        module_name, attr_name = _IMPORT_MAPPING[name]
        import importlib

        module = importlib.import_module(module_name, __name__)
        return getattr(module, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
