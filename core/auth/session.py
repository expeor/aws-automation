# internal/auth/session.py
"""
공통 인증 인터페이스

프로파일명만 주면 자동으로 Provider를 감지하고 세션을 생성합니다.
모든 도구에서 이 인터페이스를 사용하면 인증 코드 중복을 방지할 수 있습니다.

## 1. 프로파일 기반 (기존 방식)

단일 프로파일 또는 다중 프로파일로 세션 획득.
Static, SSO Profile에 적합.

    from core.auth import get_session, iter_sessions

    # 단일 프로파일 + 단일 리전
    session = get_session("my-profile", "ap-northeast-2")

    # 멀티 프로파일 + 다중 리전
    for session, profile, region in iter_sessions(["dev", "prod"], regions):
        ec2 = session.client("ec2")

## 2. Context 기반 + 결과 추적 (권장)

    from core.auth import SessionIterator

    with SessionIterator(ctx) as sessions:
        for session, identifier, region in sessions:
            # 작업 수행
            ec2 = session.client("ec2")

    # 자동으로 성공/실패 추적
    if sessions.has_failures_only():
        console.print("모든 조회 실패")
    elif sessions.has_no_sessions():
        console.print("조회 가능한 계정 없음")

## 2. Context 기반 (Flow 통합 방식)

ExecutionContext를 사용하여 SSO Session 멀티 계정 지원.
Flow에서 선택된 계정/역할 정보를 자동으로 사용.

    from core.auth import iter_context_sessions

    # SSO Session: 계정별 세션 + 리전별 순회
    # Static/SSO Profile: 프로파일 세션 + 리전별 순회
    for session, identifier, region in iter_context_sessions(ctx):
        ec2 = session.client("ec2")
        # identifier: SSO Session이면 account_id, 그 외는 profile_name
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator
from typing import (
    TYPE_CHECKING,
    TypeVar,
)

from .config import Loader, detect_provider_type
from .types import ProviderType

if TYPE_CHECKING:
    import boto3

    from cli.flow.context import ExecutionContext
    from core.parallel import ParallelExecutionResult

    from .provider import BaseProvider

T = TypeVar("T")

logger = logging.getLogger(__name__)

# 프로파일별 캐시된 Provider (Thread-safe)
_provider_cache: dict[str, BaseProvider] = {}
_cache_lock = threading.RLock()


def get_session(
    profile: str,
    region: str | None = None,
    retry_on_expired: bool = True,
) -> boto3.Session:
    """단일 프로파일 + 단일 리전 세션 획득 (Thread-safe, 자동 재인증)

    Args:
        profile: AWS 프로파일명
        region: AWS 리전 (None이면 프로파일 기본 리전)
        retry_on_expired: 토큰 만료 시 재인증 후 재시도 여부 (기본: True)

    Returns:
        boto3.Session 객체

    Example:
        session = get_session("my-profile", "ap-northeast-2")
        ec2 = session.client("ec2")
    """
    from .types import TokenExpiredError

    # 캐시 확인 (락 내에서)
    with _cache_lock:
        if profile in _provider_cache:
            provider = _provider_cache[profile]
            if provider.is_authenticated():
                try:
                    return provider.get_session(region=region)
                except TokenExpiredError:
                    if retry_on_expired:
                        logger.info(f"토큰 만료, 재인증 시도: {profile}")
                        # 캐시에서 제거
                        provider.close()
                        del _provider_cache[profile]
                        # 재귀 호출로 새 Provider 생성 (retry 비활성화)
                        return get_session(profile, region, retry_on_expired=False)
                    else:
                        raise

    # 락 밖에서 Provider 생성 (네트워크 호출 가능)
    provider = _create_provider_for_profile(profile)
    provider.authenticate()

    # 캐시 저장 (Double-check 패턴)
    with _cache_lock:
        if profile not in _provider_cache:
            _provider_cache[profile] = provider
        else:
            # 다른 스레드가 먼저 생성했으면 새로 만든 건 버림
            provider.close()
            provider = _provider_cache[profile]

    return provider.get_session(region=region)


def iter_regions(
    profile: str,
    regions: list[str],
) -> Iterator[tuple[boto3.Session, str]]:
    """단일 프로파일 + 다중 리전 세션 제너레이터

    Args:
        profile: AWS 프로파일명
        regions: 리전 리스트

    Yields:
        (session, region) 튜플

    Example:
        regions = ["ap-northeast-2", "us-east-1"]
        for session, region in iter_regions("my-profile", regions):
            ec2 = session.client("ec2")
    """
    for region in regions:
        try:
            session = get_session(profile, region)
            yield session, region
        except Exception as e:
            logger.warning(f"세션 생성 실패 [{profile}/{region}]: {e}")
            continue


def iter_profiles(
    profiles: list[str],
    region: str,
) -> Iterator[tuple[boto3.Session, str]]:
    """멀티 프로파일 + 단일 리전 세션 제너레이터

    ※ SSO 멀티 프로파일은 sso-session 사용을 권장합니다.

    Args:
        profiles: 프로파일명 리스트 (Access Key 기반 권장)
        region: AWS 리전

    Yields:
        (session, profile) 튜플

    Example:
        profiles = ["dev", "prod"]
        for session, profile in iter_profiles(profiles, "ap-northeast-2"):
            ec2 = session.client("ec2")
    """
    for profile in profiles:
        try:
            session = get_session(profile, region)
            yield session, profile
        except Exception as e:
            logger.warning(f"세션 생성 실패 [{profile}/{region}]: {e}")
            continue


def iter_sessions(
    profiles: list[str],
    regions: list[str],
) -> Iterator[tuple[boto3.Session, str, str]]:
    """멀티 프로파일 + 다중 리전 세션 제너레이터

    ※ SSO 멀티 프로파일은 sso-session 사용을 권장합니다.

    Args:
        profiles: 프로파일명 리스트 (Access Key 기반 권장)
        regions: 리전 리스트

    Yields:
        (session, profile, region) 튜플

    Example:
        profiles = ["dev", "prod"]
        regions = ["ap-northeast-2", "us-east-1"]
        for session, profile, region in iter_sessions(profiles, regions):
            ec2 = session.client("ec2")
    """
    for profile in profiles:
        for region in regions:
            try:
                session = get_session(profile, region)
                yield session, profile, region
            except Exception as e:
                logger.warning(f"세션 생성 실패 [{profile}/{region}]: {e}")
                continue


def clear_cache() -> None:
    """Provider 캐시 초기화 (Thread-safe)"""
    global _provider_cache

    with _cache_lock:
        for provider in _provider_cache.values():
            try:
                provider.close()
            except Exception as e:
                # Provider close는 cleanup 작업이므로 모든 예외 무시
                logger.debug(f"Provider close 중 오류 (무시됨): {e}")
        _provider_cache.clear()


def _create_provider_for_profile(profile: str):
    """프로파일에 맞는 Provider 생성

    Args:
        profile: AWS 프로파일명

    Returns:
        Provider 인스턴스
    """
    from .provider import (
        SSOProfileConfig,
        SSOProfileProvider,
        SSOSessionConfig,
        SSOSessionProvider,
        StaticCredentialsConfig,
        StaticCredentialsProvider,
    )

    # 설정 로드
    loader = Loader()
    config = loader.load()

    aws_profile = config.profiles.get(profile)
    if not aws_profile:
        raise ValueError(f"프로파일을 찾을 수 없습니다: {profile}")

    # Provider 타입 감지
    provider_type = detect_provider_type(aws_profile)

    if provider_type == ProviderType.SSO_SESSION:
        # sso_session 참조하는 경우
        session_name = aws_profile.sso_session
        if not session_name:
            raise ValueError(f"프로파일 '{profile}'에 sso_session이 설정되지 않았습니다")
        sso_session = config.sessions.get(session_name)
        if not sso_session:
            raise ValueError(f"SSO 세션을 찾을 수 없습니다: {session_name}")

        # SSOSessionProvider는 멀티 계정 지원으로, account_id/role_name은
        # get_session() 호출 시 전달받음 (Config에는 포함하지 않음)
        sso_session_config = SSOSessionConfig(
            session_name=session_name,
            start_url=sso_session.start_url,
            region=sso_session.region,
        )
        return SSOSessionProvider(sso_session_config)

    elif provider_type == ProviderType.SSO_PROFILE:
        # SSO 프로파일 (sso_session 참조 또는 Legacy 직접 설정)
        # sso_session이 있으면 해당 세션에서 start_url과 sso_region 가져옴
        start_url: str
        sso_region: str
        profile_session_name: str | None
        if aws_profile.sso_session:
            profile_session_name = aws_profile.sso_session
            sso_session = config.sessions.get(profile_session_name)
            if not sso_session:
                raise ValueError(f"SSO 세션을 찾을 수 없습니다: {profile_session_name}")
            start_url = sso_session.start_url
            sso_region = sso_session.region
        else:
            # Legacy: 프로파일에 직접 설정된 경우
            profile_session_name = None
            if not aws_profile.sso_start_url:
                raise ValueError(f"프로파일 '{profile}'에 sso_start_url이 설정되지 않았습니다")
            if not aws_profile.sso_region:
                raise ValueError(f"프로파일 '{profile}'에 sso_region이 설정되지 않았습니다")
            start_url = aws_profile.sso_start_url
            sso_region = aws_profile.sso_region

        if not aws_profile.sso_account_id:
            raise ValueError(f"프로파일 '{profile}'에 sso_account_id가 설정되지 않았습니다")
        if not aws_profile.sso_role_name:
            raise ValueError(f"프로파일 '{profile}'에 sso_role_name이 설정되지 않았습니다")

        sso_profile_config = SSOProfileConfig(
            profile_name=profile,
            account_id=aws_profile.sso_account_id,
            role_name=aws_profile.sso_role_name,
            region=aws_profile.region or sso_region,
            start_url=start_url,
            sso_region=sso_region,
            sso_session=profile_session_name,
        )
        return SSOProfileProvider(sso_profile_config)

    elif provider_type == ProviderType.STATIC_CREDENTIALS:
        # Access Key 기반
        if not aws_profile.aws_access_key_id:
            raise ValueError(f"프로파일 '{profile}'에 aws_access_key_id가 설정되지 않았습니다")
        if not aws_profile.aws_secret_access_key:
            raise ValueError(f"프로파일 '{profile}'에 aws_secret_access_key가 설정되지 않았습니다")
        static_config = StaticCredentialsConfig(
            profile_name=profile,
            access_key_id=aws_profile.aws_access_key_id,
            secret_access_key=aws_profile.aws_secret_access_key,
            session_token=aws_profile.aws_session_token,
            region=aws_profile.region or "ap-northeast-2",
        )
        return StaticCredentialsProvider(static_config)

    else:
        raise ValueError(f"지원하지 않는 Provider 타입: {provider_type}")


# =============================================================================
# Context 기반 세션 헬퍼 (Flow 통합)
# =============================================================================


class SessionIterator:
    """세션 순회 + 결과 추적 클래스

    성공/실패를 자동으로 추적하여 도구에서 에러 처리를 간소화합니다.
    iter_context_sessions와 달리 직접 순회하면서 에러를 추적합니다.

    Example:
        with SessionIterator(ctx) as sessions:
            for session, identifier, region in sessions:
                ec2 = session.client("ec2")
                # 작업 수행

        if sessions.has_failures_only():
            console.print("모든 조회 실패")
            console.print(sessions.get_error_summary())
        elif sessions.has_no_sessions():
            console.print("조회 가능한 계정 없음")

    Attributes:
        success_count: 성공한 세션 수
        error_count: 실패한 세션 수
        errors: 에러 목록 [(identifier, region, exception), ...]
    """

    def __init__(self, ctx: ExecutionContext):
        self._ctx = ctx
        self._success_count = 0
        self._error_count = 0
        self._errors: list[tuple[str, str, Exception]] = []

    def __enter__(self) -> SessionIterator:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def __iter__(self) -> Iterator[tuple[boto3.Session, str, str]]:
        """세션 순회 (에러 직접 추적)"""
        if self._ctx.is_sso_session():
            yield from self._iter_sso_sessions()
        elif self._ctx.is_multi_profile():
            yield from self._iter_multi_profile_sessions()
        else:
            yield from self._iter_single_profile_sessions()

    def _iter_sso_sessions(self) -> Iterator[tuple[boto3.Session, str, str]]:
        """SSO Session 순회 (에러 추적)"""
        target_accounts = self._ctx.get_target_accounts()
        provider = self._ctx.provider
        if provider is None:
            logger.warning("Provider가 설정되지 않았습니다")
            return

        for account in target_accounts:
            role_name = self._ctx.get_effective_role(account.id)
            if not role_name:
                logger.warning(f"계정 {account.id}에 사용할 역할이 없어 스킵")
                continue

            for region in self._ctx.regions:
                try:
                    session = provider.get_session(
                        account_id=account.id,
                        role_name=role_name,
                        region=region,
                    )
                    self._success_count += 1
                    yield session, account.id, region
                except Exception as e:
                    self._error_count += 1
                    self._errors.append((account.id, region, e))
                    logger.warning(f"세션 생성 실패 [{account.id}/{region}]: {e}")

    def _iter_multi_profile_sessions(self) -> Iterator[tuple[boto3.Session, str, str]]:
        """다중 프로파일 순회 (에러 추적)"""
        for profile in self._ctx.profiles:
            for region in self._ctx.regions:
                try:
                    session = get_session(profile, region)
                    self._success_count += 1
                    yield session, profile, region
                except Exception as e:
                    self._error_count += 1
                    self._errors.append((profile, region, e))
                    logger.warning(f"세션 생성 실패 [{profile}/{region}]: {e}")

    def _iter_single_profile_sessions(self) -> Iterator[tuple[boto3.Session, str, str]]:
        """단일 프로파일 순회 (에러 추적)"""
        profile = self._ctx.profile_name
        if not profile:
            logger.warning("프로파일이 설정되지 않았습니다")
            return

        for region in self._ctx.regions:
            try:
                session = get_session(profile, region)
                self._success_count += 1
                yield session, profile, region
            except Exception as e:
                self._error_count += 1
                self._errors.append((profile, region, e))
                logger.warning(f"세션 생성 실패 [{profile}/{region}]: {e}")

    @property
    def success_count(self) -> int:
        """성공한 세션 수"""
        return self._success_count

    @property
    def error_count(self) -> int:
        """실패한 세션 수"""
        return self._error_count

    @property
    def errors(self) -> list[tuple[str, str, Exception]]:
        """발생한 에러 목록 [(identifier, region, exception), ...]"""
        return self._errors

    def has_no_sessions(self) -> bool:
        """세션이 하나도 없는 경우 (선택된 계정/리전 없음)"""
        return self._success_count == 0 and self._error_count == 0

    def has_failures_only(self) -> bool:
        """모든 세션이 실패한 경우"""
        return self._success_count == 0 and self._error_count > 0

    def has_any_success(self) -> bool:
        """하나 이상 성공한 경우"""
        return self._success_count > 0

    def get_error_summary(self) -> str:
        """에러 요약 메시지 반환

        Returns:
            에러 요약 문자열 (없으면 빈 문자열)
        """
        if not self._errors:
            return ""

        lines = [f"총 {self._error_count}개 세션 생성 실패:"]
        for identifier, region, error in self._errors[:5]:  # 최대 5개만 표시
            lines.append(f"  - {identifier}/{region}: {error}")

        if len(self._errors) > 5:
            lines.append(f"  ... 외 {len(self._errors) - 5}개")

        return "\n".join(lines)


class ParallelSessionIterator:
    """병렬 세션 순회 클래스

    SessionIterator의 병렬 버전.
    기존 순차 패턴과 유사한 인터페이스를 제공하면서 내부적으로 병렬 처리합니다.

    기존 코드 (순차):
        with SessionIterator(ctx) as sessions:
            for session, identifier, region in sessions:
                result = collect(session, ...)
                all_results.append(result)

    신규 코드 (병렬, 권장):
        from core.parallel import parallel_collect

        result = parallel_collect(ctx, collect_func, max_workers=20)
        all_data = result.get_data()

    또는 기존 패턴 유지하면서 병렬화:
        with ParallelSessionIterator(ctx, max_workers=20) as parallel:
            result = parallel.map(collect_func, service="ec2")
            # result: ParallelExecutionResult
    """

    def __init__(
        self,
        ctx: ExecutionContext,
        max_workers: int = 20,
    ):
        """초기화

        Args:
            ctx: ExecutionContext
            max_workers: 최대 동시 스레드 수
        """
        from core.parallel import ParallelConfig, ParallelSessionExecutor

        self._ctx = ctx
        self._max_workers = max_workers
        self._executor = ParallelSessionExecutor(
            ctx,
            ParallelConfig(max_workers=max_workers),
        )

    def __enter__(self) -> ParallelSessionIterator:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def map(
        self,
        func: Callable[[boto3.Session, str, str, str], T],
        service: str = "default",
    ) -> ParallelExecutionResult[T]:
        """작업 함수를 모든 세션에 병렬 매핑

        Args:
            func: (session, account_id, account_name, region) -> T
            service: AWS 서비스 이름 (rate limiting용)

        Returns:
            ParallelExecutionResult[T]

        Example:
            def collect_volumes(session, account_id, account_name, region):
                ec2 = session.client("ec2", region_name=region)
                return ec2.describe_volumes()["Volumes"]

            with ParallelSessionIterator(ctx, max_workers=20) as parallel:
                result = parallel.map(collect_volumes, service="ec2")

                for volume in result.get_flat_data():
                    print(volume["VolumeId"])
        """
        return self._executor.execute(func, service)


def iter_context_sessions(
    ctx: ExecutionContext,
) -> Iterator[tuple[boto3.Session, str, str]]:
    """ExecutionContext 기반 세션 제너레이터

    Flow에서 선택된 정보를 기반으로 세션을 순회합니다.

    - SSO Session: 선택된 계정들 × 리전들
    - SSO Profile / Static: 프로파일 × 리전들

    Args:
        ctx: ExecutionContext (Flow 실행 결과)

    Yields:
        (session, identifier, region) 튜플
        - SSO Session: identifier = account_id
        - 그 외: identifier = profile_name

    Example:
        for session, identifier, region in iter_context_sessions(ctx):
            ec2 = session.client("ec2")
            print(f"Processing {identifier} in {region}")
    """
    if ctx.is_sso_session():
        # SSO Session: 멀티 계정 지원
        yield from _iter_sso_session_contexts(ctx)
    elif ctx.is_multi_profile():
        # Static: 다중 프로파일 지원
        yield from _iter_multi_profile_contexts(ctx)
    else:
        # SSO Profile: 단일 프로파일
        yield from _iter_single_profile_contexts(ctx)


def get_context_session(
    ctx: ExecutionContext,
    region: str,
    account_id: str | None = None,
) -> boto3.Session:
    """ExecutionContext 기반 단일 세션 획득

    Args:
        ctx: ExecutionContext
        region: AWS 리전
        account_id: 계정 ID (SSO Session에서 특정 계정 지정 시,
                    단일 계정 선택된 경우 생략 가능)

    Returns:
        boto3.Session
    """
    if ctx.is_sso_session():
        # account_id가 없으면 단일 계정인 경우 자동으로 추론
        if not account_id:
            target_accounts = ctx.get_target_accounts()
            if len(target_accounts) == 1:
                account_id = target_accounts[0].id
            else:
                raise ValueError("SSO Session에서 여러 계정이 선택된 경우 account_id를 명시해야 합니다")

        role_name = ctx.get_effective_role(account_id)
        if not role_name:
            raise ValueError(f"계정 {account_id}에 사용할 역할이 없습니다")

        provider = ctx.provider
        if provider is None:
            raise ValueError("Provider가 설정되지 않았습니다")

        return provider.get_session(
            account_id=account_id,
            role_name=role_name,
            region=region,
        )
    else:
        # SSO Profile / Static
        profile = ctx.profile_name
        if not profile:
            raise ValueError("프로파일이 설정되지 않았습니다")
        return get_session(profile, region)


def _iter_sso_session_contexts(
    ctx: ExecutionContext,
) -> Iterator[tuple[boto3.Session, str, str]]:
    """SSO Session 멀티 계정 순회"""
    target_accounts = ctx.get_target_accounts()
    provider = ctx.provider
    if provider is None:
        logger.warning("Provider가 설정되지 않았습니다")
        return

    for account in target_accounts:
        role_name = ctx.get_effective_role(account.id)
        if not role_name:
            logger.warning(f"계정 {account.id}에 사용할 역할이 없어 스킵")
            continue

        for region in ctx.regions:
            try:
                session = provider.get_session(
                    account_id=account.id,
                    role_name=role_name,
                    region=region,
                )
                yield session, account.id, region
            except Exception as e:
                logger.warning(f"세션 생성 실패 [{account.id}/{region}]: {e}")
                continue


def _iter_multi_profile_contexts(
    ctx: ExecutionContext,
) -> Iterator[tuple[boto3.Session, str, str]]:
    """다중 프로파일 순회 (Static)"""
    for profile in ctx.profiles:
        for region in ctx.regions:
            try:
                session = get_session(profile, region)
                yield session, profile, region
            except Exception as e:
                logger.warning(f"세션 생성 실패 [{profile}/{region}]: {e}")
                continue


def _iter_single_profile_contexts(
    ctx: ExecutionContext,
) -> Iterator[tuple[boto3.Session, str, str]]:
    """단일 프로파일 순회 (SSO Profile)"""
    profile = ctx.profile_name
    if not profile:
        logger.warning("프로파일이 설정되지 않았습니다")
        return

    for region in ctx.regions:
        try:
            session = get_session(profile, region)
            yield session, profile, region
        except Exception as e:
            logger.warning(f"세션 생성 실패 [{profile}/{region}]: {e}")
            continue


# =============================================================================
# Context 정보 조회 (배너 표시용)
# =============================================================================


def get_current_context_info() -> dict[str, str] | None:
    """현재 AWS 컨텍스트 정보 반환 (배너 표시용)

    환경 변수 또는 AWS 설정 파일에서 현재 프로파일을 감지하고,
    해당 프로파일의 인증 방식에 따라 mode를 결정합니다.

    Returns:
        {
            "mode": "multi" | "single",
            "profile": "프로파일명",
            "provider_type": "sso_session" | "sso_profile" | "static" | ...
        }
        또는 프로파일을 찾을 수 없으면 None

    Example:
        >>> info = get_current_context_info()
        >>> if info:
        ...     print(f"Mode: {info['mode']}, Profile: {info['profile']}")
    """
    import os

    try:
        # 1. 환경 변수에서 프로파일 확인
        profile_name = os.environ.get("AWS_PROFILE") or os.environ.get("AWS_DEFAULT_PROFILE")

        # 2. AWS 설정에서 기본 프로파일 확인
        loader = Loader()
        config = loader.load()

        if not profile_name:
            profile_name = config.default_profile

        if not profile_name or profile_name not in config.profiles:
            return None

        # 3. Provider 타입 감지
        profile = config.profiles[profile_name]
        provider_type = detect_provider_type(profile)

        # Provider 타입을 감지할 수 없는 경우
        if provider_type is None:
            return None

        # 4. Mode 결정
        # SSO Session (sso_session만 참조, account/role 미지정) = multi
        # 나머지 = single
        mode = "multi" if provider_type == ProviderType.SSO_SESSION else "single"

        return {
            "mode": mode,
            "profile": profile_name,
            "provider_type": provider_type.value,
        }

    except Exception as e:
        logger.debug(f"컨텍스트 정보 조회 실패: {e}")
        return None
