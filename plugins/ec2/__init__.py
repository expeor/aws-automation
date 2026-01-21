"""
plugins/ec2 - EC2 관련 분석 도구

EC2, EBS, EIP 등 컴퓨팅 리소스 분석
"""

CATEGORY = {
    "name": "ec2",
    "display_name": "EC2",
    "description": "EC2 및 컴퓨팅 리소스 관리",
    "aliases": ["compute", "ebs", "eip"],
}

TOOLS = [
    {
        "name": "EC2 인스턴스 미사용 분석",
        "description": "유휴/저사용 EC2 인스턴스 탐지 (CloudWatch 기반)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
    {
        "name": "EBS 미사용 분석",
        "description": "미사용 EBS 볼륨 탐지 및 비용 절감 기회 식별",
        "permission": "read",
        "module": "ebs_audit",
        "area": "unused",
    },
    {
        "name": "EIP 미사용 분석",
        "description": "미연결 Elastic IP 탐지",
        "permission": "read",
        "module": "eip_audit",
        "area": "unused",
    },
    {
        "name": "EBS Snapshot 미사용 분석",
        "description": "고아/오래된 EBS Snapshot 탐지",
        "permission": "read",
        "module": "snapshot_audit",
        "area": "unused",
    },
    {
        "name": "AMI 미사용 분석",
        "description": "미사용 AMI 탐지 (스냅샷 비용 절감)",
        "permission": "read",
        "module": "ami_audit",
        "area": "unused",
    },
]
