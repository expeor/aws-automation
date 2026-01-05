"""
plugins/rds - RDS 분석 도구

RDS, Aurora 데이터베이스 관련 분석
"""

CATEGORY = {
    "name": "rds",
    "display_name": "RDS",
    "description": "RDS 및 Aurora 데이터베이스 관리",
    "aliases": ["database", "aurora", "db"],
}

TOOLS = [
    {
        "name": "RDS Snapshot 미사용 분석",
        "description": "오래된 수동 스냅샷 탐지 (RDS/Aurora)",
        "permission": "read",
        "module": "snapshot_audit",
        "area": "unused",
    },
    {
        "name": "RDS 유휴 인스턴스 분석",
        "description": "유휴/저사용 RDS 인스턴스 탐지",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
