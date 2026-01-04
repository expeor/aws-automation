"""
core/parallel/executor.py - 병렬 세션 실행기

Map-Reduce 패턴으로 멀티 계정/리전 작업을 병렬 처리합니다.
ThreadPoolExecutor 기반이며, Rate limiting과 재시도를 지원합니다.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from .decorators import RetryConfig, categorize_error, get_error_code, is_retryable
from .quiet import is_quiet, set_quiet
from .rate_limiter import RateLimiterConfig, TokenBucketRateLimiter
from .types import ErrorCategory, ParallelExecutionResult, TaskError, TaskResult

if TYPE_CHECKING:
    import boto3

    from cli.flow.context import ExecutionContext

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ParallelConfig:
    """병렬 실행 설정

    Attributes:
        max_workers: 최대 동시 스레드 수
        retry_config: 재시도 설정
        rate_limiter_config: Rate limiter 설정
    """

    max_workers: int = 20
    retry_config: RetryConfig | None = None
    rate_limiter_config: RateLimiterConfig | None = None


@dataclass
class _TaskSpec:
    """내부 작업 명세"""

    account_id: str
    account_name: str
    region: str
    session_getter: Callable[[], boto3.Session]


class ParallelSessionExecutor:
    """병렬 세션 실행기

    Map-Reduce 패턴으로 멀티 계정/리전 작업을 병렬 처리합니다.

    특징:
    - ThreadPoolExecutor 기반 병렬 처리
    - Rate limiting으로 쓰로틀링 방지
    - 지수 백오프 재시도
    - 구조화된 결과 수집 (Map-Reduce)

    Example:
        def collect_volumes(session, account_id, account_name, region):
            ec2 = session.client("ec2", region_name=region)
            volumes = ec2.describe_volumes()["Volumes"]
            return [parse_volume(v) for v in volumes]

        executor = ParallelSessionExecutor(ctx, ParallelConfig(max_workers=20))
        result = executor.execute(collect_volumes, service="ec2")

        # 결과 처리
        all_volumes = result.get_flat_data()
        print(f"수집: {result.success_count}, 실패: {result.error_count}")
    """

    def __init__(
        self,
        ctx: ExecutionContext,
        config: ParallelConfig | None = None,
    ):
        """초기화

        Args:
            ctx: 실행 컨텍스트
            config: 병렬 실행 설정 (None이면 기본값)
        """
        self.ctx = ctx
        self.config = config or ParallelConfig()

        # Rate Limiter 초기화
        limiter_config = self.config.rate_limiter_config or RateLimiterConfig()
        self._rate_limiter = TokenBucketRateLimiter(limiter_config)

        # 재시도 설정
        self._retry_config = self.config.retry_config or RetryConfig()

    def execute(
        self,
        func: Callable[[boto3.Session, str, str, str], T],
        service: str = "default",
    ) -> ParallelExecutionResult[T]:
        """작업 함수를 모든 세션에 병렬 실행

        Args:
            func: (session, account_id, account_name, region) -> T 함수
            service: AWS 서비스 이름 (rate limit용, 로깅용)

        Returns:
            ParallelExecutionResult[T]: 전체 실행 결과
        """
        # 작업 목록 생성
        tasks = self._build_task_list()

        if not tasks:
            logger.warning("실행할 작업이 없습니다")
            return ParallelExecutionResult()

        logger.info(f"병렬 실행 시작: {len(tasks)}개 작업, max_workers={self.config.max_workers}, service={service}")

        results: list[TaskResult[T]] = []
        start_time = time.monotonic()

        # 부모 스레드의 quiet 상태를 저장하여 워커 스레드에 전파
        parent_quiet = is_quiet()

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # 모든 작업 제출 (quiet 상태 전파)
            futures = {}
            for task in tasks:
                future = executor.submit(
                    self._execute_single,
                    func,
                    task,
                    service,
                    parent_quiet,
                )
                futures[future] = task

            # 완료된 작업 수집
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # 예상치 못한 executor 에러
                    logger.error(f"작업 실행 중 예외 [{task.account_id}/{task.region}]: {e}")
                    results.append(
                        TaskResult(
                            identifier=task.account_id,
                            region=task.region,
                            success=False,
                            error=TaskError(
                                identifier=task.account_id,
                                region=task.region,
                                category=ErrorCategory.UNKNOWN,
                                error_code="ExecutorError",
                                message=str(e),
                                original_exception=e,
                            ),
                        )
                    )

        total_time = (time.monotonic() - start_time) * 1000
        exec_result = ParallelExecutionResult(results=results)

        logger.info(
            f"병렬 실행 완료: 성공 {exec_result.success_count}, 실패 {exec_result.error_count}, 총 {total_time:.0f}ms"
        )

        return exec_result

    def _build_task_list(self) -> list[_TaskSpec]:
        """실행할 작업 목록 생성"""
        tasks: list[_TaskSpec] = []

        if self.ctx.is_sso_session():
            tasks = self._build_sso_tasks()
        elif self.ctx.is_multi_profile():
            tasks = self._build_multi_profile_tasks()
        else:
            tasks = self._build_single_profile_tasks()

        return tasks

    def _build_sso_tasks(self) -> list[_TaskSpec]:
        """SSO Session 기반 작업 목록"""
        tasks: list[_TaskSpec] = []
        target_accounts = self.ctx.get_target_accounts()

        for account in target_accounts:
            role_name = self.ctx.get_effective_role(account.id)
            if not role_name:
                logger.warning(f"계정 {account.id}에 사용할 역할이 없어 스킵")
                continue

            for region in self.ctx.regions:
                # 클로저 캡처를 위해 기본 인자 사용
                def make_session_getter(acc_id=account.id, rn=role_name, reg=region):
                    return lambda: self.ctx.provider.get_session(
                        account_id=acc_id,
                        role_name=rn,
                        region=reg,
                    )

                tasks.append(
                    _TaskSpec(
                        account_id=account.id,
                        account_name=account.name,
                        region=region,
                        session_getter=make_session_getter(),
                    )
                )

        return tasks

    def _build_multi_profile_tasks(self) -> list[_TaskSpec]:
        """다중 프로파일 기반 작업 목록"""
        from core.auth.session import get_session

        tasks: list[_TaskSpec] = []

        for profile in self.ctx.profiles:
            for region in self.ctx.regions:

                def make_session_getter(p=profile, r=region):
                    return lambda: get_session(p, r)

                tasks.append(
                    _TaskSpec(
                        account_id=profile,
                        account_name=profile,
                        region=region,
                        session_getter=make_session_getter(),
                    )
                )

        return tasks

    def _build_single_profile_tasks(self) -> list[_TaskSpec]:
        """단일 프로파일 기반 작업 목록"""
        from core.auth.session import get_session

        tasks: list[_TaskSpec] = []
        profile = self.ctx.profile_name or "default"

        for region in self.ctx.regions:

            def make_session_getter(r=region):
                return lambda: get_session(profile, r)

            tasks.append(
                _TaskSpec(
                    account_id=profile,
                    account_name=profile,
                    region=region,
                    session_getter=make_session_getter(),
                )
            )

        return tasks

    def _execute_single(
        self,
        func: Callable[[boto3.Session, str, str, str], T],
        task: _TaskSpec,
        service: str,
        quiet: bool = False,
    ) -> TaskResult[T]:
        """단일 작업 실행 (스레드 내에서)"""
        # 워커 스레드에 quiet 상태 전파
        set_quiet(quiet)
        start_time = time.monotonic()

        try:
            # Rate limiting
            if not self._rate_limiter.acquire():
                return TaskResult(
                    identifier=task.account_id,
                    region=task.region,
                    success=False,
                    error=TaskError(
                        identifier=task.account_id,
                        region=task.region,
                        category=ErrorCategory.THROTTLING,
                        error_code="RateLimitTimeout",
                        message="Rate limiter timeout",
                    ),
                    duration_ms=(time.monotonic() - start_time) * 1000,
                )

            # 세션 획득
            session = task.session_getter()

            # 작업 실행 (재시도 포함)
            return self._execute_with_retry(func, session, task, service, start_time)

        except Exception as e:
            # 세션 획득 실패 등
            return TaskResult(
                identifier=task.account_id,
                region=task.region,
                success=False,
                error=TaskError(
                    identifier=task.account_id,
                    region=task.region,
                    category=categorize_error(e),
                    error_code=get_error_code(e),
                    message=str(e),
                    original_exception=e,
                ),
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    def _execute_with_retry(
        self,
        func: Callable[[boto3.Session, str, str, str], T],
        session: boto3.Session,
        task: _TaskSpec,
        service: str,
        start_time: float,
    ) -> TaskResult[T]:
        """재시도 로직을 포함한 작업 실행"""
        last_error: Exception | None = None

        for attempt in range(self._retry_config.max_retries + 1):
            try:
                data = func(session, task.account_id, task.account_name, task.region)
                return TaskResult(
                    identifier=task.account_id,
                    region=task.region,
                    success=True,
                    data=data,
                    duration_ms=(time.monotonic() - start_time) * 1000,
                )

            except Exception as e:
                last_error = e

                # 재시도 가능 여부 확인
                if not is_retryable(e) or attempt >= self._retry_config.max_retries:
                    return TaskResult(
                        identifier=task.account_id,
                        region=task.region,
                        success=False,
                        error=TaskError(
                            identifier=task.account_id,
                            region=task.region,
                            category=categorize_error(e),
                            error_code=get_error_code(e),
                            message=str(e),
                            retries=attempt,
                            original_exception=e,
                        ),
                        duration_ms=(time.monotonic() - start_time) * 1000,
                    )

                # 재시도 대기
                delay = self._retry_config.get_delay(attempt)
                logger.debug(f"[{task.account_id}/{task.region}] 시도 {attempt + 1} 실패, {delay:.2f}초 후 재시도...")
                time.sleep(delay)

        # 재시도 소진 (도달하면 안 됨)
        return TaskResult(
            identifier=task.account_id,
            region=task.region,
            success=False,
            error=TaskError(
                identifier=task.account_id,
                region=task.region,
                category=(categorize_error(last_error) if last_error else ErrorCategory.UNKNOWN),
                error_code=get_error_code(last_error) if last_error else "Unknown",
                message="최대 재시도 횟수 초과",
                retries=self._retry_config.max_retries,
                original_exception=last_error,
            ),
            duration_ms=(time.monotonic() - start_time) * 1000,
        )


def parallel_collect(
    ctx: ExecutionContext,
    collector_func: Callable[[boto3.Session, str, str, str], T],
    max_workers: int = 20,
    service: str = "default",
) -> ParallelExecutionResult[T]:
    """병렬 수집 편의 함수

    ParallelSessionExecutor를 간단하게 사용할 수 있는 래퍼입니다.

    Args:
        ctx: ExecutionContext
        collector_func: (session, account_id, account_name, region) -> T
        max_workers: 최대 동시 스레드 수
        service: AWS 서비스 이름

    Returns:
        ParallelExecutionResult[T]

    Example:
        def collect_sgs(session, account_id, account_name, region):
            ec2 = session.client("ec2", region_name=region)
            return ec2.describe_security_groups()["SecurityGroups"]

        result = parallel_collect(ctx, collect_sgs, max_workers=20, service="ec2")

        all_sgs = result.get_flat_data()
        print(f"총 {len(all_sgs)}개 보안그룹 수집")

        if result.error_count > 0:
            print(result.get_error_summary())
    """
    config = ParallelConfig(max_workers=max_workers)
    executor = ParallelSessionExecutor(ctx, config)
    return executor.execute(collector_func, service)
