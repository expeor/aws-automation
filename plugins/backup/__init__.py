"""
plugins/backup - AWS Backup 분석 도구

Backup Vault, Plan, Job 현황 분석
"""

CATEGORY = {
    "name": "backup",
    "display_name": "AWS Backup",
    "description": "AWS Backup 현황 및 분석",
    "aliases": ["bkp", "vault", "recovery"],
}

TOOLS = [
    {
        "name": "Backup 현황",
        "description": "Backup Vault, Plan, 최근 작업 현황 분석",
        "permission": "read",
        "module": "audit",
        "area": "backup",
    },
]
