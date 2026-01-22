"""
plugins/rds - RDS Analysis Tools

RDS and Aurora database analysis
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
        "name": "RDS Snapshot 미사용 분석",
        "name_en": "Unused RDS Snapshot Analysis",
        "description": "오래된 수동 스냅샷 탐지 (RDS/Aurora)",
        "description_en": "Detect old manual snapshots (RDS/Aurora)",
        "permission": "read",
        "module": "snapshot_audit",
        "area": "unused",
    },
    {
        "name": "RDS 유휴 인스턴스 분석",
        "name_en": "Idle RDS Instance Analysis",
        "description": "유휴/저사용 RDS 인스턴스 탐지",
        "description_en": "Detect idle/underutilized RDS instances",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
