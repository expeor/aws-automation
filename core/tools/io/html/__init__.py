"""DEPRECATED: Use shared.io.html instead.

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드에서는 shared.io.html를 사용하세요.
"""

import warnings

from shared.io.html import (
    DEFAULT_TOP_N,
    AWSReport,
    ChartSize,
    HTMLReport,
    ResourceItem,
    aggregate_by_group,
    build_treemap_hierarchy,
    create_aws_report,
    group_top_n,
    open_in_browser,
)

warnings.warn(
    "core.tools.io.html is deprecated. Use shared.io.html instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    # 저수준 API
    "HTMLReport",
    "ChartSize",
    "open_in_browser",
    # 고수준 API (AWS 리포트)
    "AWSReport",
    "ResourceItem",
    "create_aws_report",
    # 대용량 데이터 헬퍼
    "group_top_n",
    "aggregate_by_group",
    "build_treemap_hierarchy",
    "DEFAULT_TOP_N",
]
