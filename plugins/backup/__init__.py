"""
plugins/backup - AWS Backup Management Tools
"""

CATEGORY = {
    "name": "backup",
    "display_name": "AWS Backup",
    "description": "AWS Backup 현황 및 분석",
    "description_en": "AWS Backup Status and Analysis",
    "aliases": ["bkp", "vault", "recovery"],
}

TOOLS = [
    {
        "name": "Backup 현황",
        "name_en": "Backup Status",
        "description": "Backup Vault, Plan, 최근 작업 현황 분석",
        "description_en": "Backup Vault, Plan, recent job status analysis",
        "permission": "read",
        "module": "audit",
        "area": "inventory",
    },
    {
        "name": "통합 백업 현황",
        "name_en": "Comprehensive Backup Status",
        "description": "AWS Backup + 서비스별 자체 백업 현황 통합 분석 (RDS, DynamoDB, EFS, FSx)",
        "description_en": "AWS Backup + service-native backup status (RDS, DynamoDB, EFS, FSx)",
        "permission": "read",
        "module": "comprehensive",
        "area": "inventory",
    },
]
