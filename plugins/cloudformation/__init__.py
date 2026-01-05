"""
plugins/cloudformation - CloudFormation 관리 도구

CloudFormation Stack 리소스 검색, 분석 등

## 사용 케이스
- 특정 리소스가 어떤 Stack에서 생성되었는지 확인
- 리소스 삭제 전 CloudFormation 의존성 확인
- 수동 생성 vs CFN 관리 리소스 구분
"""

CATEGORY = {
    "name": "cloudformation",
    "display_name": "CloudFormation",
    "description": "CloudFormation Stack 관리 및 분석",
    "aliases": ["cfn", "stack"],
}

TOOLS = [
    {
        "name": "CFN 리소스 검색",
        "description": "Physical ID 또는 Resource Type으로 CloudFormation Stack 리소스 검색",
        "permission": "read",
        "module": "resource_finder",
        "function": "run_search",
        "area": "search",
    },
    {
        "name": "CFN Physical ID 검색",
        "description": "Physical ID로 해당 리소스가 속한 CloudFormation Stack 찾기",
        "permission": "read",
        "module": "resource_finder",
        "function": "run_search_by_physical_id",
        "area": "search",
    },
]
