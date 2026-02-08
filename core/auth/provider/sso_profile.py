# core/auth/provider/sso_profile.py
"""
core/auth/provider/sso_profile.py - SSO Profile Provider 구현

AWS SSO 프로파일 기반 인증 Provider입니다. SSOSessionProvider를 상속하여
특정 계정/역할에 바인딩된 기본값 기능을 추가합니다.

특징:
    - 기본 account_id/role_name이 설정되어 get_session() 호출 시 생략 가능
    - SSOSessionProvider의 멀티 계정 기능도 사용 가능
    - Legacy SSO (sso_session 없이 직접 설정) 형식도 지원
"""

import logging
from dataclasses import dataclass
from typing import Any

import boto3

from ..types import AccountInfo, ProviderType
from .sso_session import SSOSessionConfig, SSOSessionProvider

logger = logging.getLogger(__name__)


@dataclass
class SSOProfileConfig:
    """SSO Profile Provider 설정

    Attributes:
        profile_name: 프로파일 이름
        account_id: 기본 계정 ID
        role_name: 기본 역할 이름
        region: 기본 리전
        start_url: SSO 시작 URL
        sso_region: SSO 리전
        sso_session: SSO 세션 이름 (Optional, 신규 형식에서 사용)
    """

    profile_name: str
    account_id: str
    role_name: str
    region: str
    start_url: str
    sso_region: str
    sso_session: str | None = None


class SSOProfileProvider(SSOSessionProvider):
    """SSO Profile 기반 인증 Provider

    SSOSessionProvider를 상속하여 기본 계정/역할 바인딩 기능 추가.

    특징:
    - 특정 계정/역할에 바인딩된 프로파일
    - 기본 계정/역할로 간편하게 세션 획득
    - 다른 계정 접근도 가능 (멀티 계정)

    Example:
        config = SSOProfileConfig(
            profile_name="my-profile",
            sso_session="my-sso",
            account_id="123456789012",
            role_name="AdminRole",
            region="ap-northeast-2",
            start_url="https://my-sso.awsapps.com/start",
            sso_region="ap-northeast-2",
        )
        provider = SSOProfileProvider(config)
        provider.authenticate()

        # 기본 계정/역할로 세션 획득
        session = provider.get_session()

        # 다른 계정으로 세션 획득
        other_session = provider.get_session(
            account_id="987654321098",
            role_name="ReadOnly"
        )
    """

    def __init__(self, config: SSOProfileConfig):
        """SSOProfileProvider 초기화

        Args:
            config: SSOProfileConfig 설정 객체
        """
        # SSO Session 설정으로 부모 초기화
        # sso_session이 없는 레거시 형식도 지원 (profile_name을 session_name으로 사용)
        sso_config = SSOSessionConfig(
            session_name=config.sso_session or config.profile_name,
            start_url=config.start_url,
            region=config.sso_region,
        )
        super().__init__(sso_config)

        self._profile_config = config
        self._name = config.profile_name  # 프로파일 이름으로 오버라이드
        self._default_region = config.region
        self._default_account_id = config.account_id
        self._default_role_name = config.role_name

    @property
    def _provider_type(self) -> ProviderType:
        return ProviderType.SSO_PROFILE

    @property
    def default_account_id(self) -> str:
        """기본 계정 ID"""
        return self._default_account_id

    @property
    def default_role_name(self) -> str:
        """기본 역할 이름"""
        return self._default_role_name

    def get_session(
        self,
        account_id: str | None = None,
        role_name: str | None = None,
        region: str | None = None,
        retry_on_expired: bool = True,
    ) -> boto3.Session:
        """세션 획득 (기본값 사용 가능)

        account_id와 role_name을 생략하면 프로파일의 기본값 사용.

        Args:
            account_id: AWS 계정 ID (기본값 사용 가능)
            role_name: 역할 이름 (기본값 사용 가능)
            region: AWS 리전
            retry_on_expired: 토큰 만료 시 재인증 후 재시도 여부 (기본: True)

        Returns:
            boto3.Session 객체
        """
        return super().get_session(
            account_id=account_id or self._default_account_id,
            role_name=role_name or self._default_role_name,
            region=region,
            retry_on_expired=retry_on_expired,
        )

    def get_aws_config(
        self,
        account_id: str | None = None,
        role_name: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """AWS 설정 정보를 반환합니다 (기본값 사용 가능).

        Args:
            account_id: AWS 계정 ID (None이면 기본값 사용)
            role_name: 역할 이름 (None이면 기본값 사용)
            region: AWS 리전

        Returns:
            {"region_name": str, "credentials": ...} 딕셔너리
        """
        return super().get_aws_config(
            account_id=account_id or self._default_account_id,
            role_name=role_name or self._default_role_name,
            region=region,
        )

    def get_default_account_info(self) -> AccountInfo:
        """프로파일에 설정된 기본 계정 정보를 반환합니다.

        SSO 계정 목록에서 기본 계정을 찾고, 없으면 기본 정보를 생성합니다.

        Returns:
            AccountInfo 객체
        """
        accounts = self.list_accounts()
        if self._default_account_id in accounts:
            return accounts[self._default_account_id]

        # 계정 목록에 없으면 기본 정보 생성
        return AccountInfo(
            id=self._default_account_id,
            name=f"account-{self._default_account_id}",
            roles=[self._default_role_name],
            default_role=self._default_role_name,
        )
