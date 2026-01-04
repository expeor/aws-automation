"""
core/parallel/quiet.py - 병렬 실행 시 콘솔 출력 억제

병렬 처리 중 여러 스레드에서 동시에 콘솔 출력이 발생하면
Progress bar와 섞여서 지저분해집니다.

이 모듈은 병렬 실행 시 콘솔 출력을 억제하는 기능을 제공합니다.

Example:
    from core.parallel.quiet import quiet_mode, is_quiet

    # 병렬 실행 시
    with quiet_mode():
        parallel_collect(ctx, collector_func)

    # 개별 함수에서 확인
    if not is_quiet():
        console.print("메시지")
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Generator
from contextlib import contextmanager

# 스레드-로컬 저장소로 quiet 상태 관리
_quiet_state = threading.local()


def is_quiet() -> bool:
    """현재 스레드가 quiet 모드인지 확인

    Returns:
        True이면 콘솔 출력을 억제해야 함
    """
    return getattr(_quiet_state, "quiet", False)


def set_quiet(value: bool) -> None:
    """현재 스레드의 quiet 모드 설정"""
    _quiet_state.quiet = value


@contextmanager
def quiet_mode() -> Generator[None, None, None]:
    """병렬 실행 시 콘솔 출력을 억제하는 컨텍스트 매니저

    이 컨텍스트 안에서 실행되는 코드는 is_quiet() == True가 됩니다.
    개별 함수에서 is_quiet()를 확인하여 출력을 조건부로 수행할 수 있습니다.

    또한 logging WARNING 레벨 이하의 로그도 억제됩니다.
    (루트 로거의 레벨을 ERROR로 변경하여 모든 자식 로거에 적용)

    Example:
        with quiet_mode():
            # 이 블록 안에서 is_quiet() == True
            parallel_collect(ctx, collector_func)
    """
    # quiet 모드 설정
    old_value = getattr(_quiet_state, "quiet", False)
    _quiet_state.quiet = True

    # 루트 로거의 레벨을 ERROR로 변경 (WARNING 이하 억제)
    root_logger = logging.getLogger()
    old_level = root_logger.level
    root_logger.setLevel(logging.ERROR)

    try:
        yield
    finally:
        # 원래 상태로 복원
        _quiet_state.quiet = old_value
        root_logger.setLevel(old_level)


# 모든 스레드에서 상태를 상속받도록 하는 헬퍼
def inherit_quiet_state() -> bool:
    """부모 스레드의 quiet 상태를 반환 (ThreadPoolExecutor에서 사용)"""
    return is_quiet()
