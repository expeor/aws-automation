# internal/tools/base.py
"""
BaseToolRunner - 모든 도구 Runner의 공통 베이스 클래스

각 서비스의 runner.py는 이 클래스를 상속받아 구현합니다.
internal/flow/runner.py에서 동적으로 로드하여 실행합니다.

Usage:
    # internal/tools/{service}/runner.py
    from core.tools.base import BaseToolRunner
    
    class ToolRunner(BaseToolRunner):
        def get_tools(self) -> dict:
            return {
                "도구이름": self._run_some_tool,
            }
        
        def _run_some_tool(self) -> None:
            ...
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from rich.console import Console

    from cli.flow.context import ExecutionContext


def _get_console() -> "Console":
    """Lazy console 인스턴스 반환"""
    from rich.console import Console

    return Console()


@dataclass
class BaseToolRunner(ABC):
    """도구 Runner 베이스 클래스

    모든 서비스의 ToolRunner는 이 클래스를 상속받아야 합니다.

    Attributes:
        ctx: 실행 컨텍스트 (프로파일, 리전, 계정 정보 등)

    Example:
        class ToolRunner(BaseToolRunner):
            def get_tools(self) -> dict:
                return {"미사용 볼륨": self._run_unused}

            def _run_unused(self) -> None:
                for region in self.regions:
                    session = self.get_session(region)
                    # ... 작업 수행
    """

    ctx: Optional["ExecutionContext"] = None

    # 하위 호환성을 위한 필드 (deprecated)
    profiles: List[str] = field(default_factory=list)
    regions: List[str] = field(default_factory=list)

    # SSO 전용 필드 (Optional)
    start_url: Optional[str] = None
    session_name: Optional[str] = None

    def __post_init__(self):
        """ctx에서 값 추출하여 하위 호환 필드 설정"""
        if self.ctx:
            # regions 설정
            if not self.regions and self.ctx.regions:
                self.regions = self.ctx.regions

            # profiles 설정
            if not self.profiles and self.ctx.profile_name:
                self.profiles = [self.ctx.profile_name]

            # SSO 정보 설정
            if self.ctx.provider:
                self.start_url = getattr(self.ctx.provider, "start_url", None)
                self.session_name = self.ctx.profile_name

    @abstractmethod
    def get_tools(self) -> Dict[str, Callable[[], Any]]:
        """도구 이름 → 실행 함수 매핑 반환

        Returns:
            {"도구이름": self._run_method, ...}
        """
        pass

    def run_tool(self, tool_name: str) -> Any:
        """도구 이름으로 실행

        Args:
            tool_name: menu.py의 도구 이름과 일치하는 키

        Returns:
            도구 실행 결과 (Optional)
        """
        tools = self.get_tools()

        if tool_name not in tools:
            _get_console().print(
                f"[yellow]⚠️ '{tool_name}' 기능은 아직 구현되지 않았습니다.[/yellow]"
            )
            return None

        return tools[tool_name]()

    def get_session(self, region: str, account_id: Optional[str] = None):
        """boto3 세션 획득

        Args:
            region: AWS 리전
            account_id: 계정 ID (멀티 계정 시)

        Returns:
            boto3.Session 인스턴스
        """
        import boto3

        # ctx가 있으면 ctx.provider를 통해 세션 획득
        if self.ctx and self.ctx.provider:
            try:
                if account_id and self.ctx.role_selection:
                    # 멀티 계정: role 기반 세션
                    role_name = self.ctx.role_selection.primary_role
                    return self.ctx.provider.get_session(
                        account_id=account_id,
                        role_name=role_name,
                        region=region,
                    )
                else:
                    # 단일 계정
                    return self.ctx.provider.get_session(region=region)
            except Exception as e:
                _get_console().print(f"[yellow]⚠️ 인증 오류, 기본 세션 사용: {e}[/yellow]")

        # Fallback: 프로파일 기반 세션
        profile = self.profiles[0] if self.profiles else None
        return boto3.Session(profile_name=profile, region_name=region)

    def iterate_regions(self):
        """리전 순회 제너레이터

        Yields:
            (region, session) 튜플
        """
        for region in self.regions:
            session = self.get_session(region)
            yield region, session

    def iterate_accounts_and_regions(self):
        """계정 + 리전 순회 제너레이터 (멀티 계정용)

        Yields:
            (account_id, region, session) 튜플
        """
        if not self.ctx or not self.ctx.is_multi_account():
            # 단일 계정 모드
            for region in self.regions:
                session = self.get_session(region)
                yield None, region, session
        else:
            # 멀티 계정 모드
            for account in self.ctx.get_target_accounts():
                for region in self.regions:
                    session = self.get_session(region, account.id)
                    yield account.id, region, session
