# core/auth/types/types.py
"""
core/auth/types/types.py - AWS 인증 모듈의 핵심 타입 정의

이 모듈은 인증 시스템 전체에서 사용되는 기본 타입들을 정의합니다.

포함 항목:
    - ProviderType: 인증 Provider 타입 열거형 (SSO_SESSION, SSO_PROFILE, STATIC_CREDENTIALS)
    - AccountInfo: AWS 계정 정보 데이터 클래스
    - Provider: 모든 인증 Provider가 구현해야 하는 추상 기본 클래스 (ABC)
    - 에러 클래스: AuthError, NotAuthenticatedError, AccountNotFoundError,
      TokenExpiredError, ConfigurationError, ProviderError
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import boto3


# =============================================================================
# Provider Type Enum
# =============================================================================


class ProviderType(Enum):
    """인증 Provider 타입을 나타내는 열거형

    - SSOSession: AWS SSO 세션 기반 인증 (권장)
    - SSOProfile: SSO 프로파일 기반 인증 (sso_session 참조 또는 Legacy)
    - StaticCredentials: 정적 액세스 키 인증

    Note:
        SSO_PROFILE은 두 가지 경우에 사용됩니다:
        1. sso_session을 참조하고 account_id/role_name이 고정된 프로파일
        2. Legacy SSO (sso_session 없이 sso_start_url 직접 설정) - Deprecated

        Legacy SSO 사용 시 sso-session 방식으로 마이그레이션을 권장합니다.
    """

    SSO_SESSION = "sso-session"
    SSO_PROFILE = "sso-profile"
    STATIC_CREDENTIALS = "static-credentials"

    def __str__(self) -> str:
        return self.value


# =============================================================================
# Account Info
# =============================================================================


@dataclass
class AccountInfo:
    """AWS 계정 정보를 나타내는 데이터 클래스

    Attributes:
        id: AWS 계정 ID (12자리)
        name: 계정 이름 (별칭)
        email: 계정 이메일 (옵션)
        roles: 사용 가능한 역할 목록
        default_role: 기본 역할 이름
        is_management: 관리 계정 여부
        tags: 추가 메타데이터
    """

    id: str
    name: str
    email: str | None = None
    roles: list[str] = field(default_factory=list)
    default_role: str | None = None
    is_management: bool = False
    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """데이터 유효성 검사

        계정 ID가 12자리 숫자가 아닌 경우 경고를 출력합니다.
        이름이 비어있으면 "account-{id}" 형식으로 자동 설정합니다.
        """
        if not self.id or len(self.id) != 12 or not self.id.isdigit():
            logger.warning("유효하지 않은 AWS 계정 ID: '%s' (12자리 숫자여야 함)", self.id)
        if not self.name:
            self.name = f"account-{self.id}"

    def get_role(self, preferred_role: str = "readonly") -> str | None:
        """선호하는 역할을 찾아 반환

        Args:
            preferred_role: 선호하는 역할 타입 (readonly, admin 등)

        Returns:
            매칭되는 역할 이름 또는 None
        """
        if not self.roles:
            return self.default_role

        for role in self.roles:
            if preferred_role.lower() in role.lower():
                return role

        return self.roles[0] if self.roles else self.default_role

    def __hash__(self):
        """계정 ID 기반 해시값 반환."""
        return hash(self.id)

    def __eq__(self, other):
        """계정 ID 기반 동등성 비교."""
        if isinstance(other, AccountInfo):
            return self.id == other.id
        return False


# =============================================================================
# Provider Interface (Abstract Base Class)
# =============================================================================


class Provider(ABC):
    """모든 인증 Provider가 구현해야 하는 추상 기본 클래스

    이 인터페이스를 통해 다양한 인증 방식을 통일된 API로 사용할 수 있습니다.

    Example:
        class MyProvider(Provider):
            def type(self) -> ProviderType:
                return ProviderType.STATIC_CREDENTIALS

            def name(self) -> str:
                return "my-provider"

            # ... 나머지 메서드 구현
    """

    @abstractmethod
    def type(self) -> ProviderType:
        """Provider 타입을 반환합니다."""
        pass

    @abstractmethod
    def name(self) -> str:
        """Provider 이름(식별자)을 반환합니다."""
        pass

    @abstractmethod
    def authenticate(self) -> None:
        """인증을 수행합니다.

        Raises:
            AuthError: 인증 실패 시
        """
        pass

    @abstractmethod
    def is_authenticated(self) -> bool:
        """인증 상태를 확인합니다.

        Returns:
            True if 인증됨, False otherwise
        """
        pass

    @abstractmethod
    def get_session(
        self,
        account_id: str | None = None,
        role_name: str | None = None,
        region: str | None = None,
    ) -> boto3.Session:
        """지정된 계정/역할/리전에 대한 boto3 Session을 반환합니다.

        Args:
            account_id: 대상 계정 ID (멀티 계정 Provider에서 사용)
            role_name: 사용할 역할 이름
            region: AWS 리전

        Returns:
            boto3.Session 객체

        Raises:
            NotAuthenticatedError: 인증되지 않은 경우
            AccountNotFoundError: 계정을 찾을 수 없는 경우
        """
        pass

    @abstractmethod
    def get_aws_config(
        self,
        account_id: str | None = None,
        role_name: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """지정된 계정/역할/리전에 대한 AWS Config를 반환합니다.

        boto3 Session의 _session.get_config()와 유사한 설정 객체를 반환합니다.

        Args:
            account_id: 대상 계정 ID
            role_name: 사용할 역할 이름
            region: AWS 리전

        Returns:
            AWS 설정 정보를 담은 dict
        """
        pass

    @abstractmethod
    def list_accounts(self) -> dict[str, AccountInfo]:
        """접근 가능한 계정 목록을 반환합니다.

        Returns:
            {account_id: AccountInfo} 딕셔너리
        """
        pass

    @abstractmethod
    def supports_multi_account(self) -> bool:
        """멀티 계정 지원 여부를 반환합니다.

        Returns:
            True if 멀티 계정 지원, False otherwise
        """
        pass

    @abstractmethod
    def get_default_region(self) -> str:
        """기본 리전을 반환합니다."""
        pass

    def refresh(self) -> None:  # noqa: B027
        """자격 증명을 갱신합니다.

        기본 구현은 아무것도 하지 않습니다.
        토큰 갱신이 필요한 Provider는 이 메서드를 오버라이드합니다.
        """
        pass

    def close(self) -> None:  # noqa: B027
        """리소스를 정리합니다.

        기본 구현은 아무것도 하지 않습니다.
        정리가 필요한 Provider는 이 메서드를 오버라이드합니다.
        """
        pass


# =============================================================================
# Error Classes
# =============================================================================


class AuthError(Exception):
    """인증 관련 기본 에러 클래스

    모든 인증 에러의 부모 클래스입니다.
    원인 예외(cause)를 체이닝하여 디버깅을 용이하게 합니다.

    Attributes:
        message: 에러 메시지
        cause: 원인 예외 (옵션)
    """

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        if self.cause:
            return f"{self.message}: {self.cause}"
        return self.message


class NotAuthenticatedError(AuthError):
    """인증되지 않은 상태에서 작업을 시도할 때 발생하는 에러

    Provider가 authenticate()를 호출하지 않았거나,
    활성 Provider가 설정되지 않은 상태에서 세션을 요청할 때 발생합니다.
    """

    def __init__(self, message: str = "인증이 필요합니다", cause: Exception | None = None):
        super().__init__(message, cause)


class AccountNotFoundError(AuthError):
    """계정을 찾을 수 없을 때 발생하는 에러

    SSO Provider에서 지정된 account_id에 해당하는 계정이 없을 때 발생합니다.

    Attributes:
        account_id: 찾을 수 없는 계정 ID
    """

    def __init__(self, account_id: str, cause: Exception | None = None):
        message = f"계정을 찾을 수 없습니다: {account_id}"
        super().__init__(message, cause)
        self.account_id = account_id


class TokenExpiredError(AuthError):
    """토큰이 만료되었을 때 발생하는 에러

    SSO 액세스 토큰이 만료되었거나 디바이스 인증 시간이 초과된 경우 발생합니다.

    Attributes:
        expired_at: 토큰 만료 시간 (옵션)
    """

    def __init__(
        self,
        message: str = "토큰이 만료되었습니다",
        expired_at: datetime | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message, cause)
        self.expired_at = expired_at


class ConfigurationError(AuthError):
    """설정 오류가 발생했을 때 발생하는 에러

    AWS 설정 파일 파싱 실패, 필수 설정값 누락 등의 경우 발생합니다.

    Attributes:
        config_key: 문제가 된 설정 키 이름 (옵션)
    """

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message, cause)
        self.config_key = config_key


class ProviderError(AuthError):
    """Provider에서 발생하는 에러

    Provider 이름과 실패한 작업 정보를 포함하여 디버깅을 용이하게 합니다.
    에러 메시지 형식: "[provider] operation: message"

    Attributes:
        provider: 에러가 발생한 Provider 이름
        operation: 실패한 작업 이름 (예: "authenticate", "get_role_credentials")
    """

    def __init__(
        self,
        provider: str,
        operation: str,
        message: str,
        cause: Exception | None = None,
    ):
        full_message = f"[{provider}] {operation}: {message}"
        super().__init__(full_message, cause)
        self.provider = provider
        self.operation = operation
