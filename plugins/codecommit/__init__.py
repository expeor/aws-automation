"""
plugins/codecommit - CodeCommit Repository Management Tools
"""

CATEGORY = {
    "name": "codecommit",
    "display_name": "CodeCommit",
    "description": "CodeCommit 리포지토리 관리 및 분석",
    "description_en": "CodeCommit Repository Management and Analysis",
    "aliases": ["cc", "repo"],
}

TOOLS = [
    {
        "name": "CodeCommit 현황",
        "name_en": "CodeCommit Inventory",
        "description": "CodeCommit 리포지토리 및 브랜치 현황 분석",
        "description_en": "CodeCommit repository and branch status analysis",
        "permission": "read",
        "module": "unused",
        "function": "run_audit",
        "area": "inventory",
    },
    {
        "name": "미사용 리포지토리 탐지",
        "name_en": "Unused Repository Detection",
        "description": "브랜치가 없는 빈 리포지토리 목록 조회",
        "description_en": "Detect repositories with no branches",
        "permission": "read",
        "module": "unused",
        "function": "run_empty_repos",
        "area": "unused",
    },
]
