"""
Security Group Audit Analysis Module
"""

from .collector import SGCollector
from .analyzer import SGAnalyzer, RuleAnalysisResult, SGAnalysisResult
from .reporter import SGExcelReporter
from .critical_ports import (
    CRITICAL_PORTS,  # 하위 호환성 (PORT_INFO alias)
    PORT_INFO,
    CriticalPort,
    TRUSTED_ADVISOR_RED_PORTS,
    WEB_PORTS,
    ALL_RISKY_PORTS,
)

__all__ = [
    "SGCollector",
    "SGAnalyzer",
    "SGExcelReporter",
    "RuleAnalysisResult",
    "SGAnalysisResult",
    "CRITICAL_PORTS",
    "PORT_INFO",
    "CriticalPort",
    "TRUSTED_ADVISOR_RED_PORTS",
    "WEB_PORTS",
    "ALL_RISKY_PORTS",
]
