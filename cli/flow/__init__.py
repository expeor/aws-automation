# cli/flow/__init__.py
"""
CLI Flow Module - 통합 CLI Flow

이 모듈은 AA CLI의 전체 실행 흐름을 관리합니다.
questionary 기반 대화형 UI를 포함하므로 CLI 전용입니다.

구조:
    context.py      - ExecutionContext, 상태 관리 데이터 클래스
    runner.py       - FlowRunner, 전체 흐름 관리
    steps/          - 개별 Step 구현
        category.py - 카테고리/도구 선택
        profile.py  - 프로파일 선택 + Provider 생성
        role.py     - SSO Role 선택
        region.py   - 리전 선택

사용법:
    from cli.flow import FlowRunner, create_flow_runner
    
    # 방법 1: 전체 메뉴부터 시작
    runner = create_flow_runner()
    runner.run()
    
    # 방법 2: 특정 카테고리부터 시작
    runner = create_flow_runner()
    runner.run("ebs")  # EBS 카테고리 도구 선택부터

CLI 통합:
    # cli/commands/{cat}_cmd.py
    from cli.flow import create_flow_runner
    
    @click.command()
    def ebs():
        runner = create_flow_runner()
        runner.run("ebs")

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
    실제 사용 시점에만 하위 모듈이 로드되어 CLI 시작 시간을 최적화합니다.
"""

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
