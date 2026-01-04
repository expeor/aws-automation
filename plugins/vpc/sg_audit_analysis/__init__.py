"""
Security Group Audit Analysis Module
"""

from .analyzer import RuleAnalysisResult, SGAnalysisResult, SGAnalyzer
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
    "RuleAnalysisResult",
    "SGAnalysisResult",
    "CRITICAL_PORTS",
    "PORT_INFO",
    "CriticalPort",
    "TRUSTED_ADVISOR_RED_PORTS",
    "WEB_PORTS",
    "ALL_RISKY_PORTS",
]
