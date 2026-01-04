"""
core/parallel/client.py - boto3 client 생성 헬퍼

Retry + Rate Limiting이 적용된 boto3 client를 생성합니다.

Usage:
    from core.parallel.client import get_client

    # 기본 설정 (adaptive retry, max 5회)
    ec2 = get_client(session, "ec2", region_name="ap-northeast-2")

    # 커스텀 설정
    ec2 = get_client(session, "ec2", max_attempts=10, connect_timeout=10)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import boto3

# 기본 retry 설정
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_RETRY_MODE = "adaptive"  # adaptive: 동적 조정, standard: 고정
DEFAULT_CONNECT_TIMEOUT = 10  # 초
DEFAULT_READ_TIMEOUT = 30  # 초


def get_client(
    session: boto3.Session,
    service_name: str,
    region_name: str | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    retry_mode: str = DEFAULT_RETRY_MODE,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
    read_timeout: int = DEFAULT_READ_TIMEOUT,
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
        retries={
            "max_attempts": max_attempts,
            "mode": retry_mode,
        },
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )

    # 기존 config가 있으면 병합
    if "config" in kwargs:
        existing = kwargs.pop("config")
        config = config.merge(existing)

    return session.client(
        service_name,
        region_name=region_name,
        config=config,
        **kwargs,
    )


def get_resource(
    session: boto3.Session,
    service_name: str,
    region_name: str | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    retry_mode: str = DEFAULT_RETRY_MODE,
    **kwargs: Any,
) -> Any:
    """Retry가 적용된 boto3 resource 생성

    Args:
        session: boto3 Session
        service_name: AWS 서비스 이름
        region_name: 리전 (None이면 세션 기본값)
        max_attempts: 최대 시도 횟수
        retry_mode: 재시도 모드
        **kwargs: session.resource()에 전달할 추가 인자

    Returns:
        boto3 resource
    """
    from botocore.config import Config

    config = Config(
        retries={
            "max_attempts": max_attempts,
            "mode": retry_mode,
        }
    )

    if "config" in kwargs:
        existing = kwargs.pop("config")
        config = config.merge(existing)

    return session.resource(
        service_name,
        region_name=region_name,
        config=config,
        **kwargs,
    )
