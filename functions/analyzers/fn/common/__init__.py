"""
functions/analyzers/fn/common - Lambda 공통 모듈

Lambda 분석 플러그인에서 공유하는 데이터 구조 및 수집 로직을 제공한다.

주요 제공:
    - LambdaFunctionInfo: Lambda 함수 메타데이터 + 설정 정보.
    - LambdaMetrics: CloudWatch 기반 호출/성능/동시성 메트릭.
    - collect_functions(): 함수 목록 수집 (메타데이터만).
    - collect_function_metrics(): 단일 함수 메트릭 수집 (하위 호환).
"""

from .collector import (
    LambdaFunctionInfo,
    LambdaMetrics,
    collect_function_metrics,
    collect_functions,
)

__all__: list[str] = [
    "LambdaFunctionInfo",
    "LambdaMetrics",
    "collect_functions",
    "collect_function_metrics",
]
