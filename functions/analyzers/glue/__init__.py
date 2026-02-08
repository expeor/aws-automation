"""
functions/analyzers/glue - AWS Glue ETL 작업 관리 및 최적화 도구

Glue ETL 작업의 실행 기록을 분석하고
미사용/실패 Glue 작업을 탐지합니다.

도구 목록:
    - unused: 미사용/실패 Glue 작업 탐지 (실행 기록 기반)
"""

CATEGORY = {
    "name": "glue",
    "display_name": "Glue",
    "description": "AWS Glue ETL 작업 관리 및 최적화",
    "description_en": "AWS Glue ETL Job Management and Optimization",
    "aliases": ["etl"],
}

TOOLS = [
    {
        "name": "미사용 작업 분석",
        "name_en": "Unused Job Analysis",
        "description": "미사용/실패 Glue 작업 탐지 (실행 기록 기반)",
        "description_en": "Detect unused/failed Glue jobs based on execution history",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
