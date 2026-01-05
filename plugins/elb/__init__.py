"""
plugins/elb - Elastic Load Balancing 분석 도구

ALB, NLB, CLB, GWLB 등 모든 로드밸런서 유형을 포함합니다.

하위 서비스:
    - alb: Application Load Balancer
    - nlb: Network Load Balancer
    - clb: Classic Load Balancer
    - gwlb: Gateway Load Balancer

도구 목록:
    - 미사용 ELB: 타겟이 없는 로드밸런서 탐지
    - Target Group 분석: 미연결/빈 타겟 그룹 탐지
    - ELB Security Audit: SSL/TLS, WAF, 액세스 로그 보안 감사
    - CLB Migration Advisor: CLB→ALB/NLB 마이그레이션 분석
    - Listener Rules 분석: ALB 리스너 규칙 복잡도/최적화 분석
    - ALB 로그 분석: S3에 저장된 ALB 액세스 로그 분석

CLI 사용법:
    aa elb     → 모든 ELB 도구
    aa alb     → ALB 전용 도구만
    aa nlb     → NLB 전용 도구만
    aa clb     → CLB 전용 도구만
"""

CATEGORY = {
    "name": "elb",
    "display_name": "ELB",
    "description": "Elastic Load Balancing (ALB/NLB/CLB/GWLB)",
    "aliases": ["loadbalancer", "lb"],
    # 하위 서비스 정의 - 각각 별도 CLI 명령어로 등록됨
    "sub_services": ["alb", "nlb", "clb", "gwlb"],
}

TOOLS = [
    # === Unused 영역 (서브타입별) ===
    {
        "name": "미사용 ELB",
        "description": "타겟이 없는 로드밸런서 탐지 (ALB/NLB/CLB/GWLB 전체)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
    {
        "name": "ALB 미사용 분석",
        "description": "타겟이 없는 ALB 탐지",
        "permission": "read",
        "module": "alb_unused",
        "area": "unused",
        "sub_service": "alb",
    },
    {
        "name": "NLB 미사용 분석",
        "description": "타겟이 없는 NLB 탐지",
        "permission": "read",
        "module": "nlb_unused",
        "area": "unused",
        "sub_service": "nlb",
    },
    {
        "name": "CLB 미사용 분석",
        "description": "인스턴스가 없는 CLB 탐지",
        "permission": "read",
        "module": "clb_unused",
        "area": "unused",
        "sub_service": "clb",
    },
    # === Cost 영역 ===
    {
        "name": "Target Group 분석",
        "description": "미연결/빈 타겟 그룹 탐지 (ALB/NLB)",
        "permission": "read",
        "module": "target_group_audit",
        "area": "cost",
    },
    {
        "name": "CLB Migration Advisor",
        "description": "CLB→ALB/NLB 마이그레이션 분석 및 추천",
        "permission": "read",
        "module": "migration_advisor",
        "area": "cost",
        "sub_service": "clb",
    },
    # === Security 영역 ===
    {
        "name": "ELB Security Audit",
        "description": "SSL/TLS, WAF, 인증서, 액세스 로그 보안 감사",
        "permission": "read",
        "module": "security_audit",
        "area": "security",
    },
    # === Audit 영역 (ALB 전용) ===
    {
        "name": "ALB Listener Rules 분석",
        "description": "ALB 리스너 규칙 복잡도 및 최적화 분석",
        "permission": "read",
        "module": "listener_rules",
        "area": "audit",
        "sub_service": "alb",
    },
    # === Log 영역 (ALB 전용) ===
    {
        "name": "ALB 로그 분석",
        "description": "S3에 저장된 ALB 액세스 로그 분석",
        "permission": "read",
        "module": "alb_log",
        "area": "log",
        "single_region_only": True,
        "sub_service": "alb",
    },
]
