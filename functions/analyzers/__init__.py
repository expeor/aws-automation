"""
functions/analyzers - AWS 서비스별 분석 도구

EC2, VPC, RDS, IAM 등 30개 이상의 AWS 서비스 카테고리에 대한
분석 도구를 제공합니다. 각 서비스 디렉토리는 CATEGORY와 TOOLS를
정의하는 플러그인 구조를 따릅니다.

구조:
    functions/analyzers/
    ├── {service}/       # AWS 서비스별 도구 (ec2, rds, vpc, iam, kms, ...)
    ├── cost/            # 비용 분석 (Cost Optimization Hub, pricing)
    ├── health/          # AWS Health 이벤트 및 패치 관리
    ├── sso/             # IAM Identity Center 보안 감사
    └── tag_editor/      # 리소스 태그 관리 및 MAP 2.0
"""
