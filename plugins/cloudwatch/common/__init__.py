"""
plugins/cloudwatch/common - Shared CloudWatch Utilities

CloudWatch API 최적화 도구 제공 (GetMetricData 배치 조회 등)
여러 플러그인에서 공유하는 CloudWatch 유틸리티 모음.

Usage:
    from plugins.cloudwatch.common import (
        MetricQuery,
        batch_get_metrics,
        build_ec2_metric_queries,
        build_lambda_metric_queries,
    )
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
