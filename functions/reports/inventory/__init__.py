"""functions/reports/inventory/__init__.py - AWS 리소스 인벤토리 패키지.

EC2, VPC, ELB 등 주요 AWS 리소스의 종합 인벤토리를 수집하고
Excel 보고서로 생성합니다. 60개 이상의 리소스 타입을 카테고리별로 수집합니다.

Example:
    >>> from core.shared.aws.inventory import InventoryCollector
    >>> collector = InventoryCollector(ctx)
    >>> instances = collector.collect_ec2()
"""

CATEGORY = {
    "name": "inventory",
    "display_name": "Resource Inventory",
    "description": "AWS 리소스 인벤토리 종합 조회",
    "description_en": "AWS Resource Inventory Explorer",
    "aliases": ["resource_explorer", "cmdb", "resources"],
}

TOOLS = [
    {
        "name": "종합 인벤토리",
        "name_en": "Comprehensive Inventory",
        "description": "EC2, VPC, ELB 등 주요 리소스 종합 인벤토리 조회",
        "description_en": "Comprehensive inventory of EC2, VPC, ELB and other major resources",
        "permission": "read",
        "module": "inventory",
        "area": "inventory",
        "timeline_phases": ["리소스 수집", "Excel 생성", "요약"],
    },
]
