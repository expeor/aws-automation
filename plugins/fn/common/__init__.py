"""
plugins/fn/common - Lambda 공통 모듈

Lambda 플러그인에서 공유하는 데이터 구조 및 수집 로직
"""

from .collector import (
    LambdaFunctionInfo,
    LambdaMetrics,
    collect_function_metrics,
    collect_functions,
)

__all__ = [
    "LambdaFunctionInfo",
    "LambdaMetrics",
    "collect_functions",
    "collect_function_metrics",
]
