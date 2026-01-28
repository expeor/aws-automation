"""DEPRECATED: Use shared.aws.metrics instead.

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드에서는 shared.aws.metrics를 사용하세요.

Usage:
    from shared.aws.metrics import MetricQuery, batch_get_metrics
"""

import warnings

from shared.aws.metrics import (
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

warnings.warn(
    "core.cloudwatch is deprecated. Use shared.aws.metrics instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "MetricQuery",
    "batch_get_metrics",
    "batch_get_metrics_with_stats",
    "build_ec2_metric_queries",
    "build_rds_metric_queries",
    "build_lambda_metric_queries",
    "build_nat_metric_queries",
    "build_elasticache_metric_queries",
    "build_sagemaker_endpoint_metric_queries",
    "sanitize_metric_id",
]
