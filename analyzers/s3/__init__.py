"""
plugins/s3 - S3 Storage Management Tools

Bucket inventory, unused buckets, storage analysis

Tools:
    - Empty Bucket Analysis: Detect S3 buckets with no objects
"""

CATEGORY = {
    "name": "s3",
    "display_name": "S3",
    "description": "S3 스토리지 관리",
    "description_en": "S3 Storage Management",
    "aliases": ["storage", "bucket"],
}

TOOLS = [
    {
        "name": "미사용 S3 버킷 탐지",
        "name_en": "Unused S3 Bucket Detection",
        "description": "객체가 없는 빈 S3 버킷 탐지",
        "description_en": "Detect S3 buckets with no objects",
        "permission": "read",
        "module": "empty_bucket",
        "area": "unused",
    },
]
