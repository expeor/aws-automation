# internal/tools - AWS 분석/작업 도구
"""
AWS 분석/작업 도구 플러그인 시스템

Note:
    Lazy Import 패턴 사용 - CLI 시작 시간 최적화
"""

__all__ = [
    "BaseToolRunner",
    # Types
    "ToolArea",
    "AREA_DISPLAY",
    "get_area_display",
    "format_area_badge",
    # Discovery
    "discover_categories",
    "get_category",
    "load_tool",
    "list_tools_by_area",
    "get_area_summary",
]

# Lazy import 매핑 테이블
_IMPORT_MAPPING = {
    # base.py
    "BaseToolRunner": (".base", "BaseToolRunner"),
    # types.py
    "ToolArea": (".types", "ToolArea"),
    "AREA_DISPLAY": (".types", "AREA_DISPLAY"),
    "get_area_display": (".types", "get_area_display"),
    "format_area_badge": (".types", "format_area_badge"),
    # discovery.py
    "discover_categories": (".discovery", "discover_categories"),
    "get_category": (".discovery", "get_category"),
    "load_tool": (".discovery", "load_tool"),
    "list_tools_by_area": (".discovery", "list_tools_by_area"),
    "get_area_summary": (".discovery", "get_area_summary"),
}


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드"""
    if name in _IMPORT_MAPPING:
        import importlib

        module_name, attr_name = _IMPORT_MAPPING[name]
        module = importlib.import_module(module_name, __name__)
        return getattr(module, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
