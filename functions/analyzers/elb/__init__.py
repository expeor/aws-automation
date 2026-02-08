"""
plugins/elb - Elastic Load Balancing Analysis Tools

Includes all load balancer types: ALB, NLB, CLB, GWLB
"""

CATEGORY = {
    "name": "elb",
    "display_name": "ELB",
    "description": "Elastic Load Balancing (ALB/NLB/CLB/GWLB)",
    "description_en": "Elastic Load Balancing (ALB/NLB/CLB/GWLB)",
    "aliases": ["loadbalancer", "lb"],
    "sub_services": ["alb", "nlb", "clb", "gwlb"],
}

TOOLS = [
    # Unused resource detection
    {
        "name": "미사용 ELB 탐지",
        "name_en": "Unused ELB Detection",
        "description": "타겟이 없는 로드밸런서 탐지 (ALB/NLB/CLB/GWLB)",
        "description_en": "Detect load balancers without targets (all types)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
    {
        "name": "미사용 Target Group 탐지",
        "name_en": "Unused Target Group Detection",
        "description": "미연결/빈 타겟 그룹 탐지",
        "description_en": "Detect unattached/empty target groups",
        "permission": "read",
        "module": "target_group_audit",
        "area": "unused",
    },
    # Security
    {
        "name": "ELB 보안 점검",
        "name_en": "ELB Security Check",
        "description": "SSL/TLS, WAF, 인증서, 액세스 로그 보안 점검",
        "description_en": "SSL/TLS, WAF, certificate, access log security check",
        "permission": "read",
        "module": "security_audit",
        "area": "security",
    },
    # Cost optimization
    {
        "name": "CLB 마이그레이션 검토",
        "name_en": "CLB Migration Review",
        "description": "CLB→ALB/NLB 마이그레이션 분석",
        "description_en": "CLB to ALB/NLB migration analysis",
        "permission": "read",
        "module": "migration_advisor",
        "area": "cost",
        "sub_service": "clb",
    },
    # Inventory
    {
        "name": "ALB Listener Rules 현황",
        "name_en": "ALB Listener Rules Inventory",
        "description": "ALB 리스너 규칙 복잡도 및 현황",
        "description_en": "ALB listener rule complexity and inventory",
        "permission": "read",
        "module": "listener_rules",
        "area": "inventory",
        "sub_service": "alb",
    },
    # Log analysis
    {
        "name": "ALB 로그 분석",
        "name_en": "ALB Log Analysis",
        "description": "S3에 저장된 ALB 액세스 로그 분석",
        "description_en": "Analyze ALB access logs stored in S3",
        "permission": "read",
        "module": "alb_log",
        "area": "log",
        "single_region_only": True,
        "sub_service": "alb",
    },
    # Inventory
    {
        "name": "ELB 인벤토리",
        "name_en": "ELB Inventory",
        "description": "모든 유형의 로드밸런서 및 Target Group 현황 조회",
        "description_en": "List all load balancers and target groups",
        "permission": "read",
        "module": "inventory",
        "area": "inventory",
    },
]
