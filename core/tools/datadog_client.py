"""
core/tools/datadog_client.py - Datadog API 클라이언트 관리

Datadog API 클라이언트의 초기화, 검증, 캐싱을 담당합니다.

Usage:
    from core.tools.datadog_client import DatadogClientManager, get_datadog_clients

    API_KEYS = {
        "prod_app": {"api_key": "xxx", "app_key": "yyy"},
    }

    # 클래스 사용
    manager = DatadogClientManager(API_KEYS)
    clients = manager.get_all_clients(api_types={"events"}, show_progress=True)

    # 편의 함수
    clients = get_datadog_clients(API_KEYS, api_types={"events"})

    # 결과 사용
    for env, apis in clients.items():
        events_api = apis["events"]
        # events_api.search_events(...)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from datadog_api_client import ApiClient

logger = logging.getLogger(__name__)

ApiType = Literal["events", "metrics"]


class DatadogClientManager:
    """Datadog API 클라이언트 관리자

    여러 환경의 Datadog API 클라이언트를 초기화하고 관리합니다.
    API 키 유효성 검사, SSL 설정, 클라이언트 캐싱을 담당합니다.

    Attributes:
        api_keys: 환경별 API 키 딕셔너리
            {"env_name": {"api_key": "...", "app_key": "..."}, ...}
    """

    def __init__(self, api_keys: dict[str, dict[str, str]]) -> None:
        self._api_keys = api_keys
        self._api_clients: dict[str, ApiClient] = {}
        self._validated_envs: set[str] = set()
        self._invalid_envs: set[str] = set()

    def _create_configuration(self, api_key: str, app_key: str):
        """Datadog API Configuration 생성"""
        from datadog_api_client import Configuration

        configuration = Configuration()
        configuration.api_key["apiKeyAuth"] = api_key
        configuration.api_key["appKeyAuth"] = app_key
        configuration.server_variables["site"] = "datadoghq.com"

        # macOS SSL 인증서 문제 해결
        try:
            import certifi

            configuration.ssl_ca_cert = certifi.where()
            logger.debug("certifi CA 번들 사용: %s", certifi.where())
        except ImportError:
            logger.warning("certifi 패키지 없음. 'pip install certifi' 권장")

        return configuration

    def _validate_and_create_client(self, env: str, keys: dict[str, str]) -> ApiClient | None:
        """API 키 유효성 검사 후 클라이언트 생성"""
        from datadog_api_client import ApiClient
        from datadog_api_client.v1.api.authentication_api import AuthenticationApi

        if env in self._invalid_envs:
            return None

        if env in self._api_clients:
            return self._api_clients[env]

        api_key = keys.get("api_key", "")
        app_key = keys.get("app_key", "")

        if not api_key or not app_key:
            logger.warning("%s: API 키 또는 APP 키가 설정되지 않음", env)
            self._invalid_envs.add(env)
            return None

        try:
            configuration = self._create_configuration(api_key, app_key)
            api_client = ApiClient(configuration)

            # API 키 유효성 검사
            auth_api = AuthenticationApi(api_client)
            auth_api.validate()

            self._api_clients[env] = api_client
            self._validated_envs.add(env)
            logger.info("%s: Datadog API 클라이언트 초기화 성공", env)
            return api_client

        except Exception as e:
            logger.error("%s: API 키 유효성 검사 실패 - %s", env, e)
            self._invalid_envs.add(env)
            return None

    def get_client(
        self,
        env: str,
        api_types: set[ApiType] | None = None,
    ) -> dict[str, Any] | None:
        """특정 환경의 API 클라이언트 반환

        Args:
            env: 환경명 (prod_app, prod_erp 등)
            api_types: 필요한 API 타입 (기본: events, metrics)

        Returns:
            {"events": EventsApi, "metrics": MetricsApi} 또는 None
        """
        from datadog_api_client.v1.api.metrics_api import MetricsApi
        from datadog_api_client.v2.api.events_api import EventsApi

        if api_types is None:
            api_types = {"events", "metrics"}

        keys = self._api_keys.get(env)
        if not keys:
            logger.warning("%s: api_keys에 정의되지 않은 환경", env)
            return None

        api_client = self._validate_and_create_client(env, keys)
        if not api_client:
            return None

        result: dict[str, Any] = {}
        if "events" in api_types:
            result["events"] = EventsApi(api_client)
        if "metrics" in api_types:
            result["metrics"] = MetricsApi(api_client)

        return result

    def get_all_clients(
        self,
        api_types: set[ApiType] | None = None,
        show_progress: bool = False,
    ) -> dict[str, dict[str, Any]]:
        """모든 환경의 API 클라이언트 반환

        Args:
            api_types: 필요한 API 타입 (기본: events, metrics)
            show_progress: 프로그레스 바 표시 여부

        Returns:
            {env: {"events": EventsApi, "metrics": MetricsApi}, ...}
        """
        if api_types is None:
            api_types = {"events", "metrics"}

        result: dict[str, dict[str, Any]] = {}
        envs = list(self._api_keys.keys())

        if show_progress:
            from cli.ui import step_progress

            with step_progress("Datadog 클라이언트 초기화", total_steps=len(envs)) as tracker:
                for env in envs:
                    tracker.step(f"검증 중: {env}")
                    client = self.get_client(env, api_types)
                    if client:
                        result[env] = client
                    tracker.complete_step()
        else:
            for env in envs:
                client = self.get_client(env, api_types)
                if client:
                    result[env] = client

        if not result:
            logger.error("유효한 Datadog API 클라이언트가 없습니다")
        else:
            logger.info("%d개 환경의 클라이언트 초기화 완료", len(result))

        return result

    @property
    def valid_envs(self) -> set[str]:
        """유효성 검사를 통과한 환경 목록"""
        return self._validated_envs.copy()

    @property
    def invalid_envs(self) -> set[str]:
        """유효성 검사 실패한 환경 목록"""
        return self._invalid_envs.copy()

    def reset(self) -> None:
        """캐시 초기화 (테스트용)"""
        self._api_clients.clear()
        self._validated_envs.clear()
        self._invalid_envs.clear()


# =============================================================================
# 편의 함수
# =============================================================================


def get_datadog_clients(
    api_keys: dict[str, dict[str, str]],
    api_types: set[ApiType] | None = None,
    show_progress: bool = False,
) -> dict[str, dict[str, Any]]:
    """Datadog API 클라이언트 반환 (편의 함수)

    Args:
        api_keys: 환경별 API 키 딕셔너리
        api_types: 필요한 API 타입 (기본: events, metrics)
        show_progress: 프로그레스 바 표시 여부

    Returns:
        {env: {"events": EventsApi, "metrics": MetricsApi}, ...}

    Example:
        API_KEYS = {"prod": {"api_key": "xxx", "app_key": "yyy"}}
        clients = get_datadog_clients(API_KEYS, api_types={"events"})
    """
    manager = DatadogClientManager(api_keys)
    return manager.get_all_clients(api_types, show_progress)
