# internal/auth/provider/base.py
"""
Provider 기본 클래스

모든 Provider가 상속받는 공통 기능을 제공합니다.
"""

import logging
from abc import abstractmethod

import boto3

from ..cache import AccountCache, CredentialsCache
from ..types import NotAuthenticatedError, Provider, ProviderType

logger = logging.getLogger(__name__)


class BaseProvider(Provider):
    """Provider 기본 구현

    모든 Provider가 상속받아 사용하는 공통 기능:
    - 인증 상태 관리
    - 캐시 관리
    - 로깅
    """

    def __init__(
        self,
        name: str,
        region: str = "ap-northeast-2",
    ):
        """BaseProvider 초기화

        Args:
            name: Provider 이름 (식별자)
            region: 기본 AWS 리전
        """
        self._name = name
        self._default_region = region
        self._authenticated = False

        # 캐시
        self._account_cache = AccountCache()
        self._credentials_cache = CredentialsCache()

    @property
    @abstractmethod
    def _provider_type(self) -> ProviderType:
        """Provider 타입 (서브클래스에서 구현)"""
        pass

    def type(self) -> ProviderType:
        """Provider 타입 반환"""
        return self._provider_type

    def name(self) -> str:
        """Provider 이름 반환"""
        return self._name

    def is_authenticated(self) -> bool:
        """인증 상태 확인"""
        return self._authenticated

    def get_default_region(self) -> str:
        """기본 리전 반환"""
        return self._default_region

    def _ensure_authenticated(self) -> None:
        """인증 상태 확인 (인증되지 않으면 예외 발생)"""
        if not self._authenticated:
            raise NotAuthenticatedError(f"Provider '{self._name}'이(가) 인증되지 않았습니다")

    def _create_session(
        self,
        access_key_id: str,
        secret_access_key: str,
        session_token: str | None = None,
        region: str | None = None,
    ) -> boto3.Session:
        """boto3 Session 생성

        Args:
            access_key_id: AWS Access Key ID
            secret_access_key: AWS Secret Access Key
            session_token: Session Token (임시 자격증명용)
            region: AWS 리전

        Returns:
            boto3.Session 객체
        """
        return boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            aws_session_token=session_token,
            region_name=region or self._default_region,
        )

    def _get_cached_credentials(
        self,
        account_id: str,
        role_name: str,
    ) -> dict[str, str] | None:
        """캐시된 자격증명 조회"""
        return self._credentials_cache.get(account_id, role_name)

    def _cache_credentials(
        self,
        account_id: str,
        role_name: str,
        credentials: dict[str, str],
    ) -> None:
        """자격증명 캐시"""
        self._credentials_cache.set(account_id, role_name, credentials)

    def close(self) -> None:
        """리소스 정리"""
        self._account_cache.clear()
        self._credentials_cache.clear()
        self._authenticated = False
