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
    # === Cost 영역 ===
    {
        "name": "미사용 ELB",
        "description": "타겟이 없는 로드밸런서 탐지 (ALB/NLB/CLB/GWLB)",
        "permission": "read",
        "module": "unused",
        "area": "cost",
        # sub_service 미지정 → aa elb에서만 표시 (전체 LB 대상)
    },
    {
        "name": "Target Group 분석",
        "description": "미연결/빈 타겟 그룹 탐지 (ALB/NLB)",
        "permission": "read",
        "module": "target_group_audit",
        "area": "cost",
        # sub_service 미지정 → aa elb에서만 표시
    },
    {
        "name": "CLB Migration Advisor",
        "description": "CLB→ALB/NLB 마이그레이션 분석 및 추천",
        "permission": "read",
        "module": "migration_advisor",
        "area": "cost",
        "sub_service": "clb",  # CLB 전용
    },
    # === Security 영역 ===
    {
        "name": "ELB Security Audit",
        "description": "SSL/TLS, WAF, 인증서, 액세스 로그 보안 감사",
        "permission": "read",
        "module": "security_audit",
        "area": "security",
        # sub_service 미지정 → aa elb에서만 표시 (전체 LB 대상)
    },
    # === Operational 영역 (ALB 전용) ===
    {
        "name": "ALB Listener Rules 분석",
        "description": "ALB 리스너 규칙 복잡도 및 최적화 분석",
        "permission": "read",
        "module": "listener_rules",
        "area": "operational",
        "sub_service": "alb",  # ALB 전용
    },
    {
        "name": "ALB 로그 분석",
        "description": "S3에 저장된 ALB 액세스 로그 분석",
        "permission": "read",
        "module": "alb_log",
        "area": "operational",
        "single_region_only": True,
        "sub_service": "alb",  # ALB 전용
    },
]
