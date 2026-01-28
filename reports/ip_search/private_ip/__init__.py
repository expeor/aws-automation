"""
plugins/vpc/ip_search/private_ip - Private IP Search Tool

Search AWS ENI cache for private IP addresses.
Supports multi-profile/multi-account cache management.
"""

from .tool import run

__all__ = ["run"]
