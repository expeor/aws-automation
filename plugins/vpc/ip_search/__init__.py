"""
plugins/vpc/ip_search - IP Search Tools

Submodules:
    - public_ip: Cloud provider IP range search (AWS, GCP, Azure, Oracle)
    - private_ip: AWS ENI cache-based internal IP search

Each submodule provides its own `run(ctx)` entry point.
"""

# Submodules export their own run() functions
# Import them directly from the submodule:
#   from plugins.vpc.ip_search.public_ip import run
#   from plugins.vpc.ip_search.private_ip import run

__all__: list[str] = []
