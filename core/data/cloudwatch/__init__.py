"""
core/data/cloudwatch - CloudWatch Metrics Services

Re-export from core/cloudwatch for the new core/data/ architecture.
This module provides the canonical import path for CloudWatch services.

Usage (new):
    from core.data.cloudwatch import MetricQuery, batch_get_metrics

Usage (legacy, still supported):
    from core.cloudwatch import MetricQuery, batch_get_metrics
"""

# Re-export everything from the original module
from core.cloudwatch import (
    MetricQuery,
    batch_get_metrics,
    sanitize_metric_id,
)

__all__ = [
    "MetricQuery",
    "batch_get_metrics",
    "sanitize_metric_id",
]
