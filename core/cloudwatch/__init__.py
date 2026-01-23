"""
core/cloudwatch - CloudWatch 유틸리티 모듈 (레거시 경로)

DEPRECATED: plugins.cloudwatch.common 사용 권장

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드에서는 plugins.cloudwatch.common을 사용하세요.

Usage (recommended):
    from plugins.cloudwatch.common import MetricQuery, batch_get_metrics

Usage (legacy, still supported):
    from core.cloudwatch import MetricQuery, batch_get_metrics
"""

# Re-export from new location for backward compatibility
from plugins.cloudwatch.common import (
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

__all__ = [
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
]
