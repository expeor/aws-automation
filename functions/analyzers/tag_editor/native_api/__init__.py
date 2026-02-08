"""
functions/analyzers/tag_editor/native_api - Native AWS API 태그 수집/적용 모듈

ResourceGroupsTaggingAPI가 불완전하거나 태그 보존이 필요한 서비스용
Native API 수집/적용 모듈입니다.

지원 서비스:
    - CloudWatch Logs: list_tags_for_resource, tag_resource 사용
    - S3 Buckets: get_bucket_tagging, put_bucket_tagging 사용 (기존 태그 보존)
"""

from .cloudwatch_logs import apply_log_group_tag, collect_log_group_tags
from .s3_buckets import apply_s3_bucket_tag, collect_s3_bucket_tags

# Native API가 필요한 리소스 타입
NATIVE_API_RESOURCE_TYPES = {
    "logs:log-group",  # CloudWatch Logs
    "s3:bucket",  # S3 Buckets
}

__all__ = [
    # CloudWatch Logs
    "collect_log_group_tags",
    "apply_log_group_tag",
    # S3 Buckets
    "collect_s3_bucket_tags",
    "apply_s3_bucket_tag",
    # Constants
    "NATIVE_API_RESOURCE_TYPES",
]
