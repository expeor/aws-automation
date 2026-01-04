"""
plugins/vpc/ip_search - IP 검색 도구

통합 검색: Public (클라우드 대역) + Private (AWS ENI) 동시 검색
다양한 쿼리 지원: IP, CIDR, ENI ID, VPC ID, Instance ID, 텍스트 등

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
    - REQUIRED_PERMISSIONS: 필요한 AWS 권한 목록
"""

from plugins.vpc.ip_search.main import run

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "ec2:DescribeNetworkInterfaces",
    ],
}

__all__: list[str] = ["run", "REQUIRED_PERMISSIONS"]
