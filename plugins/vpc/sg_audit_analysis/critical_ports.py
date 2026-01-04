"""
Critical Ports 정의 - AWS Trusted Advisor 기준

공식 문서 기반:
- AWS Trusted Advisor: Security Groups - Specific Ports Unrestricted
  - RED (HIGH): 20, 21, 1433, 1434, 3306, 3389, 4333, 5432, 5500
  - GREEN (허용): 25, 80, 443, 465
  - YELLOW (MEDIUM): 그 외 모든 포트
- CIS AWS Foundations Benchmark
- NIST SP 800-123

Risk Level 결정은 포트 + Source 복합 조건으로 analyzer.py에서 수행
"""

from dataclasses import dataclass


@dataclass
class CriticalPort:
    """Critical Port 정의"""

    port: int
    name: str
    protocol: str  # tcp / udp / both
    category: str  # database / remote_access / file_transfer / windows / unix
    description: str
    sources: list[str]


# AWS Trusted Advisor RED 포트 (9개)
# 이 포트들이 0.0.0.0/0에 노출되면 HIGH
TRUSTED_ADVISOR_RED_PORTS: set[int] = {
    20,  # FTP Data
    21,  # FTP Control
    1433,  # MS SQL Server
    1434,  # MS SQL Server Browser
    3306,  # MySQL/MariaDB
    3389,  # RDP
    4333,  # mSQL
    5432,  # PostgreSQL
    5500,  # VNC HTTP
}

# AWS Trusted Advisor GREEN 포트 (4개)
# 이 포트들은 0.0.0.0/0에 노출되어도 일반적으로 허용 (웹 서비스)
WEB_PORTS: set[int] = {
    25,  # SMTP
    80,  # HTTP
    443,  # HTTPS
    465,  # SMTPS
}

# 추가 위험 포트 (CIS/NIST 기준)
# AWS Trusted Advisor에는 없지만 보안 기준상 위험한 포트
ADDITIONAL_RISKY_PORTS: set[int] = {
    22,  # SSH (AWS Trusted Advisor에서는 YELLOW지만 CIS에서는 제한 권장)
    23,  # Telnet (평문 전송)
    111,  # RPC Portmapper
    135,  # MS RPC
    137,  # NetBIOS NS
    138,  # NetBIOS DGM
    139,  # NetBIOS SSN
    445,  # SMB/CIFS
    1521,  # Oracle
    2049,  # NFS
    5900,  # VNC
    6379,  # Redis
    9200,  # Elasticsearch
    27017,  # MongoDB
}

# 모든 위험 포트 = Trusted Advisor RED + 추가 위험 포트
ALL_RISKY_PORTS: set[int] = TRUSTED_ADVISOR_RED_PORTS | ADDITIONAL_RISKY_PORTS


# 포트 상세 정보 (참조용)
PORT_INFO: dict[int, CriticalPort] = {
    # === Trusted Advisor RED: 파일 전송 ===
    20: CriticalPort(
        port=20,
        name="FTP Data",
        protocol="tcp",
        category="file_transfer",
        description="FTP Data Transfer",
        sources=["AWS Trusted Advisor (RED)"],
    ),
    21: CriticalPort(
        port=21,
        name="FTP",
        protocol="tcp",
        category="file_transfer",
        description="FTP Control (평문 전송)",
        sources=["AWS Trusted Advisor (RED)"],
    ),
    # === Trusted Advisor RED: 데이터베이스 ===
    1433: CriticalPort(
        port=1433,
        name="MSSQL",
        protocol="tcp",
        category="database",
        description="Microsoft SQL Server",
        sources=["AWS Trusted Advisor (RED)"],
    ),
    1434: CriticalPort(
        port=1434,
        name="MSSQL Browser",
        protocol="udp",
        category="database",
        description="MSSQL Browser Service",
        sources=["AWS Trusted Advisor (RED)"],
    ),
    3306: CriticalPort(
        port=3306,
        name="MySQL",
        protocol="tcp",
        category="database",
        description="MySQL/MariaDB",
        sources=["AWS Trusted Advisor (RED)"],
    ),
    5432: CriticalPort(
        port=5432,
        name="PostgreSQL",
        protocol="tcp",
        category="database",
        description="PostgreSQL",
        sources=["AWS Trusted Advisor (RED)"],
    ),
    4333: CriticalPort(
        port=4333,
        name="mSQL",
        protocol="tcp",
        category="database",
        description="ahsp/mini SQL",
        sources=["AWS Trusted Advisor (RED)"],
    ),
    # === Trusted Advisor RED: 원격 접속 ===
    3389: CriticalPort(
        port=3389,
        name="RDP",
        protocol="tcp",
        category="remote_access",
        description="Remote Desktop Protocol",
        sources=["AWS Trusted Advisor (RED)"],
    ),
    5500: CriticalPort(
        port=5500,
        name="VNC HTTP",
        protocol="tcp",
        category="remote_access",
        description="VNC Server HTTP",
        sources=["AWS Trusted Advisor (RED)"],
    ),
    # === 추가 위험 포트: 원격 관리 ===
    22: CriticalPort(
        port=22,
        name="SSH",
        protocol="tcp",
        category="remote_access",
        description="Secure Shell",
        sources=["AWS Trusted Advisor (YELLOW)", "CIS Benchmark 5.2"],
    ),
    23: CriticalPort(
        port=23,
        name="Telnet",
        protocol="tcp",
        category="remote_access",
        description="Telnet (평문 전송 - 사용 금지 권장)",
        sources=["NIST SP 800-123", "CIS Controls"],
    ),
    5900: CriticalPort(
        port=5900,
        name="VNC",
        protocol="tcp",
        category="remote_access",
        description="VNC",
        sources=["CIS Controls"],
    ),
    # === 추가 위험 포트: 데이터베이스 ===
    1521: CriticalPort(
        port=1521,
        name="Oracle",
        protocol="tcp",
        category="database",
        description="Oracle TNS Listener",
        sources=["NIST SP 800-123"],
    ),
    6379: CriticalPort(
        port=6379,
        name="Redis",
        protocol="tcp",
        category="database",
        description="Redis",
        sources=["Redis Security Docs"],
    ),
    9200: CriticalPort(
        port=9200,
        name="Elasticsearch",
        protocol="tcp",
        category="database",
        description="Elasticsearch HTTP",
        sources=["Elastic Security Docs"],
    ),
    27017: CriticalPort(
        port=27017,
        name="MongoDB",
        protocol="tcp",
        category="database",
        description="MongoDB",
        sources=["MongoDB Security Checklist"],
    ),
    # === 추가 위험 포트: Windows 서비스 ===
    135: CriticalPort(
        port=135,
        name="MS RPC",
        protocol="tcp",
        category="windows",
        description="Microsoft RPC",
        sources=["CIS Controls", "Microsoft Security Baseline"],
    ),
    137: CriticalPort(
        port=137,
        name="NetBIOS NS",
        protocol="udp",
        category="windows",
        description="NetBIOS Name Service",
        sources=["CIS Controls"],
    ),
    138: CriticalPort(
        port=138,
        name="NetBIOS DGM",
        protocol="udp",
        category="windows",
        description="NetBIOS Datagram",
        sources=["CIS Controls"],
    ),
    139: CriticalPort(
        port=139,
        name="NetBIOS SSN",
        protocol="tcp",
        category="windows",
        description="NetBIOS Session",
        sources=["CIS Controls"],
    ),
    445: CriticalPort(
        port=445,
        name="SMB",
        protocol="tcp",
        category="windows",
        description="SMB/CIFS",
        sources=["CIS Controls", "Microsoft Security Baseline"],
    ),
    # === 추가 위험 포트: Unix 서비스 ===
    111: CriticalPort(
        port=111,
        name="RPC",
        protocol="both",
        category="unix",
        description="ONC RPC Portmapper",
        sources=["CIS Controls"],
    ),
    2049: CriticalPort(
        port=2049,
        name="NFS",
        protocol="both",
        category="unix",
        description="Network File System",
        sources=["CIS Controls"],
    ),
    # === 웹 포트 (Trusted Advisor GREEN) ===
    25: CriticalPort(
        port=25,
        name="SMTP",
        protocol="tcp",
        category="web",
        description="Simple Mail Transfer Protocol",
        sources=["AWS Trusted Advisor (GREEN)"],
    ),
    80: CriticalPort(
        port=80,
        name="HTTP",
        protocol="tcp",
        category="web",
        description="HTTP",
        sources=["AWS Trusted Advisor (GREEN)"],
    ),
    443: CriticalPort(
        port=443,
        name="HTTPS",
        protocol="tcp",
        category="web",
        description="HTTPS",
        sources=["AWS Trusted Advisor (GREEN)"],
    ),
    465: CriticalPort(
        port=465,
        name="SMTPS",
        protocol="tcp",
        category="web",
        description="SMTP over SSL",
        sources=["AWS Trusted Advisor (GREEN)"],
    ),
}


def is_trusted_advisor_red(port: int) -> bool:
    """AWS Trusted Advisor RED 포트 여부"""
    return port in TRUSTED_ADVISOR_RED_PORTS


def is_web_port(port: int) -> bool:
    """웹 포트 (일반적으로 허용) 여부"""
    return port in WEB_PORTS


def is_risky_port(port: int) -> bool:
    """위험 포트 (Trusted Advisor RED + 추가) 여부"""
    return port in ALL_RISKY_PORTS


def get_port_info(port: int) -> CriticalPort | None:
    """포트 정보 조회"""
    return PORT_INFO.get(port)


def check_port_range(from_port: int, to_port: int) -> list[CriticalPort]:
    """포트 범위 내 위험 포트 조회 (웹 포트 제외)"""
    return [
        info
        for port, info in PORT_INFO.items()
        if from_port <= port <= to_port and port in ALL_RISKY_PORTS
    ]


def check_port_range_all(from_port: int, to_port: int) -> list[CriticalPort]:
    """포트 범위 내 모든 정의된 포트 조회 (웹 포트 포함)"""
    return [info for port, info in PORT_INFO.items() if from_port <= port <= to_port]


# 하위 호환성을 위한 alias
CRITICAL_PORTS = PORT_INFO
