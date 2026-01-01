# internal/flow/steps/__init__.py
"""Flow Steps 모듈

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
"""

__all__ = [
    "CategoryStep",
    "ProfileStep",
    "AccountStep",
    "RoleStep",
    "RegionStep",
]

_IMPORT_MAPPING = {
    "CategoryStep": (".category", "CategoryStep"),
    "ProfileStep": (".profile", "ProfileStep"),
    "AccountStep": (".account", "AccountStep"),
    "RoleStep": (".role", "RoleStep"),
    "RegionStep": (".region", "RegionStep"),
}


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드"""
    if name in _IMPORT_MAPPING:
        module_name, attr_name = _IMPORT_MAPPING[name]
        import importlib

        module = importlib.import_module(module_name, __name__)
        return getattr(module, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
