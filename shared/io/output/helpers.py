"""출력 경로 헬퍼 함수

컨텍스트에서 식별자를 추출하고 출력 경로를 생성하는 공통 헬퍼.
60개+ 분석기 파일에서 반복되던 6줄 패턴을 1줄로 줄여줍니다.

Usage:
    from shared.io.output import get_context_identifier, create_output_path

    identifier = get_context_identifier(ctx)
    output_path = create_output_path(ctx, "ec2", "unused")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext

from .builder import OutputPath


def get_context_identifier(ctx: ExecutionContext) -> str:
    """ctx에서 프로파일명 추출

    .config/.credentials에 설정된 profile name을 반환합니다.
    SSO Session, SSO Profile, Static 모두 동일하게 프로파일명 사용.

    Args:
        ctx: 실행 컨텍스트

    Returns:
        프로파일명 문자열
    """
    if ctx.profile_name:
        return ctx.profile_name
    elif ctx.profiles:
        return ctx.profiles[0]
    else:
        return "default"


def create_output_path(ctx: ExecutionContext, service: str, tool: str) -> str:
    """ctx 기반 출력 경로 자동 생성

    identifier + service + tool + date 패턴의 출력 경로를 생성합니다.

    Args:
        ctx: 실행 컨텍스트
        service: 서비스명 (예: "ec2", "lambda", "vpc")
        tool: 도구명 (예: "unused", "audit", "inventory")

    Returns:
        출력 디렉토리 경로 문자열
    """
    identifier = get_context_identifier(ctx)
    return OutputPath(identifier).sub(service, tool).with_date().build()
