"""
NAT Gateway Audit Analysis Package

NAT Gateway 미사용 탐지:
- Collector: NAT Gateway 목록 + CloudWatch 메트릭 (BytesOutToDestination)
- Analyzer: 미사용 판단 + 비용 계산
- Reporter: Excel 보고서 생성
"""

from .analyzer import NATAnalysisResult, NATAnalyzer
from .collector import NATAuditData, NATCollector, NATGateway
from .reporter import NATExcelReporter

__all__ = [
    "NATCollector",
    "NATGateway",
    "NATAuditData",
    "NATAnalyzer",
    "NATAnalysisResult",
    "NATExcelReporter",
]
