"""
functions/analyzers/iam/iam_audit_analysis - IAM 감사 분석 모듈

IAM 보안 감사를 위한 수집, 분석, 보고서 생성 컴포넌트를 제공합니다.

구성 요소:
    - IAMCollector: IAM 사용자, 역할, Access Key, 비밀번호 정책 수집
    - IAMAnalyzer: 사용자/역할/키 보안 분석
    - IAMExcelReporter: Excel 보고서 생성
"""

from .analyzer import (
    IAMAnalyzer,
    KeyAnalysisResult,
    RoleAnalysisResult,
    UserAnalysisResult,
)
from .collector import (
    GitCredential,
    IAMAccessKey,
    IAMCollector,
    IAMData,
    IAMRole,
    IAMUser,
    IAMUserChangeHistory,
    PasswordPolicy,
    RoleResourceRelation,
)
from .reporter import IAMExcelReporter

__all__: list[str] = [
    # Collector
    "IAMCollector",
    "IAMUser",
    "IAMRole",
    "IAMAccessKey",
    "GitCredential",
    "IAMUserChangeHistory",
    "RoleResourceRelation",
    "PasswordPolicy",
    "IAMData",
    # Analyzer
    "IAMAnalyzer",
    "UserAnalysisResult",
    "RoleAnalysisResult",
    "KeyAnalysisResult",
    # Reporter
    "IAMExcelReporter",
]
