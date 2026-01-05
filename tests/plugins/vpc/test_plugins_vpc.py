"""
tests/test_plugins_vpc.py - VPC 플러그인 테스트
"""

from plugins.vpc.sg_audit_analysis.critical_ports import (
    ALL_RISKY_PORTS,
    PORT_INFO,
    TRUSTED_ADVISOR_RED_PORTS,
    WEB_PORTS,
    check_port_range,
    check_port_range_all,
    get_port_info,
    is_risky_port,
    is_trusted_advisor_red,
    is_web_port,
)


class TestCriticalPortSets:
    """포트 집합 테스트"""

    def test_trusted_advisor_red_ports(self):
        """Trusted Advisor RED 포트"""
        expected = {20, 21, 1433, 1434, 3306, 3389, 4333, 5432, 5500}
        assert expected == TRUSTED_ADVISOR_RED_PORTS

    def test_web_ports(self):
        """웹 포트"""
        expected = {25, 80, 443, 465}
        assert expected == WEB_PORTS

    def test_all_risky_ports_includes_red(self):
        """위험 포트에 RED 포함"""
        for port in TRUSTED_ADVISOR_RED_PORTS:
            assert port in ALL_RISKY_PORTS

    def test_ssh_in_risky(self):
        """SSH 포트가 위험 포트에 포함"""
        assert 22 in ALL_RISKY_PORTS


class TestIsTrustedAdvisorRed:
    """is_trusted_advisor_red 테스트"""

    def test_red_port(self):
        """RED 포트"""
        assert is_trusted_advisor_red(3306) is True
        assert is_trusted_advisor_red(3389) is True
        assert is_trusted_advisor_red(5432) is True

    def test_not_red_port(self):
        """RED가 아닌 포트"""
        assert is_trusted_advisor_red(22) is False
        assert is_trusted_advisor_red(80) is False
        assert is_trusted_advisor_red(443) is False


class TestIsWebPort:
    """is_web_port 테스트"""

    def test_web_port(self):
        """웹 포트"""
        assert is_web_port(80) is True
        assert is_web_port(443) is True
        assert is_web_port(25) is True

    def test_not_web_port(self):
        """웹이 아닌 포트"""
        assert is_web_port(22) is False
        assert is_web_port(3306) is False


class TestIsRiskyPort:
    """is_risky_port 테스트"""

    def test_risky_port(self):
        """위험 포트"""
        assert is_risky_port(22) is True
        assert is_risky_port(3306) is True
        assert is_risky_port(6379) is True

    def test_not_risky_port(self):
        """위험하지 않은 포트"""
        assert is_risky_port(80) is False
        assert is_risky_port(443) is False
        assert is_risky_port(8080) is False


class TestGetPortInfo:
    """get_port_info 테스트"""

    def test_known_port(self):
        """알려진 포트"""
        info = get_port_info(22)
        assert info is not None
        assert info.name == "SSH"
        assert info.port == 22

    def test_unknown_port(self):
        """알 수 없는 포트"""
        info = get_port_info(12345)
        assert info is None

    def test_database_port(self):
        """데이터베이스 포트"""
        info = get_port_info(3306)
        assert info is not None
        assert info.name == "MySQL"
        assert info.category == "database"


class TestCheckPortRange:
    """check_port_range 테스트"""

    def test_range_with_risky_ports(self):
        """위험 포트 포함 범위"""
        ports = check_port_range(20, 25)
        port_numbers = {p.port for p in ports}
        assert 20 in port_numbers
        assert 21 in port_numbers
        assert 22 in port_numbers
        assert 23 in port_numbers
        # 25는 WEB_PORT라서 제외됨

    def test_range_without_risky_ports(self):
        """위험 포트 없는 범위"""
        ports = check_port_range(8000, 8100)
        assert len(ports) == 0

    def test_single_port_range(self):
        """단일 포트 범위"""
        ports = check_port_range(22, 22)
        assert len(ports) == 1
        assert ports[0].port == 22


class TestCheckPortRangeAll:
    """check_port_range_all 테스트"""

    def test_range_includes_web_ports(self):
        """웹 포트 포함 범위"""
        ports = check_port_range_all(79, 81)
        port_numbers = {p.port for p in ports}
        assert 80 in port_numbers

    def test_range_includes_all_defined(self):
        """정의된 모든 포트 포함"""
        ports = check_port_range_all(20, 25)
        port_numbers = {p.port for p in ports}
        assert 20 in port_numbers
        assert 21 in port_numbers
        assert 22 in port_numbers
        assert 23 in port_numbers
        assert 25 in port_numbers  # 웹 포트도 포함


class TestPortInfo:
    """PORT_INFO 데이터 테스트"""

    def test_all_ports_have_info(self):
        """모든 위험 포트에 정보 있음"""
        for port in ALL_RISKY_PORTS:
            assert port in PORT_INFO, f"Port {port} missing from PORT_INFO"

    def test_critical_port_fields(self):
        """CriticalPort 필드 확인"""
        for _port, info in PORT_INFO.items():
            assert isinstance(info.port, int)
            assert isinstance(info.name, str)
            assert info.protocol in ["tcp", "udp", "both"]
            assert isinstance(info.category, str)
            assert isinstance(info.description, str)
            assert isinstance(info.sources, list)

    def test_categories(self):
        """카테고리 분류"""
        categories = {info.category for info in PORT_INFO.values()}
        expected = {
            "database",
            "remote_access",
            "file_transfer",
            "windows",
            "unix",
            "web",
        }
        assert categories == expected
