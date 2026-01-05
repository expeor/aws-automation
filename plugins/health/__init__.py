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
        "module": "analysis",
        "area": "inventory",
        "is_global": True,  # AWS Health API는 us-east-1 고정 - 리전 선택 불필요
    },
    {
        "name": "필수 패치 분석",
        "description": "예정된 패치/유지보수 이벤트 분석 및 보고서 생성",
        "permission": "read",
        "module": "patch_analysis",
        "area": "audit",
        "is_global": True,  # AWS Health API는 us-east-1 고정 - 리전 선택 불필요
    },
    {
        "name": "서비스 장애 현황",
        "description": "현재 진행 중인 AWS 서비스 장애 조회",
        "permission": "read",
        "module": "issues",
        "area": "inventory",
        "is_global": True,  # AWS Health API는 us-east-1 고정 - 리전 선택 불필요
    },
]
