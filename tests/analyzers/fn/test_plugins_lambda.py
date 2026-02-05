"""
tests/test_plugins_lambda.py - Lambda 플러그인 테스트
"""

from datetime import date

from analyzers.fn.common.runtime_eol import (
    RUNTIME_EOL_DATA,
    EOLStatus,
    RuntimeInfo,
    get_deprecated_runtimes,
    get_expiring_runtimes,
    get_recommended_upgrade,
    get_runtime_info,
    get_runtime_status,
)


class TestRuntimeInfo:
    """RuntimeInfo 데이터클래스 테스트"""

    def test_is_deprecated_true(self):
        """지원 종료된 런타임"""
        runtime = RuntimeInfo(
            runtime_id="python3.6",
            name="Python 3.6",
            deprecation_date=date(2022, 7, 18),
            block_update_date=date(2022, 8, 17),
            eol_date=None,
        )
        assert runtime.is_deprecated is True

    def test_is_deprecated_false(self):
        """지원 중인 런타임"""
        runtime = RuntimeInfo(
            runtime_id="python3.12",
            name="Python 3.12",
            deprecation_date=None,
            block_update_date=None,
            eol_date=None,
        )
        assert runtime.is_deprecated is False

    def test_days_until_deprecation_none(self):
        """EOL 미정인 런타임"""
        runtime = RuntimeInfo(
            runtime_id="python3.12",
            name="Python 3.12",
            deprecation_date=None,
            block_update_date=None,
            eol_date=None,
        )
        assert runtime.days_until_deprecation is None

    def test_status_supported(self):
        """지원 중 상태"""
        runtime = RuntimeInfo(
            runtime_id="python3.12",
            name="Python 3.12",
            deprecation_date=None,
            block_update_date=None,
            eol_date=None,
        )
        assert runtime.status == EOLStatus.SUPPORTED

    def test_status_deprecated(self):
        """지원 종료 상태"""
        runtime = RuntimeInfo(
            runtime_id="python3.6",
            name="Python 3.6",
            deprecation_date=date(2022, 7, 18),
            block_update_date=None,
            eol_date=None,
        )
        assert runtime.status == EOLStatus.DEPRECATED


class TestGetRuntimeInfo:
    """런타임 정보 조회 테스트"""

    def test_get_existing_runtime(self):
        """존재하는 런타임"""
        info = get_runtime_info("python3.12")
        assert info is not None
        assert info.name == "Python 3.12"

    def test_get_nonexistent_runtime(self):
        """존재하지 않는 런타임"""
        info = get_runtime_info("python2.5")
        assert info is None


class TestGetRuntimeStatus:
    """런타임 상태 조회 테스트"""

    def test_supported_runtime(self):
        """지원 중인 런타임"""
        status = get_runtime_status("python3.13")
        assert status == EOLStatus.SUPPORTED

    def test_deprecated_runtime(self):
        """지원 종료된 런타임"""
        status = get_runtime_status("python3.6")
        assert status == EOLStatus.DEPRECATED

    def test_unknown_runtime(self):
        """알 수 없는 런타임"""
        status = get_runtime_status("unknown")
        assert status == EOLStatus.SUPPORTED


class TestGetDeprecatedRuntimes:
    """지원 종료 런타임 목록 테스트"""

    def test_deprecated_runtimes_exist(self):
        """지원 종료 런타임이 있음"""
        deprecated = get_deprecated_runtimes()
        assert len(deprecated) > 0
        assert "python3.6" in deprecated
        assert "python2.7" in deprecated


class TestGetExpiringRuntimes:
    """곧 지원 종료될 런타임 목록 테스트"""

    def test_expiring_runtimes(self):
        """지원 종료 예정 런타임"""
        # 이미 지원 종료된 것은 제외됨
        expiring = get_expiring_runtimes(days=365)
        for _runtime_id, info in expiring.items():
            days = info.days_until_deprecation
            assert days is not None
            assert 0 < days <= 365


class TestGetRecommendedUpgrade:
    """권장 업그레이드 테스트"""

    def test_python_upgrade(self):
        """Python 업그레이드 권장"""
        assert get_recommended_upgrade("python3.8") == "python3.13"
        assert get_recommended_upgrade("python3.7") == "python3.13"

    def test_nodejs_upgrade(self):
        """Node.js 업그레이드 권장"""
        assert get_recommended_upgrade("nodejs16.x") == "nodejs22.x"
        assert get_recommended_upgrade("nodejs14.x") == "nodejs22.x"

    def test_no_upgrade_needed(self):
        """업그레이드 불필요"""
        assert get_recommended_upgrade("python3.13") is None
        assert get_recommended_upgrade("nodejs22.x") is None

    def test_java_upgrade(self):
        """Java 업그레이드 권장"""
        assert get_recommended_upgrade("java8") == "java21"

    def test_dotnet_upgrade(self):
        """.NET 업그레이드 권장"""
        assert get_recommended_upgrade("dotnet6") == "dotnet10"
        assert get_recommended_upgrade("dotnetcore3.1") == "dotnet10"


class TestRuntimeEOLData:
    """런타임 EOL 데이터 테스트"""

    def test_current_python_runtimes_active(self):
        """현재 Python 런타임 지원 확인"""
        for version in ["python3.13", "python3.12", "python3.11", "python3.10"]:
            info = RUNTIME_EOL_DATA.get(version)
            assert info is not None
            assert info.status in [EOLStatus.SUPPORTED, EOLStatus.LOW, EOLStatus.MEDIUM]

    def test_current_nodejs_runtimes_active(self):
        """현재 Node.js 런타임 지원 확인 (미종료)"""
        for version in ["nodejs22.x", "nodejs20.x"]:
            info = RUNTIME_EOL_DATA.get(version)
            assert info is not None
            assert info.is_deprecated is False

    def test_old_runtimes_deprecated(self):
        """이전 런타임 지원 종료 확인"""
        deprecated = ["python2.7", "python3.6", "python3.8", "python3.9", "nodejs12.x", "nodejs18.x"]
        for version in deprecated:
            info = RUNTIME_EOL_DATA.get(version)
            assert info is not None
            assert info.is_deprecated is True

    def test_os_version_set(self):
        """OS 버전 필드 확인"""
        from analyzers.fn.common.runtime_eol import OS_AL1, OS_AL2, OS_AL2023

        assert RUNTIME_EOL_DATA["python3.13"].os_version == OS_AL2023
        assert RUNTIME_EOL_DATA["python3.10"].os_version == OS_AL2
        assert RUNTIME_EOL_DATA["python3.7"].os_version == OS_AL1

    def test_recommended_upgrade_field(self):
        """recommended_upgrade 필드 확인"""
        assert RUNTIME_EOL_DATA["python3.8"].recommended_upgrade == "python3.13"
        assert RUNTIME_EOL_DATA["nodejs16.x"].recommended_upgrade == "nodejs22.x"
        assert RUNTIME_EOL_DATA["python3.13"].recommended_upgrade == ""
