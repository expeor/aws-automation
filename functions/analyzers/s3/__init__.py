"""
functions/analyzers/s3 - S3 스토리지 관리 도구

S3 버킷의 사용 현황을 분석하고
객체가 없는 빈 버킷을 탐지합니다.

도구 목록:
    - empty_bucket: 객체가 없는 빈 S3 버킷 탐지
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
