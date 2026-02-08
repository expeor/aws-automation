"""
core/parallel/executor.py - 병렬 세션 실행기

Map-Reduce 패턴으로 멀티 계정/리전 AWS 작업을 병렬 처리합니다.
ThreadPoolExecutor 기반이며, Rate limiting과 지수 백오프 재시도를 지원합니다.

주요 구성 요소:
- ParallelConfig: 병렬 실행 설정 (워커 수, 재시도, Rate limit)
- ParallelSessionExecutor: 멀티 계정/리전 병렬 실행기
- parallel_collect: 간편한 병렬 수집 래퍼 함수

Example:
    from core.parallel import parallel_collect

    def collect_volumes(session, account_id, account_name, region):
        ec2 = session.client("ec2", region_name=region)
        return ec2.describe_volumes()["Volumes"]

    result = parallel_collect(ctx, collect_volumes, service="ec2")
    all_volumes = result.get_flat_data()
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

    from core.cli.flow.context import ExecutionContext
    from core.cli.ui.progress import ParallelTracker

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _clear_exception_chain(e: BaseException) -> None:
    """traceback + chained exception 메모리 누수 방지"""
    e.__traceback__ = None
    if e.__context__ is not None:
        e.__context__.__traceback__ = None
    if e.__cause__ is not None:
        e.__cause__.__traceback__ = None


@dataclass
class ParallelConfig:
    """병렬 실행 설정

    Attributes:
        max_workers: 최대 동시 스레드 수 (1~100)
        retry_config: 재시도 설정
        rate_limiter_config: Rate limiter 설정
    """

    max_workers: int = 20
    retry_config: RetryConfig | None = None
    rate_limiter_config: RateLimiterConfig | None = None

    def __post_init__(self) -> None:
        if self.max_workers < 1:
            raise ValueError(f"max_workers must be >= 1, got {self.max_workers}")
        if self.max_workers > 100:
            self.max_workers = 100


@dataclass
class _TaskSpec:
    """내부 작업 명세

    병렬 실행할 개별 작업의 정보를 담습니다.

    Attributes:
        account_id: AWS 계정 ID 또는 프로파일명
        account_name: AWS 계정 이름 또는 프로파일명
        region: 대상 AWS 리전
        session_getter: boto3 Session을 반환하는 지연 팩토리 함수
    """

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

        # 재시도 설정
        self._retry_config = self.config.retry_config or RetryConfig()

    def execute(
        self,
        func: Callable[[boto3.Session, str, str, str], T],
        service: str = "default",
        progress_tracker: ParallelTracker | None = None,
    ) -> ParallelExecutionResult[T]:
        """작업 함수를 모든 세션에 병렬 실행

        Args:
            func: (session, account_id, account_name, region) -> T 함수
            service: AWS 서비스 이름 (rate limit용, 로깅용)
            progress_tracker: 진행 상황 추적기 (선택사항).
                전달 시 자동으로:
                1. set_total(task_count) 호출
                2. 각 task 완료 시 on_complete(success) 호출

        Returns:
            ParallelExecutionResult[T]: 전체 실행 결과
        """
        # 작업 목록 생성
        tasks = self._build_task_list()

        if not tasks:
            logger.warning("실행할 작업이 없습니다")
            return ParallelExecutionResult()

        logger.info(f"병렬 실행 시작: {len(tasks)}개 작업, max_workers={self.config.max_workers}, service={service}")

        # progress_tracker에 total 설정
        if progress_tracker:
            progress_tracker.set_total(len(tasks))

        results: list[TaskResult[T]] = []
        start_time = time.monotonic()

        # 부모 스레드의 quiet 상태를 저장하여 워커 스레드에 전파
        parent_quiet = is_quiet()

        # 서비스별 rate limiter 사용
        from .rate_limiter import get_rate_limiter

        rate_limiter = get_rate_limiter(service)

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
                    rate_limiter,
                )
                futures[future] = task

            # 완료된 작업 수집
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                    results.append(result)

                    # progress_tracker에 완료 알림
                    if progress_tracker:
                        progress_tracker.on_complete(result.success)
                except Exception as e:
                    # 예상치 못한 executor 에러
                    logger.error(f"작업 실행 중 예외 [{task.account_id}/{task.region}]: {e}")
                    _clear_exception_chain(e)
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

                    # progress_tracker에 실패 알림
                    if progress_tracker:
                        progress_tracker.on_complete(success=False)

        total_time = (time.monotonic() - start_time) * 1000
        exec_result = ParallelExecutionResult(results=tuple(results))

        logger.info(
            f"병렬 실행 완료: 성공 {exec_result.success_count}, 실패 {exec_result.error_count}, 총 {total_time:.0f}ms"
        )

        return exec_result

    def _build_task_list(self) -> list[_TaskSpec]:
        """컨텍스트 유형에 따라 실행할 작업 목록 생성

        SSO Session, 다중 프로파일, 단일 프로파일 중
        현재 ExecutionContext의 인증 모드를 감지하여 적절한 작업 목록을 구성합니다.

        Returns:
            _TaskSpec 리스트 (계정 x 리전 조합)
        """
        tasks: list[_TaskSpec] = []

        if self.ctx.is_sso_session():
            tasks = self._build_sso_tasks()
        elif self.ctx.is_multi_profile():
            tasks = self._build_multi_profile_tasks()
        else:
            tasks = self._build_single_profile_tasks()

        return tasks

    def _build_sso_tasks(self) -> list[_TaskSpec]:
        """SSO Session 기반 작업 목록 생성

        대상 계정별 역할(role)과 리전 조합으로 작업 목록을 구성합니다.
        역할이 없는 계정은 스킵합니다.

        Returns:
            _TaskSpec 리스트
        """
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
        """다중 프로파일 기반 작업 목록 생성

        각 프로파일과 리전의 조합으로 작업 목록을 구성합니다.

        Returns:
            _TaskSpec 리스트
        """
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
        """단일 프로파일 기반 작업 목록 생성

        하나의 프로파일에 대해 각 리전별 작업 목록을 구성합니다.

        Returns:
            _TaskSpec 리스트
        """
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
        rate_limiter: TokenBucketRateLimiter | None = None,
    ) -> TaskResult[T]:
        """단일 작업 실행 (워커 스레드 내에서 호출)

        Rate limiting 적용 후 세션을 획득하고 재시도 로직을 포함하여
        작업 함수를 실행합니다. 부모 스레드의 quiet 상태를 전파합니다.

        Args:
            func: (session, account_id, account_name, region) -> T 콜백 함수
            task: 실행할 작업 명세
            service: AWS 서비스 이름 (로깅용)
            quiet: quiet 모드 여부 (부모 스레드에서 전파)
            rate_limiter: 서비스별 Rate limiter

        Returns:
            TaskResult[T]: 성공 시 데이터, 실패 시 에러 정보 포함
        """
        # 워커 스레드에 quiet 상태 전파
        set_quiet(quiet)
        start_time = time.monotonic()

        try:
            # Rate limiting (서비스별 limiter 사용)
            if rate_limiter and not rate_limiter.acquire():
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
            _clear_exception_chain(e)
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
        """지수 백오프 재시도 로직을 포함한 작업 실행

        재시도 가능한 에러(throttling, network 등) 발생 시 RetryConfig에 따라
        지수 백오프로 재시도하고, 재시도 불가능한 에러는 즉시 반환합니다.

        Args:
            func: (session, account_id, account_name, region) -> T 콜백 함수
            session: boto3 Session
            task: 실행할 작업 명세
            service: AWS 서비스 이름 (로깅용)
            start_time: 작업 시작 시각 (monotonic, duration 계산용)

        Returns:
            TaskResult[T]: 성공 또는 실패 결과
        """
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
                    _clear_exception_chain(e)
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
        if last_error is not None:
            _clear_exception_chain(last_error)
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
    progress_tracker: ParallelTracker | None = None,
) -> ParallelExecutionResult[T]:
    """병렬 수집 편의 함수

    ParallelSessionExecutor를 간단하게 사용할 수 있는 래퍼입니다.

    Args:
        ctx: ExecutionContext
        collector_func: (session, account_id, account_name, region) -> T
        max_workers: 최대 동시 스레드 수
        service: AWS 서비스 이름
        progress_tracker: 진행 상황 추적기 (선택사항).
            전달 시 자동으로:
            1. set_total(task_count) 호출
            2. 각 task 완료 시 on_complete(success) 호출
            ctx에 timeline이 있으면 자동으로 TimelineParallelTracker 생성.

    Returns:
        ParallelExecutionResult[T]

    Example (기본 사용):
        def collect_sgs(session, account_id, account_name, region):
            ec2 = session.client("ec2", region_name=region)
            return ec2.describe_security_groups()["SecurityGroups"]

        result = parallel_collect(ctx, collect_sgs, max_workers=20, service="ec2")

        all_sgs = result.get_flat_data()
        print(f"총 {len(all_sgs)}개 보안그룹 수집")

        if result.error_count > 0:
            print(result.get_error_summary())

    Example (progress_tracker 사용):
        from core.cli.ui import parallel_progress

        with parallel_progress("리소스 수집") as tracker:
            with quiet_mode():
                result = parallel_collect(
                    ctx, collect_sgs, progress_tracker=tracker
                )

        success, failed, total = tracker.stats
        console.print(f"완료: {success}개 성공, {failed}개 실패")
    """
    # progress_tracker가 없고 ctx에 timeline이 있으면 자동 생성
    _auto_timeline = False
    if progress_tracker is None:
        timeline = getattr(ctx, "_timeline", None)
        if timeline is not None:
            collect_phase = getattr(ctx, "_timeline_collect_phase", 0)
            progress_tracker = timeline.create_parallel_tracker(collect_phase)
            _auto_timeline = True

    config = ParallelConfig(max_workers=max_workers)
    executor = ParallelSessionExecutor(ctx, config)
    result = executor.execute(collector_func, service, progress_tracker=progress_tracker)

    # 자동 생성된 timeline tracker인 경우, 수집 phase 완료 후 Live를 중단하여
    # 이후 도구의 console.print() 출력이 Live 렌더링과 겹치지 않도록 함
    if _auto_timeline:
        timeline = getattr(ctx, "_timeline", None)
        if timeline is not None:
            collect_phase = getattr(ctx, "_timeline_collect_phase", 0)
            timeline.complete_phase(collect_phase)
            timeline.stop()

    return result
