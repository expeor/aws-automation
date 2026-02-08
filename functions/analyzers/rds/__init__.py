"""
functions/analyzers/rds - RDS 및 Aurora 데이터베이스 분석 도구

RDS/Aurora 인스턴스와 스냅샷의 사용 현황을 분석하고,
유휴/저사용 인스턴스 및 오래된 수동 스냅샷을 탐지합니다.

도구 목록:
    - snapshot_audit: 오래된 수동 스냅샷 탐지 (RDS/Aurora)
    - unused: 유휴/저사용 RDS 인스턴스 탐지
"""

CATEGORY = {
    "name": "rds",
    "display_name": "RDS",
    "description": "RDS 및 Aurora 데이터베이스 관리",
    "description_en": "RDS and Aurora Database Management",
    "aliases": ["database", "aurora", "db"],
}

TOOLS = [
    {
        "name": "미사용 RDS Snapshot 탐지",
        "name_en": "Unused RDS Snapshot Detection",
        "description": "오래된 수동 스냅샷 탐지 (RDS/Aurora)",
        "description_en": "Detect old manual snapshots (RDS/Aurora)",
        "permission": "read",
        "module": "snapshot_audit",
        "area": "unused",
    },
    {
        "name": "미사용 RDS 인스턴스 탐지",
        "name_en": "Unused RDS Instance Detection",
        "description": "유휴/저사용 RDS 인스턴스 탐지",
        "description_en": "Detect idle/underutilized RDS instances",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
