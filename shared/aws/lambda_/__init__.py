"""
shared/aws/lambda_ - Lambda 공통 모듈

Lambda 플러그인에서 공유하는 데이터 구조 및 수집 로직
"""

from .collector import (
    LambdaFunctionInfo,
    LambdaMetrics,
    collect_function_metrics,
    collect_functions,
    collect_functions_with_metrics,
)
from .runtime_eol import (
    EOLStatus,
    RuntimeInfo,
    get_recommended_upgrade,
    get_runtime_info,
)

__all__: list[str] = [
    # collector
    "LambdaFunctionInfo",
    "LambdaMetrics",
    "collect_functions",
    "collect_function_metrics",
    "collect_functions_with_metrics",
    # runtime_eol
    "EOLStatus",
    "RuntimeInfo",
    "get_runtime_info",
    "get_recommended_upgrade",
]
