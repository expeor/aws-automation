"""
plugins/s3 - S3 스토리지 관리 도구

버킷 현황, 미사용 버킷, 스토리지 분석 등

도구 목록:
    - 빈 버킷 분석: 객체가 없는 빈 S3 버킷 탐지
"""

CATEGORY = {
    "name": "s3",
    "description": "S3 스토리지 관리",
    "aliases": ["storage", "bucket"],
}

TOOLS = [
    {
        "name": "빈 버킷 분석",
        "description": "객체가 없는 빈 S3 버킷 탐지",
        "permission": "read",
        "module": "empty_bucket",
        "area": "cost",
    },
]
