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

# filter 참조 카운팅 (concurrent quiet_mode 안전성)
_filter_refcount = 0
_filter_lock = threading.Lock()


class _QuietFilter(logging.Filter):
    """스레드별 quiet 상태에 따라 WARNING 이하 로그를 필터링

    quiet 모드가 활성화된 스레드에서는 ERROR 미만의 로그 레코드를
    차단하여 병렬 실행 중 불필요한 콘솔 출력을 방지합니다.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """로그 레코드 필터링"""
        return not (is_quiet() and record.levelno < logging.ERROR)


_quiet_filter = _QuietFilter()


def is_quiet() -> bool:
    """현재 스레드가 quiet 모드인지 확인

    Returns:
        True이면 콘솔 출력을 억제해야 함
    """
    return getattr(_quiet_state, "quiet", False)


def set_quiet(value: bool) -> None:
    """현재 스레드의 quiet 모드 설정

    Args:
        value: True이면 quiet 모드 활성화, False이면 비활성화
    """
    _quiet_state.quiet = value


@contextmanager
def quiet_mode() -> Generator[None, None, None]:
    """병렬 실행 시 콘솔 출력을 억제하는 컨텍스트 매니저

    이 컨텍스트 안에서 실행되는 코드는 is_quiet() == True가 됩니다.
    개별 함수에서 is_quiet()를 확인하여 출력을 조건부로 수행할 수 있습니다.

    WARNING 이하의 로그는 스레드별 Filter로 억제됩니다.
    (글로벌 로거 레벨 변경 대신 Filter를 사용하여 스레드 안전성 확보)

    참조 카운팅을 사용하여 concurrent quiet_mode() 진입 시
    한쪽이 exit해도 다른 쪽의 filter가 제거되지 않습니다.

    Example:
        with quiet_mode():
            # 이 블록 안에서 is_quiet() == True
            parallel_collect(ctx, collector_func)
    """
    global _filter_refcount

    old_value = getattr(_quiet_state, "quiet", False)
    _quiet_state.quiet = True

    root_logger = logging.getLogger()
    with _filter_lock:
        _filter_refcount += 1
        if _filter_refcount == 1:
            root_logger.addFilter(_quiet_filter)

    try:
        yield
    finally:
        _quiet_state.quiet = old_value
        with _filter_lock:
            _filter_refcount -= 1
            if _filter_refcount == 0:
                root_logger.removeFilter(_quiet_filter)
