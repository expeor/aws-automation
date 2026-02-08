"""functions/reports/ip_search/private_ip/__init__.py - Private IP Search Tool.

AWS ENI 캐시를 기반으로 내부(Private) IP 주소가 할당된 리소스를 검색합니다.
멀티 프로파일/멀티 계정 캐시 관리를 지원하며, IP, CIDR, VPC ID, ENI ID,
텍스트 검색 등 다양한 검색 방식을 제공합니다.
"""

from .tool import run

__all__ = ["run"]
