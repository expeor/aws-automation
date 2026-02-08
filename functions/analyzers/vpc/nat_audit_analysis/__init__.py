"""
functions/analyzers/vpc/nat_audit_analysis - NAT Gateway 감사 분석 패키지

NAT Gateway의 미사용 여부를 탐지하고 비용을 분석합니다.

구성 요소:
    - NATCollector: NAT Gateway 목록 + CloudWatch 메트릭 (BytesOutToDestination) 수집
    - NATAnalyzer: 미사용 판단 + 비용 계산
    - NATExcelReporter: Excel 보고서 생성
"""

from .analyzer import NATAnalysisResult, NATAnalyzer
from .collector import NATAuditData, NATCollector, NATGateway
from .reporter import NATExcelReporter

__all__: list[str] = [
    "NATCollector",
    "NATGateway",
    "NATAuditData",
    "NATAnalyzer",
    "NATAnalysisResult",
    "NATExcelReporter",
]
