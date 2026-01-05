"""
plugins/codecommit - CodeCommit 리포지토리 관리 도구

CodeCommit 리포지토리 및 브랜치 현황 분석
빈 리포지토리 탐지
"""

CATEGORY = {
    "name": "codecommit",
    "display_name": "CodeCommit",
    "description": "CodeCommit 리포지토리 관리 및 분석",
    "aliases": ["cc", "repo"],
}

TOOLS = [
    {
        "name": "리포지토리 분석",
        "description": "CodeCommit 리포지토리 및 브랜치 현황 분석",
        "permission": "read",
        "module": "unused",
        "function": "run_audit",
        "area": "inventory",
    },
    {
        "name": "빈 리포지토리 조회",
        "description": "브랜치가 없는 빈 리포지토리 목록 조회",
        "permission": "read",
        "module": "unused",
        "function": "run_empty_repos",
        "area": "unused",
    },
]
