"""
shared/aws/metrics - CloudWatch Metrics Batch Utilities

CloudWatch API 최적화 도구 제공 (GetMetricData 배치 조회 등)
여러 분석기에서 공유하는 CloudWatch 유틸리티 모음.

Usage:
    from core.shared.aws.metrics import (
        MetricQuery,
        batch_get_metrics,
        build_ec2_metric_queries,
        build_lambda_metric_queries,
        MetricSessionCache,  # 세션 캐싱
    )

    # 캐시 사용 예시
    with MetricSessionCache() as cache:
        result = batch_get_metrics(..., cache=cache)
"""

from .batch_metrics import (
    MetricQuery,
    batch_get_metrics,
    batch_get_metrics_with_stats,
    build_ec2_metric_queries,
    build_elasticache_metric_queries,
    build_lambda_metric_queries,
    build_nat_metric_queries,
    build_rds_metric_queries,
    build_sagemaker_endpoint_metric_queries,
    sanitize_metric_id,
)
from .session_cache import (
    CacheStats,
    FileBackedMetricCache,
    MetricSessionCache,
    SharedMetricCache,
    get_active_cache,
    get_global_cache,
    is_cache_active,
    set_global_cache,
)

__all__ = [
    # batch_metrics
    "MetricQuery",
    "batch_get_metrics",
    "batch_get_metrics_with_stats",
    "build_ec2_metric_queries",
    "build_elasticache_metric_queries",
    "build_lambda_metric_queries",
    "build_nat_metric_queries",
    "build_rds_metric_queries",
    "build_sagemaker_endpoint_metric_queries",
    "sanitize_metric_id",
    # session_cache
    "CacheStats",
    "FileBackedMetricCache",
    "MetricSessionCache",
    "SharedMetricCache",
    "get_active_cache",
    "get_global_cache",
    "is_cache_active",
    "set_global_cache",
]
