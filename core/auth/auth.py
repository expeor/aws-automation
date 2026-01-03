# internal/auth/auth.py
"""
AWS 통합 인증 Manager

- Provider 등록 및 관리
- 활성 Provider 설정
- 멀티 계정 병렬 작업 지원
- 통합된 인터페이스 제공
"""

import concurrent.futures
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar

import boto3
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import BotoCoreError, ClientError

from .config import AWSProfile, AWSSession, Loader, ParsedConfig
from .types import (
    AccountInfo,
    AccountNotFoundError,
    AuthError,
    NotAuthenticatedError,
    Provider,
    ProviderError,
    ProviderType,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Manager:
    """AWS 인증 Manager

    여러 Provider를 등록하고 중앙에서 관리합니다.

    특징:
    - 여러 Provider 등록 및 전환
    - 활성 Provider를 통한 통합 API
    - 멀티 계정 병렬 작업 지원
    - 계정 목록 통합 조회

    Example:
        # Manager 생성
        manager = Manager()

        # Provider 등록
        sso_provider = SSOSessionProvider(config)
        manager.register_provider(sso_provider)
        manager.set_active_provider(sso_provider)

        # 인증
        manager.authenticate()

        # AWS Config 획득
        cfg = manager.get_aws_config(account_id="123456789012", role_name="Admin")

        # 멀티 계정 병렬 작업
        manager.for_each_account_parallel(lambda ctx, account, cfg: ...)
    """

    def __init__(self):
        """Manager 초기화"""
        self._providers: Dict[str, Provider] = {}
        self._active_provider: Optional[Provider] = None
        self._config_loader = Loader()

    # =========================================================================
    # Provider 관리
    # =========================================================================

    def register_provider(self, provider: Provider) -> None:
        """Provider 등록

        Args:
            provider: 등록할 Provider 인스턴스
        """
        key = f"{provider.type().value}:{provider.name()}"
        self._providers[key] = provider
        logger.debug(f"Provider 등록됨: {key}")

    def unregister_provider(self, provider: Provider) -> bool:
        """Provider 등록 해제

        Args:
            provider: 해제할 Provider

        Returns:
            True if 성공
        """
        key = f"{provider.type().value}:{provider.name()}"
        if key in self._providers:
            del self._providers[key]
            if self._active_provider is provider:
                self._active_provider = None
            return True
        return False

    def set_active_provider(self, provider: Provider) -> None:
        """활성 Provider 설정

        Args:
            provider: 활성화할 Provider
        """
        self._active_provider = provider
        logger.debug(f"활성 Provider 설정: {provider.type().value}:{provider.name()}")

    def get_active_provider(self) -> Optional[Provider]:
        """현재 활성 Provider 반환"""
        return self._active_provider

    def find_provider(
        self,
        provider_type: Optional[ProviderType] = None,
        name: Optional[str] = None,
    ) -> Optional[Provider]:
        """Provider 검색

        Args:
            provider_type: Provider 타입 (None이면 무시)
            name: Provider 이름 (None이면 무시)

        Returns:
            매칭되는 첫 번째 Provider 또는 None
        """
        for key, provider in self._providers.items():
            if provider_type and provider.type() != provider_type:
                continue
            if name and provider.name() != name:
                continue
            return provider
        return None

    def list_providers(self) -> List[Provider]:
        """등록된 모든 Provider 목록"""
        return list(self._providers.values())

    # =========================================================================
    # 인증 API (활성 Provider 위임)
    # =========================================================================

    def _ensure_active_provider(self) -> Provider:
        """활성 Provider 확인"""
        if not self._active_provider:
            raise NotAuthenticatedError("활성 Provider가 설정되지 않았습니다")
        return self._active_provider

    def authenticate(self) -> None:
        """활성 Provider로 인증"""
        provider = self._ensure_active_provider()
        provider.authenticate()

    def is_authenticated(self) -> bool:
        """인증 상태 확인"""
        if not self._active_provider:
            return False
        return self._active_provider.is_authenticated()

    def get_session(
        self,
        account_id: Optional[str] = None,
        role_name: Optional[str] = None,
        region: Optional[str] = None,
    ) -> boto3.Session:
        """boto3 Session 획득

        Args:
            account_id: 계정 ID
            role_name: 역할 이름
            region: AWS 리전

        Returns:
            boto3.Session 객체
        """
        provider = self._ensure_active_provider()
        return provider.get_session(account_id, role_name, region)

    def get_aws_config(
        self,
        account_id: Optional[str] = None,
        role_name: Optional[str] = None,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """AWS Config 획득

        Args:
            account_id: 계정 ID
            role_name: 역할 이름
            region: AWS 리전

        Returns:
            AWS 설정 딕셔너리
        """
        provider = self._ensure_active_provider()
        return provider.get_aws_config(account_id, role_name, region)

    def get_default_region(self) -> str:
        """기본 리전 반환"""
        provider = self._ensure_active_provider()
        return provider.get_default_region()

    # =========================================================================
    # 계정 관리
    # =========================================================================

    def list_accounts(self) -> Dict[str, AccountInfo]:
        """활성 Provider의 계정 목록"""
        provider = self._ensure_active_provider()
        return provider.list_accounts()

    def list_all_accounts(self) -> Dict[str, AccountInfo]:
        """모든 Provider의 계정 목록 통합"""
        all_accounts = {}

        for provider in self._providers.values():
            try:
                if provider.is_authenticated():
                    accounts = provider.list_accounts()
                    all_accounts.update(accounts)
            except (ClientError, BotoCoreError) as e:
                logger.warning(f"Provider {provider.name()} 계정 조회 실패 (AWS): {e}")
            except (ProviderError, AuthError) as e:
                logger.warning(f"Provider {provider.name()} 계정 조회 실패 (인증): {e}")

        return all_accounts

    def get_account(self, account_id: str) -> Optional[AccountInfo]:
        """특정 계정 정보 조회

        Args:
            account_id: AWS 계정 ID

        Returns:
            AccountInfo 또는 None
        """
        accounts = self.list_accounts()
        return accounts.get(account_id)

    # =========================================================================
    # 멀티 계정 작업
    # =========================================================================

    def for_each_account(
        self,
        func: Callable[[AccountInfo, boto3.Session], T],
        accounts: Optional[Dict[str, AccountInfo]] = None,
        role_name: Optional[str] = None,
        region: Optional[str] = None,
    ) -> Dict[str, T]:
        """모든 계정에 대해 순차적으로 작업 수행

        Args:
            func: (AccountInfo, Session) -> T 함수
            accounts: 대상 계정 목록 (None이면 전체)
            role_name: 사용할 역할 이름
            region: AWS 리전

        Returns:
            {account_id: result} 딕셔너리
        """
        provider = self._ensure_active_provider()

        if accounts is None:
            accounts = provider.list_accounts()

        results = {}
        for account_id, account_info in accounts.items():
            try:
                # 역할 이름 결정
                role = role_name or account_info.get_role()
                if not role:
                    logger.warning(f"계정 {account_id}에 사용할 역할이 없습니다")
                    continue

                # 세션 획득
                session = provider.get_session(account_id, role, region)

                # 작업 수행
                result = func(account_info, session)
                results[account_id] = result

            except (ClientError, BotoCoreError) as e:
                logger.error(f"계정 {account_id} AWS 작업 실패: {e}")
                results[account_id] = None
            except (ProviderError, AuthError) as e:
                logger.error(f"계정 {account_id} 인증 실패: {e}")
                results[account_id] = None

        return results

    def for_each_account_parallel(
        self,
        func: Callable[[AccountInfo, boto3.Session], T],
        accounts: Optional[Dict[str, AccountInfo]] = None,
        role_name: Optional[str] = None,
        region: Optional[str] = None,
        max_workers: int = 10,
    ) -> Dict[str, T]:
        """모든 계정에 대해 병렬로 작업 수행

        Args:
            func: (AccountInfo, Session) -> T 함수
            accounts: 대상 계정 목록 (None이면 전체)
            role_name: 사용할 역할 이름
            region: AWS 리전
            max_workers: 최대 병렬 작업 수

        Returns:
            {account_id: result} 딕셔너리
        """
        provider = self._ensure_active_provider()

        if accounts is None:
            accounts = provider.list_accounts()

        results = {}

        def process_account(
            account_id: str,
            account_info: AccountInfo,
        ) -> tuple:
            try:
                role = role_name or account_info.get_role()
                if not role:
                    return account_id, None

                session = provider.get_session(account_id, role, region)
                result = func(account_info, session)
                return account_id, result
            except (ClientError, BotoCoreError) as e:
                logger.error(f"계정 {account_id} AWS 작업 실패: {e}")
                return account_id, None
            except (ProviderError, AuthError) as e:
                logger.error(f"계정 {account_id} 인증 실패: {e}")
                return account_id, None

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_account, acc_id, acc_info): acc_id
                for acc_id, acc_info in accounts.items()
            }

            for future in concurrent.futures.as_completed(futures):
                try:
                    account_id, result = future.result()
                    results[account_id] = result
                except concurrent.futures.CancelledError:
                    acc_id = futures[future]
                    logger.warning(f"계정 {acc_id} 작업 취소됨")
                    results[acc_id] = None
                except (ClientError, BotoCoreError, ProviderError, AuthError) as e:
                    acc_id = futures[future]
                    logger.error(f"계정 {acc_id} 작업 예외: {e}")
                    results[acc_id] = None

        return results

    # =========================================================================
    # 설정 로드 헬퍼
    # =========================================================================

    def load_config(self) -> ParsedConfig:
        """AWS 설정 파일 로드"""
        return self._config_loader.load()

    def list_profiles(self) -> List[str]:
        """프로파일 목록"""
        config = self.load_config()
        return list(config.profiles.keys())

    def list_sso_sessions(self) -> List[str]:
        """SSO 세션 목록"""
        config = self.load_config()
        return list(config.sessions.keys())

    def get_profile(self, name: str) -> Optional[AWSProfile]:
        """프로파일 정보 조회"""
        config = self.load_config()
        return config.profiles.get(name)

    def get_sso_session(self, name: str) -> Optional[AWSSession]:
        """SSO 세션 정보 조회"""
        config = self.load_config()
        return config.sessions.get(name)

    # =========================================================================
    # 리소스 정리
    # =========================================================================

    def close(self) -> None:
        """모든 Provider 리소스 정리"""
        for provider in self._providers.values():
            try:
                provider.close()
            except (ClientError, BotoCoreError) as e:
                logger.warning(f"Provider 정리 실패 (AWS): {e}")
            except (ProviderError, OSError) as e:
                logger.warning(f"Provider 정리 실패: {e}")

        self._providers.clear()
        self._active_provider = None


# =============================================================================
# 편의 함수
# =============================================================================


def create_manager() -> Manager:
    """Manager 인스턴스 생성 (편의 함수)"""
    return Manager()
