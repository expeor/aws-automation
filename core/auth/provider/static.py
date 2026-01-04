# internal/auth/provider/static.py
"""
Static Credentials Provider 구현
- 정적 액세스 키 기반 인증
- 단일 계정만 지원
- 가장 단순한 인증 방식
"""

import logging
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.exceptions import ClientError

from ..types import AccountInfo, ProviderError, ProviderType
from .base import BaseProvider

logger = logging.getLogger(__name__)


@dataclass
class StaticCredentialsConfig:
    """Static Credentials Provider 설정

    두 가지 방식 지원:
    1. 프로파일 기반: profile_name만 지정 (boto3가 ~/.aws/credentials에서 로드)
    2. 직접 지정: access_key_id, secret_access_key 직접 전달

    Attributes:
        profile_name: AWS 프로파일 이름 (프로파일 기반 사용 시)
        access_key_id: AWS Access Key ID (직접 지정 시)
        secret_access_key: AWS Secret Access Key (직접 지정 시)
        session_token: Session Token (임시 자격증명용, 옵션)
        region: 기본 리전
    """

    profile_name: str | None = None
    access_key_id: str | None = None
    secret_access_key: str | None = None
    session_token: str | None = None
    region: str = "ap-northeast-2"

    @property
    def name(self) -> str:
        """Provider 식별자"""
        return self.profile_name or "static-credentials"


class StaticCredentialsProvider(BaseProvider):
    """정적 자격증명 기반 인증 Provider

    특징:
    - 가장 단순한 인증 방식
    - 단일 계정만 지원 (멀티 계정 지원 안함)
    - STS GetCallerIdentity로 검증
    - 프로파일 기반 또는 직접 자격증명 지정 지원

    Example (프로파일 기반):
        config = StaticCredentialsConfig(profile_name="default")
        provider = StaticCredentialsProvider(config)
        provider.authenticate()
        session = provider.get_session()

    Example (직접 지정):
        config = StaticCredentialsConfig(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/...",
            region="ap-northeast-2",
        )
        provider = StaticCredentialsProvider(config)
        provider.authenticate()
        session = provider.get_session()
    """

    def __init__(self, config: StaticCredentialsConfig):
        """StaticCredentialsProvider 초기화

        Args:
            config: StaticCredentialsConfig 설정 객체
        """
        super().__init__(name=config.name, region=config.region)

        self._config = config
        self._session: boto3.Session | None = None
        self._account_info: AccountInfo | None = None

    @property
    def _provider_type(self) -> ProviderType:
        return ProviderType.STATIC_CREDENTIALS

    def authenticate(self) -> None:
        """자격증명 검증

        STS GetCallerIdentity를 호출하여 자격증명 유효성을 확인합니다.
        """
        try:
            # 세션 생성 (프로파일 기반 또는 직접 자격증명)
            if self._config.profile_name and not self._config.access_key_id:
                # 프로파일 기반: boto3가 ~/.aws/credentials에서 로드
                self._session = boto3.Session(
                    profile_name=self._config.profile_name,
                    region_name=self._config.region,
                )
            else:
                # 직접 자격증명 지정
                self._session = boto3.Session(
                    aws_access_key_id=self._config.access_key_id,
                    aws_secret_access_key=self._config.secret_access_key,
                    aws_session_token=self._config.session_token,
                    region_name=self._config.region,
                )

            # STS GetCallerIdentity로 검증
            sts_client = self._session.client("sts")
            identity = sts_client.get_caller_identity()

            # 계정 정보 추출
            arn = identity["Arn"]
            account_id = identity["Account"]

            # ARN에서 사용자/역할 이름 추출
            account_name = self._extract_name_from_arn(arn)

            self._account_info = AccountInfo(
                id=account_id,
                name=account_name,
                roles=[],  # 정적 자격증명은 역할 목록 없음
            )

            self._authenticated = True
            logger.debug(f"자격증명 검증 완료: {account_id} ({account_name})")

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["InvalidClientTokenId", "SignatureDoesNotMatch"]:
                raise ProviderError(
                    provider=self._name,
                    operation="authenticate",
                    message="유효하지 않은 AWS 자격증명입니다",
                    cause=e,
                ) from e
            elif error_code == "ExpiredToken":
                raise ProviderError(
                    provider=self._name,
                    operation="authenticate",
                    message="임시 자격증명이 만료되었습니다",
                    cause=e,
                ) from e
            raise ProviderError(
                provider=self._name,
                operation="authenticate",
                message=f"자격증명 검증 실패: {error_code}",
                cause=e,
            ) from e

    def _extract_name_from_arn(self, arn: str) -> str:
        """ARN에서 사용자/역할 이름 추출"""
        if ":user/" in arn:
            return f"user-{arn.split(':user/')[-1]}"
        elif ":role/" in arn:
            return f"role-{arn.split(':role/')[-1]}"
        elif ":assumed-role/" in arn:
            parts = arn.split(":assumed-role/")[-1].split("/")
            return f"assumed-{parts[0]}" if parts else "unknown"
        return "unknown"

    def get_session(
        self,
        account_id: str | None = None,
        role_name: str | None = None,
        region: str | None = None,
    ) -> boto3.Session:
        """boto3 Session 반환

        정적 자격증명 Provider는 단일 계정만 지원하므로
        account_id와 role_name은 무시됩니다.

        Args:
            account_id: 무시됨
            role_name: 무시됨
            region: AWS 리전 (다른 리전 사용 시)

        Returns:
            boto3.Session 객체
        """
        self._ensure_authenticated()

        if region and region != self._config.region:
            # 다른 리전으로 새 세션 생성
            return boto3.Session(
                aws_access_key_id=self._config.access_key_id,
                aws_secret_access_key=self._config.secret_access_key,
                aws_session_token=self._config.session_token,
                region_name=region,
            )

        # _ensure_authenticated()가 호출되면 self._session은 항상 존재함
        assert self._session is not None
        return self._session

    def get_aws_config(
        self,
        account_id: str | None = None,
        role_name: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """AWS 설정 정보 반환"""
        session = self.get_session(region=region)
        return {
            "region_name": session.region_name,
            "credentials": {
                "access_key_id": self._config.access_key_id,
                "secret_access_key": self._config.secret_access_key,
                "session_token": self._config.session_token,
            },
        }

    def list_accounts(self) -> dict[str, AccountInfo]:
        """계정 목록 반환

        정적 자격증명은 단일 계정만 지원합니다.
        """
        self._ensure_authenticated()

        if not self._account_info:
            return {}

        return {self._account_info.id: self._account_info}

    def supports_multi_account(self) -> bool:
        """멀티 계정 지원 여부"""
        return False

    def get_account_info(self) -> AccountInfo | None:
        """현재 계정 정보 반환"""
        return self._account_info
