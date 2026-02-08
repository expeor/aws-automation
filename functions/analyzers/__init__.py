"""
plugins/ - AWS Automation 플러그인 모듈

플러그인 구조:
    plugins/
    ├── analysis/        # 통합 분석 플랫폼 (cost, security, inventory, network, compliance, log, report)
    ├── {service}/       # AWS 서비스별 도구 (rds, ec2, s3, iam, kms, ...)
    ├── trusted_advisor/ # Trusted Advisor 점검
    └── identity_center/ # IAM Identity Center
"""
