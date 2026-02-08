"""reports - 종합 리포트 모듈

여러 AWS 서비스를 취합하는 종합 보고서를 제공합니다.

하위 모듈:
- cost_dashboard: 미사용 리소스 종합 보고서
- inventory: AWS 리소스 인벤토리
- ip_search: IP 검색기 (Public/Private)
- log_analyzer: ALB 로그 분석
- scheduled: 정기 작업 (일간/월간/분기/반기/연간)
"""

CATEGORY = {
    "name": "report",
    "display_name": "Reports",
    "description": "종합 리포트 (인벤토리, 비용, IP, 로그, 정기작업)",
    "description_en": "Comprehensive Reports (Inventory, Cost, IP, Log, Scheduled)",
    "aliases": ["reports", "rpt"],
}

TOOLS = [
    {
        "name": "미사용 리소스 종합",
        "name_en": "Unused Resources Dashboard",
        "description": "NAT, ENI, EBS, EIP, ELB, Snapshot 등 미사용 리소스 종합 보고서",
        "description_en": "Comprehensive unused resources report",
        "permission": "read",
        "ref": "cost_dashboard/orchestrator",
        "area": "cost",
    },
    {
        "name": "리소스 인벤토리",
        "name_en": "Resource Inventory",
        "description": "EC2, VPC, ELB 등 주요 리소스 종합 인벤토리",
        "description_en": "Comprehensive resource inventory",
        "permission": "read",
        "ref": "inventory/inventory",
        "area": "inventory",
    },
    {
        "name": "Public IP 검색",
        "name_en": "Public IP Search",
        "description": "AWS, GCP, Azure, Oracle 등 클라우드 IP 대역 검색",
        "description_en": "Cloud provider IP range search",
        "permission": "read",
        "ref": "ip_search/public_ip.tool",
        "area": "search",
    },
    {
        "name": "Private IP 검색",
        "name_en": "Private IP Search",
        "description": "AWS ENI 캐시 기반 내부 IP 검색",
        "description_en": "AWS ENI cache-based internal IP search",
        "permission": "read",
        "ref": "ip_search/private_ip.tool",
        "area": "search",
    },
    {
        "name": "ALB 로그 분석",
        "name_en": "ALB Log Analysis",
        "description": "S3에 저장된 ALB 액세스 로그 분석",
        "description_en": "Analyze ALB access logs stored in S3",
        "permission": "read",
        "ref": "elb/alb_log",
        "area": "log",
        "single_region_only": True,
    },
    {
        "name": "정기 작업 관리",
        "name_en": "Scheduled Operations",
        "description": "일간/월간/분기/반기/연간 정기 작업 관리",
        "description_en": "Daily/Monthly/Quarterly/Biannual/Annual scheduled operations",
        "permission": "read",
        "ref": "scheduled/menu",
        "require_session": False,
        "is_menu": True,  # CategoryStep에서 특별 처리
        "area": "inventory",  # 관리 도구이므로 inventory 분류
    },
]

__all__: list[str] = ["CATEGORY", "TOOLS"]
