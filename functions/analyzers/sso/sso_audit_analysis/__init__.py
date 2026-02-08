"""
functions/analyzers/sso/sso_audit_analysis - SSO 감사 분석 패키지

IAM Identity Center(SSO) 보안 감사를 위한 수집, 분석, 보고서 생성
컴포넌트를 제공합니다.

구성 요소:
    - SSOCollector: Permission Set, Users, Groups, Account Assignments 수집
    - SSOAnalyzer: 위험 정책 분석, MFA 상태, 미사용 사용자 탐지
    - SSOExcelReporter: Excel 보고서 생성
"""

from .analyzer import SSOAnalysisResult, SSOAnalyzer
from .collector import SSOCollector, SSOData
from .reporter import SSOExcelReporter

__all__: list[str] = [
    "SSOCollector",
    "SSOData",
    "SSOAnalyzer",
    "SSOAnalysisResult",
    "SSOExcelReporter",
]
