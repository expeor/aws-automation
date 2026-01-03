"""
plugins/health - AWS Health 서비스 도구

Personal Health Dashboard (PHD) 이벤트 분석, 패치 보고서 등
"""

CATEGORY = {
    "name": "health",
    "display_name": "Health Dashboard",
    "description": "AWS Health 이벤트 및 패치 관리",
    "aliases": ["phd", "patch", "maintenance"],
}

TOOLS = [
    {
        "name": "PHD 전체 분석",
        "description": "AWS Personal Health Dashboard 전체 이벤트 분석 및 보고서 생성",
        "permission": "read",
        "module": "phd",
        "function": "run_analysis",
        "area": "monitoring",
    },
    {
        "name": "필수 패치 분석",
        "description": "예정된 패치/유지보수 이벤트 분석 및 보고서 생성",
        "permission": "read",
        "module": "phd",
        "function": "run_patch_analysis",
        "area": "monitoring",
    },
    {
        "name": "서비스 장애 현황",
        "description": "현재 진행 중인 AWS 서비스 장애 조회",
        "permission": "read",
        "module": "phd",
        "function": "run_issues",
        "area": "monitoring",
    },
]
