"""
plugins/health - AWS Health Dashboard Tools
"""

CATEGORY = {
    "name": "health",
    "display_name": "Health",
    "description": "AWS Health 이벤트 및 패치 관리",
    "description_en": "AWS Health Events and Patch Management",
    "aliases": ["phd", "patch", "maintenance"],
}

TOOLS = [
    {
        "name": "Health 이벤트 현황",
        "name_en": "Health Event Inventory",
        "description": "AWS Personal Health Dashboard 전체 이벤트 분석 및 보고서 생성",
        "description_en": "AWS Personal Health Dashboard full event analysis and report",
        "permission": "read",
        "module": "analysis",
        "area": "inventory",
        "is_global": True,
    },
    {
        "name": "필수 패치 현황",
        "name_en": "Required Patch Status",
        "description": "예정된 패치/유지보수 이벤트 분석 및 보고서 생성",
        "description_en": "Scheduled patch/maintenance event analysis and report",
        "permission": "read",
        "module": "patch_analysis",
        "area": "inventory",
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
