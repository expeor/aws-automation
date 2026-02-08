"""
functions/analyzers/vpc/sg_audit_analysis - Security Group 감사 분석 모듈

Security Group의 인바운드/아웃바운드 규칙을 분석하고 위험한 규칙,
미사용 SG를 탐지합니다.

구성 요소:
    - SGCollector: Security Group 및 규칙 수집
    - SGAnalyzer: 위험 규칙 분석 및 미사용 SG 판단
    - SGExcelReporter: Excel 보고서 생성
    - critical_ports: 위험 포트 정의 (CRITICAL_PORTS, TRUSTED_ADVISOR_RED_PORTS 등)
"""

from .analyzer import RuleAnalysisResult, SGAnalysisResult, SGAnalyzer, SGStatus
from .collector import SGCollector
from .critical_ports import (
    ALL_RISKY_PORTS,
    CRITICAL_PORTS,  # 하위 호환성 (PORT_INFO alias)
    PORT_INFO,
    TRUSTED_ADVISOR_RED_PORTS,
    WEB_PORTS,
    CriticalPort,
)
from .reporter import SGExcelReporter

__all__: list[str] = [
    "SGCollector",
    "SGAnalyzer",
    "SGExcelReporter",
    "SGStatus",
    "RuleAnalysisResult",
    "SGAnalysisResult",
    "CRITICAL_PORTS",
    "PORT_INFO",
    "CriticalPort",
    "TRUSTED_ADVISOR_RED_PORTS",
    "WEB_PORTS",
    "ALL_RISKY_PORTS",
]
