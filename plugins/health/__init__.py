"""
plugins/health - AWS Health Dashboard Tools
"""

CATEGORY = {
    "name": "health",
    "display_name": "Health Dashboard",
    "description": "AWS Health 이벤트 및 패치 관리",
    "description_en": "AWS Health Events and Patch Management",
    "aliases": ["phd", "patch", "maintenance"],
}

TOOLS = [
    {
        "name": "PHD 전체 분석",
        "name_en": "PHD Full Analysis",
        "description": "AWS Personal Health Dashboard 전체 이벤트 분석 및 보고서 생성",
        "description_en": "AWS Personal Health Dashboard full event analysis and report",
        "permission": "read",
        "module": "analysis",
        "area": "inventory",
        "is_global": True,
    },
    {
        "name": "필수 패치 분석",
        "name_en": "Required Patch Analysis",
        "description": "예정된 패치/유지보수 이벤트 분석 및 보고서 생성",
        "description_en": "Scheduled patch/maintenance event analysis and report",
        "permission": "read",
        "module": "patch_analysis",
        "area": "audit",
        "is_global": True,
    },
    {
        "name": "서비스 장애 현황",
        "name_en": "Service Issue Status",
        "description": "현재 진행 중인 AWS 서비스 장애 조회",
        "description_en": "View ongoing AWS service issues",
        "permission": "read",
        "module": "issues",
        "area": "inventory",
        "is_global": True,
    },
]
