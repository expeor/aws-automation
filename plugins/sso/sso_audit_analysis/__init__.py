"""
SSO Audit Analysis Package

IAM Identity Center(SSO) 보안 감사:
- Collector: Permission Set, Users, Groups, Account Assignments 수집
- Analyzer: 위험 정책 분석, MFA 상태, 미사용 사용자 탐지
- Reporter: Excel 보고서 생성
"""

from .collector import SSOCollector, SSOData
from .analyzer import SSOAnalyzer, SSOAnalysisResult
from .reporter import SSOExcelReporter

__all__ = [
    "SSOCollector",
    "SSOData",
    "SSOAnalyzer",
    "SSOAnalysisResult",
    "SSOExcelReporter",
]
