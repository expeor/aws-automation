# internal/auth/provider/sso_session.py
"""
SSO Session Provider 구현

- AWS SSO 세션 기반 인증
- 멀티 계정 지원
- 토큰 캐시 관리 (AWS CLI 호환)
"""

import contextlib
import logging
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timezone
from time import sleep
from typing import Any

import boto3
from botocore.exceptions import ClientError

from ..cache import TokenCache, TokenCacheManager
from ..types import (
    AccountInfo,
    ProviderError,
    ProviderType,
    TokenExpiredError,
)
from .base import BaseProvider

logger = logging.getLogger(__name__)


@dataclass
class SSOSessionConfig:
    """SSO Session Provider 설정

    Attributes:
        session_name: SSO 세션 이름
        start_url: SSO 시작 URL
        region: SSO 리전
        client_name: OIDC 클라이언트 이름 (기본: "python-auth")
        client_type: OIDC 클라이언트 타입 (기본: "public")
    """

    session_name: str
    start_url: str
    region: str
    client_name: str = "python-auth"
    client_type: str = "public"


class SSOSessionProvider(BaseProvider):
    """SSO Session 기반 인증 Provider

    특징:
    - AWS SSO (IAM Identity Center) 세션 기반 인증
    - 멀티 계정 지원 (ListAccounts API)
    - AWS CLI 호환 토큰 캐시 (~/.aws/sso/cache/)
    - 자동 토큰 갱신

    Example:
        config = SSOSessionConfig(
            session_name="my-sso",
            start_url="https://my-sso.awsapps.com/start",
            region="ap-northeast-2",
        )
        provider = SSOSessionProvider(config)
        provider.authenticate()

        # 계정 목록 조회
        accounts = provider.list_accounts()

        # 특정 계정의 세션 획득
        session = provider.get_session(account_id="123456789012", role_name="AdminRole")
    """

    def __init__(self, config: SSOSessionConfig):
        """SSOSessionProvider 초기화

        Args:
            config: SSOSessionConfig 설정 객체
        """
        super().__init__(name=config.session_name, region=config.region)

        self._config = config
        self._token_cache_manager = TokenCacheManager(
            session_name=config.session_name,
            start_url=config.start_url,
        )
        self._token_cache: TokenCache | None = None
        self._access_token: str | None = None

        # boto3 클라이언트
        self._base_session = boto3.Session(region_name=config.region)
        self._sso_client = self._base_session.client("sso", region_name=config.region)
        self._sso_oidc_client = self._base_session.client("sso-oidc", region_name=config.region)

    @property
    def _provider_type(self) -> ProviderType:
        return ProviderType.SSO_SESSION

    def authenticate(self, force: bool = False) -> None:
        """SSO 인증 수행

        Args:
            force: True면 캐시를 무시하고 강제로 디바이스 인증 수행

        1. 캐시된 토큰이 있고 유효하면 사용
        2. 없거나 만료되었으면 디바이스 인증 흐름 시작
        """
        # force 옵션이면 캐시 무효화
        if force:
            logger.debug("강제 인증 요청 - 캐시 무효화")
            self._token_cache = None
            self._access_token = None
            self._token_cache_manager.delete()  # 파일 캐시도 삭제

        # 1. 캐시된 토큰 확인
        if not self._token_cache:
            self._token_cache = self._token_cache_manager.load()

        if self._token_cache and not self._token_cache.is_expired():
            logger.debug(f"캐시된 SSO 토큰 사용: {self._config.session_name}")
            self._access_token = self._token_cache.access_token
            self._authenticated = True
            return

        # 2. 토큰 갱신 시도 (refresh_token이 있는 경우)
        if self._token_cache and self._token_cache.refresh_token:
            try:
                self._refresh_token()
                self._authenticated = True
                return
            except Exception as e:
                logger.debug(f"토큰 갱신 실패, 새 인증 시작: {e}")

        # 3. 새 디바이스 인증 흐름
        self._start_device_authorization()
        self._authenticated = True

    def _start_device_authorization(self) -> None:
        """디바이스 인증 흐름 시작"""
        try:
            # 클라이언트 등록
            client_creds = self._sso_oidc_client.register_client(
                clientName=self._config.client_name,
                clientType=self._config.client_type,
                scopes=["openid", "profile", "email"],
            )

            # 디바이스 인증 시작
            device_auth = self._sso_oidc_client.start_device_authorization(
                clientId=client_creds["clientId"],
                clientSecret=client_creds["clientSecret"],
                startUrl=self._config.start_url,
            )

            # 사용자에게 URL 제공
            verification_url = device_auth["verificationUriComplete"]
            logger.info(f"브라우저에서 인증하세요: {verification_url}")

            with contextlib.suppress(Exception):
                webbrowser.open(verification_url, new=2)

            # 토큰 폴링
            self._poll_for_token(
                client_id=client_creds["clientId"],
                client_secret=client_creds["clientSecret"],
                device_code=device_auth["deviceCode"],
                interval=device_auth.get("interval", 5),
                expires_in=device_auth.get("expiresIn", 600),
            )

        except ClientError as e:
            raise ProviderError(
                provider=self._name,
                operation="device_authorization",
                message=f"디바이스 인증 실패: {e}",
                cause=e,
            ) from e

    def _poll_for_token(
        self,
        client_id: str,
        client_secret: str,
        device_code: str,
        interval: int,
        expires_in: int,
    ) -> None:
        """토큰 폴링"""
        max_attempts = expires_in // interval

        for _ in range(max_attempts):
            sleep(interval)

            try:
                token_response = self._sso_oidc_client.create_token(
                    grantType="urn:ietf:params:oauth:grant-type:device_code",
                    deviceCode=device_code,
                    clientId=client_id,
                    clientSecret=client_secret,
                )

                # 토큰 캐시 저장 (boto3-stubs TypedDict는 dict와 호환)
                self._save_token_cache(dict(token_response), client_id, client_secret)
                return

            except self._sso_oidc_client.exceptions.AuthorizationPendingException:
                continue
            except self._sso_oidc_client.exceptions.SlowDownException:
                sleep(interval)
                continue
            except self._sso_oidc_client.exceptions.ExpiredTokenException:
                raise TokenExpiredError("디바이스 인증 시간 초과") from None
            except Exception as e:
                raise ProviderError(
                    provider=self._name,
                    operation="create_token",
                    message=f"토큰 생성 실패: {e}",
                    cause=e,
                ) from e

        raise TokenExpiredError("디바이스 인증 시간 초과")

    def _save_token_cache(
        self,
        token_response: dict[str, Any],
        client_id: str,
        client_secret: str,
    ) -> None:
        """토큰 캐시 저장"""
        # 만료 시간 계산 (기존 aws_sso_helper.py 방식)
        expires_in = token_response.get("expiresIn", 28800)  # 기본 8시간
        expires_at_str = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + expires_in).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        self._token_cache = TokenCache(
            access_token=token_response["accessToken"],
            expires_at=expires_at_str,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=token_response.get("refreshToken"),
            region=self._config.region,
            start_url=self._config.start_url,
        )

        self._token_cache_manager.save(self._token_cache)
        self._access_token = self._token_cache.access_token
        logger.debug(f"토큰 캐시 저장 완료: 만료 {expires_at_str}")

    def _refresh_token(self) -> None:
        """토큰 갱신"""
        if not self._token_cache or not self._token_cache.refresh_token:
            raise TokenExpiredError("갱신 토큰이 없습니다")

        try:
            token_response = self._sso_oidc_client.create_token(
                grantType="refresh_token",
                clientId=self._token_cache.client_id,
                clientSecret=self._token_cache.client_secret,
                refreshToken=self._token_cache.refresh_token,
            )

            self._save_token_cache(
                dict(token_response),
                self._token_cache.client_id,
                self._token_cache.client_secret,
            )

        except Exception as e:
            raise TokenExpiredError(f"토큰 갱신 실패: {e}", cause=e) from e

    def refresh(self) -> None:
        """자격 증명 갱신"""
        if self._token_cache and self._token_cache.refresh_token:
            self._refresh_token()
        else:
            self._start_device_authorization()

    def get_session(
        self,
        account_id: str | None = None,
        role_name: str | None = None,
        region: str | None = None,
        retry_on_expired: bool = True,
    ) -> boto3.Session:
        """특정 계정/역할에 대한 boto3 Session 반환

        Args:
            account_id: AWS 계정 ID (필수)
            role_name: 역할 이름 (필수)
            region: AWS 리전 (기본값 사용 가능)
            retry_on_expired: 토큰 만료 시 재인증 후 재시도 여부 (기본: True)

        Returns:
            boto3.Session 객체
        """
        self._ensure_authenticated()

        if not account_id or not role_name:
            raise ValueError("account_id와 role_name은 필수입니다")

        # 캐시 확인
        cached = self._get_cached_credentials(account_id, role_name)
        if cached:
            return self._create_session(
                cached["access_key_id"],
                cached["secret_access_key"],
                cached.get("session_token"),
                region or self._default_region,
            )

        # 새 자격증명 획득
        assert self._access_token is not None, "인증이 필요합니다"
        try:
            response = self._sso_client.get_role_credentials(
                roleName=role_name,
                accountId=account_id,
                accessToken=self._access_token,
            )
            # TypedDict를 dict로 변환하여 안전하게 접근
            credentials = dict(response["roleCredentials"])

            # 캐시 저장
            creds_dict: dict[str, str] = {
                "access_key_id": str(credentials["accessKeyId"]),
                "secret_access_key": str(credentials["secretAccessKey"]),
                "session_token": str(credentials["sessionToken"]),
            }
            self._cache_credentials(account_id, role_name, creds_dict)

            return self._create_session(
                str(credentials["accessKeyId"]),
                str(credentials["secretAccessKey"]),
                str(credentials["sessionToken"]),
                region or self._default_region,
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["UnauthorizedException", "ExpiredTokenException"]:
                self._authenticated = False

                # 토큰 만료 시 자동 재인증 후 재시도
                if retry_on_expired:
                    logger.info("SSO 토큰 만료됨, 재인증 시도...")
                    self.authenticate(force=True)  # 강제 재인증
                    return self.get_session(account_id, role_name, region, retry_on_expired=False)

                raise TokenExpiredError(
                    f"SSO 토큰이 만료되었습니다: {error_code}",
                    cause=e,
                ) from e
            raise ProviderError(
                provider=self._name,
                operation="get_role_credentials",
                message=f"자격증명 획득 실패: {e}",
                cause=e,
            ) from e

    def get_aws_config(
        self,
        account_id: str | None = None,
        role_name: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """AWS 설정 정보 반환"""
        session = self.get_session(account_id, role_name, region)
        return {
            "region_name": session.region_name,
            "credentials": session.get_credentials(),
        }

    def list_accounts(self, retry_on_expired: bool = True) -> dict[str, AccountInfo]:
        """접근 가능한 계정 목록 반환

        Args:
            retry_on_expired: 토큰 만료 시 재인증 후 재시도 여부 (기본: True)
        """
        self._ensure_authenticated()

        # 캐시 확인
        cached_accounts = self._account_cache.get_all()
        if cached_accounts:
            return cached_accounts

        accounts = {}
        assert self._access_token is not None, "인증이 필요합니다"

        try:
            paginator = self._sso_client.get_paginator("list_accounts")

            for page in paginator.paginate(accessToken=self._access_token):
                for account in page.get("accountList", []):
                    # TypedDict fields accessed with explicit str conversion
                    acct = dict(account)  # Convert TypedDict to regular dict
                    account_id = str(acct.get("accountId", ""))

                    # 역할 목록 조회
                    roles = self._list_account_roles(account_id)

                    email_value = acct.get("emailAddress")
                    account_info = AccountInfo(
                        id=account_id,
                        name=str(acct.get("accountName", f"account-{account_id}")),
                        email=str(email_value) if email_value else None,
                        roles=roles,
                    )
                    accounts[account_id] = account_info

            # 캐시 저장
            self._account_cache.set_all(accounts)

            return accounts

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["UnauthorizedException", "ExpiredTokenException"]:
                self._authenticated = False

                # 토큰 만료 시 자동 재인증 후 재시도
                if retry_on_expired:
                    logger.info("SSO 토큰 만료됨, 재인증 시도...")
                    self.authenticate(force=True)  # 강제 재인증
                    return self.list_accounts(retry_on_expired=False)

                raise TokenExpiredError(
                    f"SSO 토큰이 만료되었습니다: {error_code}",
                    cause=e,
                ) from e
            raise ProviderError(
                provider=self._name,
                operation="list_accounts",
                message=f"계정 목록 조회 실패: {e}",
                cause=e,
            ) from e

    def _list_account_roles(self, account_id: str) -> list[str]:
        """특정 계정의 역할 목록 조회"""
        if self._access_token is None:
            return []
        try:
            response = self._sso_client.list_account_roles(
                accessToken=self._access_token,
                accountId=account_id,
            )
            # Convert TypedDict role entries to strings
            return [str(dict(role).get("roleName", "")) for role in response.get("roleList", [])]
        except Exception:
            return []  # Return empty list on API failure

    def supports_multi_account(self) -> bool:
        """멀티 계정 지원 여부"""
        return True
