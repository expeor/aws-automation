"""
tests/core/tools/test_datadog_client.py - Datadog 클라이언트 테스트
"""

from unittest.mock import MagicMock, patch

import pytest

# Skip all tests if datadog_api_client is not installed
pytest.importorskip("datadog_api_client")


class TestDatadogClientManager:
    """DatadogClientManager 클래스 테스트"""

    def test_initialization(self):
        """초기화 테스트"""
        from core.tools.datadog_client import DatadogClientManager

        api_keys = {"prod": {"api_key": "test_key", "app_key": "test_app"}}
        manager = DatadogClientManager(api_keys)

        assert manager._api_keys == api_keys
        assert manager._api_clients == {}
        assert manager._validated_envs == set()
        assert manager._invalid_envs == set()

    def test_empty_api_keys(self):
        """빈 API 키로 초기화"""
        from core.tools.datadog_client import DatadogClientManager

        manager = DatadogClientManager({})
        assert manager._api_keys == {}

    @patch("core.tools.datadog_client.DatadogClientManager._validate_and_create_client")
    def test_get_client_valid(self, mock_validate):
        """유효한 클라이언트 반환"""
        from core.tools.datadog_client import DatadogClientManager

        mock_api_client = MagicMock()
        mock_validate.return_value = mock_api_client

        api_keys = {"prod": {"api_key": "key", "app_key": "app"}}
        manager = DatadogClientManager(api_keys)

        with (
            patch("datadog_api_client.v2.api.events_api.EventsApi") as mock_events,
            patch("datadog_api_client.v1.api.metrics_api.MetricsApi") as mock_metrics,
        ):
            result = manager.get_client("prod")

            assert result is not None
            assert "events" in result
            assert "metrics" in result

    def test_get_client_unknown_env(self):
        """알 수 없는 환경 요청"""
        from core.tools.datadog_client import DatadogClientManager

        manager = DatadogClientManager({"prod": {"api_key": "k", "app_key": "a"}})
        result = manager.get_client("unknown")

        assert result is None

    def test_get_client_specific_api_types(self):
        """특정 API 타입만 요청"""
        from core.tools.datadog_client import DatadogClientManager

        with patch.object(DatadogClientManager, "_validate_and_create_client") as mock_validate:
            mock_api_client = MagicMock()
            mock_validate.return_value = mock_api_client

            manager = DatadogClientManager({"prod": {"api_key": "k", "app_key": "a"}})

            with patch("datadog_api_client.v2.api.events_api.EventsApi"):
                result = manager.get_client("prod", api_types={"events"})

                assert result is not None
                assert "events" in result
                assert "metrics" not in result

    def test_valid_envs_property(self):
        """유효한 환경 목록 프로퍼티"""
        from core.tools.datadog_client import DatadogClientManager

        manager = DatadogClientManager({})
        manager._validated_envs.add("prod")

        assert "prod" in manager.valid_envs

    def test_invalid_envs_property(self):
        """유효하지 않은 환경 목록 프로퍼티"""
        from core.tools.datadog_client import DatadogClientManager

        manager = DatadogClientManager({})
        manager._invalid_envs.add("bad_env")

        assert "bad_env" in manager.invalid_envs

    def test_reset(self):
        """캐시 초기화"""
        from core.tools.datadog_client import DatadogClientManager

        manager = DatadogClientManager({})
        manager._api_clients["test"] = MagicMock()
        manager._validated_envs.add("test")
        manager._invalid_envs.add("bad")

        manager.reset()

        assert manager._api_clients == {}
        assert manager._validated_envs == set()
        assert manager._invalid_envs == set()

    def test_validate_missing_api_key(self):
        """API 키 누락"""
        from core.tools.datadog_client import DatadogClientManager

        manager = DatadogClientManager({"prod": {"api_key": "", "app_key": "app"}})
        result = manager._validate_and_create_client("prod", {"api_key": "", "app_key": "app"})

        assert result is None
        assert "prod" in manager._invalid_envs

    def test_validate_missing_app_key(self):
        """APP 키 누락"""
        from core.tools.datadog_client import DatadogClientManager

        manager = DatadogClientManager({"prod": {"api_key": "key", "app_key": ""}})
        result = manager._validate_and_create_client("prod", {"api_key": "key", "app_key": ""})

        assert result is None
        assert "prod" in manager._invalid_envs

    def test_cached_invalid_env(self):
        """이미 실패한 환경은 스킵"""
        from core.tools.datadog_client import DatadogClientManager

        manager = DatadogClientManager({})
        manager._invalid_envs.add("bad_env")

        result = manager._validate_and_create_client("bad_env", {})

        assert result is None

    def test_cached_client_reuse(self):
        """이미 생성된 클라이언트 재사용"""
        from core.tools.datadog_client import DatadogClientManager

        mock_client = MagicMock()
        manager = DatadogClientManager({})
        manager._api_clients["prod"] = mock_client

        result = manager._validate_and_create_client("prod", {})

        assert result is mock_client


class TestGetDatadogClients:
    """get_datadog_clients 편의 함수 테스트"""

    @patch("core.tools.datadog_client.DatadogClientManager")
    def test_calls_manager(self, mock_manager_class):
        """매니저를 올바르게 호출"""
        from core.tools.datadog_client import get_datadog_clients

        mock_manager = MagicMock()
        mock_manager.get_all_clients.return_value = {}
        mock_manager_class.return_value = mock_manager

        api_keys = {"prod": {"api_key": "k", "app_key": "a"}}
        result = get_datadog_clients(api_keys)

        mock_manager_class.assert_called_once_with(api_keys)
        mock_manager.get_all_clients.assert_called_once()

    @patch("core.tools.datadog_client.DatadogClientManager")
    def test_passes_api_types(self, mock_manager_class):
        """API 타입을 올바르게 전달"""
        from core.tools.datadog_client import get_datadog_clients

        mock_manager = MagicMock()
        mock_manager.get_all_clients.return_value = {}
        mock_manager_class.return_value = mock_manager

        get_datadog_clients({}, api_types={"events"})

        mock_manager.get_all_clients.assert_called_once_with({"events"}, False)

    @patch("core.tools.datadog_client.DatadogClientManager")
    def test_passes_show_progress(self, mock_manager_class):
        """show_progress 옵션 전달"""
        from core.tools.datadog_client import get_datadog_clients

        mock_manager = MagicMock()
        mock_manager.get_all_clients.return_value = {}
        mock_manager_class.return_value = mock_manager

        get_datadog_clients({}, show_progress=True)

        mock_manager.get_all_clients.assert_called_once_with(None, True)
