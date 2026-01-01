# cli/flow/__init__.py
"""
CLI Flow Module - 통합 CLI Flow
"""

from typing import TYPE_CHECKING

# Pylance/타입 체커용 정적 임포트
if TYPE_CHECKING:
    from .context import (
        BackToMenu,
        ExecutionContext,
        FallbackStrategy,
        FlowResult,
        ProviderKind,
        RoleSelection,
        ToolInfo,
    )
    from .runner import FlowRunner, create_flow_runner
    from .steps import CategoryStep, ProfileStep, RegionStep, RoleStep

__all__ = [
    # Core
    "FlowRunner",
    "create_flow_runner",
    "ExecutionContext",
    "FlowResult",
    # Types
    "ProviderKind",
    "FallbackStrategy",
    "RoleSelection",
    "ToolInfo",
    # Exceptions
    "BackToMenu",
    # Steps
    "CategoryStep",
    "ProfileStep",
    "RoleStep",
    "RegionStep",
]

# Lazy import 매핑 테이블
_IMPORT_MAPPING = {
    # Context
    "ExecutionContext": (".context", "ExecutionContext"),
    "FlowResult": (".context", "FlowResult"),
    "ProviderKind": (".context", "ProviderKind"),
    "FallbackStrategy": (".context", "FallbackStrategy"),
    "RoleSelection": (".context", "RoleSelection"),
    "ToolInfo": (".context", "ToolInfo"),
    "BackToMenu": (".context", "BackToMenu"),
    # Runner
    "FlowRunner": (".runner", "FlowRunner"),
    "create_flow_runner": (".runner", "create_flow_runner"),
    # Steps
    "CategoryStep": (".steps", "CategoryStep"),
    "ProfileStep": (".steps", "ProfileStep"),
    "RoleStep": (".steps", "RoleStep"),
    "RegionStep": (".steps", "RegionStep"),
}


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드"""
    if name in _IMPORT_MAPPING:
        module_name, attr_name = _IMPORT_MAPPING[name]
        import importlib

        module = importlib.import_module(module_name, __name__)
        return getattr(module, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
