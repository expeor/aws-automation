"""
plugins/resource_explorer - AWS Resource Explorer

리소스 인벤토리 수집 및 종합 보고서 제공.

Usage:
    from plugins.resource_explorer.common import InventoryCollector

    collector = InventoryCollector(ctx)
    instances = collector.collect_ec2()
"""

CATEGORY = {
    "name": "resource_explorer",
    "display_name": "Resource Explorer",
    "description": "AWS 리소스 인벤토리 종합 조회",
    "description_en": "AWS Resource Inventory Explorer",
    "aliases": ["inventory", "cmdb", "resources"],
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
    },
]
