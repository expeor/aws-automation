"""
core/parallel/client.py - boto3 client/resource 생성 헬퍼

Retry(adaptive 모드) + 타임아웃 + 연결 풀이 설정된
boto3 client/resource를 생성합니다.

주요 구성 요소:
- get_client: retry 설정이 적용된 boto3 client 생성
- get_resource: retry 설정이 적용된 boto3 resource 생성

Example:
    from core.parallel.client import get_client

    # 기본 설정 (adaptive retry, max 5회)
    ec2 = get_client(session, "ec2", region_name="ap-northeast-2")

    # 커스텀 설정
    ec2 = get_client(session, "ec2", max_attempts=10, connect_timeout=10)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

if TYPE_CHECKING:
    import boto3

# Retry mode 타입 (botocore TypedDict와 호환)
RetryMode = Literal["legacy", "standard", "adaptive"]

# 기본 retry 설정
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_RETRY_MODE: RetryMode = "adaptive"  # adaptive: 동적 조정, standard: 고정
DEFAULT_CONNECT_TIMEOUT = 10  # 초
DEFAULT_READ_TIMEOUT = 30  # 초
DEFAULT_MAX_POOL_CONNECTIONS = 25  # max_workers(20) 이상 권장


def get_client(
    session: boto3.Session,
    service_name: str,
    region_name: str | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    retry_mode: RetryMode = DEFAULT_RETRY_MODE,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
    read_timeout: int = DEFAULT_READ_TIMEOUT,
    max_pool_connections: int = DEFAULT_MAX_POOL_CONNECTIONS,
    **kwargs: Any,
) -> Any:
    """Retry가 적용된 boto3 client 생성

    Args:
        session: boto3 Session
        service_name: AWS 서비스 이름 (ec2, s3, iam 등)
        region_name: 리전 (None이면 세션 기본값)
        max_attempts: 최대 시도 횟수 (기본: 5)
        retry_mode: 재시도 모드 ('adaptive' 또는 'standard')
        connect_timeout: 연결 타임아웃 (초)
        read_timeout: 읽기 타임아웃 (초)
        max_pool_connections: HTTP 연결 풀 크기 (기본: 25, max_workers 이상 권장)
        **kwargs: session.client()에 전달할 추가 인자

    Returns:
        boto3 client

    Example:
        from core.parallel.client import get_client

        ec2 = get_client(session, "ec2", region_name="ap-northeast-2")
        volumes = ec2.describe_volumes()["Volumes"]
    """
    from botocore.config import Config

    config = Config(
        retries={"max_attempts": max_attempts, "mode": retry_mode},  # pyright: ignore[reportArgumentType]
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        max_pool_connections=max_pool_connections,
    )

    # 기존 config가 있으면 병합
    if "config" in kwargs:
        existing = kwargs.pop("config")
        config = config.merge(existing)

    # session.client은 문자열 서비스명을 받지만 boto3-stubs는 Literal 타입 요구
    # cast to Any to bypass boto3-stubs Literal type requirements
    return session.client(  # pyright: ignore[reportCallIssue]
        cast(Any, service_name),
        region_name=region_name,
        config=config,
        **kwargs,
    )


def get_resource(
    session: boto3.Session,
    service_name: str,
    region_name: str | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    retry_mode: RetryMode = DEFAULT_RETRY_MODE,
    max_pool_connections: int = DEFAULT_MAX_POOL_CONNECTIONS,
    **kwargs: Any,
) -> Any:
    """Retry가 적용된 boto3 resource 생성

    Args:
        session: boto3 Session
        service_name: AWS 서비스 이름
        region_name: 리전 (None이면 세션 기본값)
        max_attempts: 최대 시도 횟수
        retry_mode: 재시도 모드
        max_pool_connections: HTTP 연결 풀 크기 (기본: 25, max_workers 이상 권장)
        **kwargs: session.resource()에 전달할 추가 인자

    Returns:
        boto3 resource
    """
    from botocore.config import Config

    config = Config(
        retries={"max_attempts": max_attempts, "mode": retry_mode},  # pyright: ignore[reportArgumentType]
        max_pool_connections=max_pool_connections,
    )

    if "config" in kwargs:
        existing = kwargs.pop("config")
        config = config.merge(existing)

    # session.resource은 문자열 서비스명을 받지만 boto3-stubs는 Literal 타입 요구
    # cast to Any to bypass boto3-stubs Literal type requirements
    return session.resource(  # pyright: ignore[reportCallIssue]
        cast(Any, service_name),
        region_name=region_name,
        config=config,
        **kwargs,
    )
