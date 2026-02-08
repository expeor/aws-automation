"""tests/analyzers/transfer/test_unused.py - Transfer Family 미사용 분석 테스트"""

from __future__ import annotations

from functions.analyzers.transfer.unused import (
    ServerStatus,
    TransferAnalysisResult,
    TransferFinding,
    TransferServerInfo,
)

# =============================================================================
# 팩토리 함수
# =============================================================================


def _make_transfer_server(
    server_id: str = "s-123456",
    endpoint_type: str = "PUBLIC",
    protocols: list[str] | None = None,
    state: str = "ONLINE",
    identity_provider_type: str = "SERVICE_MANAGED",
    user_count: int = 2,
    files_in: float = 100.0,
    files_out: float = 50.0,
    bytes_in: float = 1024.0,
    bytes_out: float = 512.0,
    estimated_monthly_cost: float = 216.0,
    account_id: str = "123456789012",
    account_name: str = "test-account",
    region: str = "ap-northeast-2",
) -> TransferServerInfo:
    """테스트용 TransferServerInfo 생성"""
    return TransferServerInfo(
        account_id=account_id,
        account_name=account_name,
        region=region,
        server_id=server_id,
        endpoint_type=endpoint_type,
        protocols=protocols or ["SFTP"],
        state=state,
        identity_provider_type=identity_provider_type,
        user_count=user_count,
        files_in=files_in,
        files_out=files_out,
        bytes_in=bytes_in,
        bytes_out=bytes_out,
        estimated_monthly_cost=estimated_monthly_cost,
    )


def _make_finding(
    server: TransferServerInfo | None = None,
    status: ServerStatus = ServerStatus.NORMAL,
    recommendation: str = "",
) -> TransferFinding:
    """테스트용 TransferFinding 생성"""
    return TransferFinding(
        server=server or _make_transfer_server(),
        status=status,
        recommendation=recommendation,
    )


def _make_analysis_result(
    findings: list[TransferFinding] | None = None,
    total_servers: int = 5,
    unused_servers: int = 1,
    idle_servers: int = 1,
    no_users_servers: int = 0,
    stopped_servers: int = 0,
    normal_servers: int = 3,
    total_monthly_waste: float = 432.0,
    account_id: str = "123456789012",
    account_name: str = "test-account",
    region: str = "ap-northeast-2",
) -> TransferAnalysisResult:
    """테스트용 TransferAnalysisResult 생성"""
    return TransferAnalysisResult(
        account_id=account_id,
        account_name=account_name,
        region=region,
        total_servers=total_servers,
        unused_servers=unused_servers,
        idle_servers=idle_servers,
        no_users_servers=no_users_servers,
        stopped_servers=stopped_servers,
        normal_servers=normal_servers,
        total_monthly_waste=total_monthly_waste,
        findings=findings or [],
    )


# =============================================================================
# ServerStatus Enum 테스트
# =============================================================================


class TestServerStatus:
    """ServerStatus enum 테스트"""

    def test_values(self):
        assert ServerStatus.NORMAL.value == "normal"
        assert ServerStatus.UNUSED.value == "unused"
        assert ServerStatus.IDLE.value == "idle"
        assert ServerStatus.NO_USERS.value == "no_users"
        assert ServerStatus.STOPPED.value == "stopped"

    def test_all_members(self):
        members = list(ServerStatus)
        assert len(members) == 5


# =============================================================================
# TransferServerInfo 테스트
# =============================================================================


class TestTransferServerInfo:
    """TransferServerInfo 프로퍼티 테스트"""

    def test_total_files(self):
        """파일 합계"""
        server = _make_transfer_server(files_in=100.0, files_out=50.0)
        assert server.total_files == 150.0

    def test_total_files_zero(self):
        """파일 없음"""
        server = _make_transfer_server(files_in=0.0, files_out=0.0)
        assert server.total_files == 0.0

    def test_total_bytes(self):
        """바이트 합계"""
        server = _make_transfer_server(bytes_in=1024.0, bytes_out=512.0)
        assert server.total_bytes == 1536.0

    def test_is_active_with_files(self):
        """파일 전송이 있으면 활성"""
        server = _make_transfer_server(files_in=10.0, files_out=0.0, bytes_in=0.0, bytes_out=0.0)
        assert server.is_active is True

    def test_is_active_with_bytes(self):
        """바이트 전송이 있으면 활성"""
        server = _make_transfer_server(files_in=0.0, files_out=0.0, bytes_in=100.0, bytes_out=0.0)
        assert server.is_active is True

    def test_is_not_active(self):
        """전송 없으면 비활성"""
        server = _make_transfer_server(files_in=0.0, files_out=0.0, bytes_in=0.0, bytes_out=0.0)
        assert server.is_active is False

    def test_default_protocols(self):
        """기본 프로토콜"""
        server = _make_transfer_server()
        assert server.protocols == ["SFTP"]

    def test_multiple_protocols(self):
        """여러 프로토콜"""
        server = _make_transfer_server(protocols=["SFTP", "FTPS", "FTP"])
        assert len(server.protocols) == 3

    def test_offline_server(self):
        """OFFLINE 서버"""
        server = _make_transfer_server(state="OFFLINE")
        assert server.state == "OFFLINE"

    def test_cost_estimate(self):
        """비용 추정"""
        server = _make_transfer_server(estimated_monthly_cost=216.0)
        assert server.estimated_monthly_cost == 216.0


# =============================================================================
# TransferFinding 테스트
# =============================================================================


class TestTransferFinding:
    """TransferFinding 테스트"""

    def test_unused_finding(self):
        server = _make_transfer_server(files_in=0.0, files_out=0.0)
        finding = _make_finding(server=server, status=ServerStatus.UNUSED, recommendation="서버 삭제 권장")
        assert finding.status == ServerStatus.UNUSED
        assert finding.recommendation == "서버 삭제 권장"

    def test_normal_finding(self):
        finding = _make_finding(status=ServerStatus.NORMAL)
        assert finding.status == ServerStatus.NORMAL

    def test_no_users_finding(self):
        server = _make_transfer_server(user_count=0)
        finding = _make_finding(server=server, status=ServerStatus.NO_USERS)
        assert finding.server.user_count == 0


# =============================================================================
# TransferAnalysisResult 테스트
# =============================================================================


class TestTransferAnalysisResult:
    """TransferAnalysisResult 테스트"""

    def test_creation(self):
        result = _make_analysis_result()
        assert result.total_servers == 5
        assert result.unused_servers == 1
        assert result.total_monthly_waste == 432.0

    def test_empty_result(self):
        result = _make_analysis_result(
            total_servers=0,
            unused_servers=0,
            idle_servers=0,
            normal_servers=0,
            total_monthly_waste=0.0,
        )
        assert result.total_servers == 0
        assert result.total_monthly_waste == 0.0

    def test_all_unused(self):
        result = _make_analysis_result(
            total_servers=3,
            unused_servers=3,
            normal_servers=0,
            total_monthly_waste=648.0,
        )
        assert result.unused_servers == result.total_servers

    def test_findings_list(self):
        findings = [
            _make_finding(status=ServerStatus.UNUSED),
            _make_finding(status=ServerStatus.IDLE),
            _make_finding(status=ServerStatus.NORMAL),
        ]
        result = _make_analysis_result(findings=findings)
        assert len(result.findings) == 3

        unused = [f for f in result.findings if f.status == ServerStatus.UNUSED]
        assert len(unused) == 1
