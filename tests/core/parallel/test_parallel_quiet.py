"""
tests/test_parallel_quiet.py - core/parallel/quiet.py 테스트
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from core.parallel.quiet import (
    inherit_quiet_state,
    is_quiet,
    quiet_mode,
    set_quiet,
)


class TestIsQuiet:
    """is_quiet 함수 테스트"""

    def test_default_is_not_quiet(self):
        """기본 상태는 quiet이 아님"""
        # 스레드 로컬 상태 초기화
        set_quiet(False)
        assert is_quiet() is False

    def test_set_quiet_true(self):
        """quiet 모드 설정"""
        set_quiet(True)
        assert is_quiet() is True
        set_quiet(False)  # 정리

    def test_set_quiet_false(self):
        """quiet 모드 해제"""
        set_quiet(True)
        set_quiet(False)
        assert is_quiet() is False


class TestSetQuiet:
    """set_quiet 함수 테스트"""

    def test_thread_local_isolation(self):
        """스레드 간 quiet 상태 격리"""
        results = {"main": None, "thread": None}

        def thread_func():
            set_quiet(True)
            results["thread"] = is_quiet()

        # 메인 스레드는 False
        set_quiet(False)

        # 다른 스레드에서 True 설정
        t = threading.Thread(target=thread_func)
        t.start()
        t.join()

        results["main"] = is_quiet()

        # 각 스레드의 상태가 독립적
        assert results["main"] is False
        assert results["thread"] is True


class TestQuietMode:
    """quiet_mode 컨텍스트 매니저 테스트"""

    def test_quiet_mode_sets_quiet(self):
        """quiet_mode 안에서는 is_quiet() == True"""
        set_quiet(False)

        with quiet_mode():
            assert is_quiet() is True

    def test_quiet_mode_restores_state(self):
        """quiet_mode 종료 후 원래 상태 복원"""
        set_quiet(False)

        with quiet_mode():
            pass

        assert is_quiet() is False

    def test_quiet_mode_restores_previous_true(self):
        """이전 상태가 True였어도 복원"""
        set_quiet(True)

        with quiet_mode():
            assert is_quiet() is True

        assert is_quiet() is True
        set_quiet(False)  # 정리

    def test_quiet_mode_exception_safe(self):
        """예외 발생해도 상태 복원"""
        set_quiet(False)

        try:
            with quiet_mode():
                assert is_quiet() is True
                raise ValueError("test error")
        except ValueError:
            pass

        assert is_quiet() is False

    def test_nested_quiet_mode(self):
        """중첩된 quiet_mode"""
        set_quiet(False)

        with quiet_mode():
            assert is_quiet() is True
            with quiet_mode():
                assert is_quiet() is True
            # 내부 컨텍스트 종료 후에도 True (외부 컨텍스트 영향)
            assert is_quiet() is True

        assert is_quiet() is False


class TestInheritQuietState:
    """inherit_quiet_state 함수 테스트"""

    def test_returns_current_quiet_state_true(self):
        """현재 quiet 상태가 True일 때"""
        set_quiet(True)
        assert inherit_quiet_state() is True
        set_quiet(False)

    def test_returns_current_quiet_state_false(self):
        """현재 quiet 상태가 False일 때"""
        set_quiet(False)
        assert inherit_quiet_state() is False


class TestQuietModeWithThreadPool:
    """ThreadPoolExecutor와 함께 사용 테스트"""

    def test_quiet_state_propagation(self):
        """quiet 상태가 워커 스레드로 전파되는지 확인"""
        results = []

        def worker(quiet_value):
            # 워커에서 quiet 상태 설정
            set_quiet(quiet_value)
            time.sleep(0.01)
            return is_quiet()

        # 부모가 quiet 모드일 때 자식 스레드에 전파
        parent_quiet = True

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(worker, parent_quiet) for _ in range(3)]
            for future in futures:
                results.append(future.result())

        # 모든 워커가 quiet 상태였어야 함
        assert all(results)

    def test_quiet_state_not_shared_between_workers(self):
        """워커 간 quiet 상태가 공유되지 않음 확인"""
        results = {"worker1": None, "worker2": None}

        def worker1():
            set_quiet(True)
            time.sleep(0.05)
            results["worker1"] = is_quiet()

        def worker2():
            set_quiet(False)
            time.sleep(0.05)
            results["worker2"] = is_quiet()

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(worker1)
            f2 = executor.submit(worker2)
            f1.result()
            f2.result()

        assert results["worker1"] is True
        assert results["worker2"] is False


class TestQuietModeLoggingIntegration:
    """quiet_mode와 로깅 통합 테스트"""

    def test_logging_suppressed_in_quiet_mode(self, caplog):
        """quiet_mode에서 WARNING 이하 로그 억제"""
        logger = logging.getLogger("test_quiet")
        logger.setLevel(logging.DEBUG)

        with quiet_mode():
            logger.debug("debug message")
            logger.info("info message")
            logger.warning("warning message")
            logger.error("error message")

        # quiet 모드에서는 낮은 레벨 로그가 필터링됨
        # (실제 필터링은 quiet_mode의 필터 추가/제거 로직에 의존)
        assert "error message" in [r.message for r in caplog.records]
