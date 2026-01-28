"""
plugins/cloudwatch/common - Backwards Compatibility Shim

DEPRECATED: 이 모듈은 shared.aws.metrics로 이동되었습니다.
새 코드에서는 shared.aws.metrics를 직접 import하세요.

Usage (NEW):
    from shared.aws.metrics import (
        MetricQuery,
        batch_get_metrics,
        build_ec2_metric_queries,
        build_lambda_metric_queries,
    )
"""

import warnings

# Re-export from new location for backwards compatibility
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

# Issue deprecation warning when this module is imported
warnings.warn(
    "plugins.cloudwatch.common is deprecated. Use shared.aws.metrics instead.",
    DeprecationWarning,
    stacklevel=2,
)
