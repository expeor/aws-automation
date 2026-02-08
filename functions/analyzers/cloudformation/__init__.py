"""
functions/analyzers/cloudformation - CloudFormation Stack 관리 및 분석 도구

CloudFormation Stack의 리소스를 Physical ID 또는 Resource Type으로
검색하고, 특정 리소스가 속한 Stack을 찾는 기능을 제공합니다.

도구 목록:
    - resource_finder (run_search): Physical ID 또는 Resource Type으로 Stack 리소스 검색
    - resource_finder (run_search_by_physical_id): Physical ID로 해당 리소스가 속한 Stack 찾기
"""

CATEGORY = {
    "name": "cloudformation",
    "display_name": "CloudFormation",
    "description": "CloudFormation Stack 관리 및 분석",
    "description_en": "CloudFormation Stack Management and Analysis",
    "aliases": ["cfn", "stack"],
}

TOOLS = [
    {
        "name": "CFN 리소스 조회",
        "name_en": "CFN Resource Lookup",
        "description": "Physical ID 또는 Resource Type으로 CloudFormation Stack 리소스 검색",
        "description_en": "Search CloudFormation Stack resources by Physical ID or Resource Type",
        "permission": "read",
        "module": "resource_finder",
        "function": "run_search",
        "area": "search",
    },
    {
        "name": "CFN Physical ID 조회",
        "name_en": "CFN Physical ID Lookup",
        "description": "Physical ID로 해당 리소스가 속한 CloudFormation Stack 찾기",
        "description_en": "Find CloudFormation Stack by Physical ID",
        "permission": "read",
        "module": "resource_finder",
        "function": "run_search_by_physical_id",
        "area": "search",
    },
]
