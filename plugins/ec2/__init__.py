"""
plugins/ec2 - EC2 Analysis Tools

Analyze EC2, EBS, EIP and other compute resources
"""

CATEGORY = {
    "name": "ec2",
    "display_name": "EC2",
    "description": "EC2 및 컴퓨팅 리소스 관리",
    "description_en": "EC2 and Compute Resource Management",
    "aliases": ["compute", "ebs", "eip"],
}

TOOLS = [
    {
        "name": "미사용 EC2 인스턴스 탐지",
        "name_en": "Unused EC2 Instance Detection",
        "description": "유휴/저사용 EC2 인스턴스 탐지 (CloudWatch 기반)",
        "description_en": "Detect idle/underutilized EC2 instances (CloudWatch-based)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
    {
        "name": "미사용 EBS 볼륨 탐지",
        "name_en": "Unused EBS Volume Detection",
        "description": "미연결 EBS 볼륨 탐지",
        "description_en": "Detect unattached EBS volumes",
        "permission": "read",
        "module": "ebs_audit",
        "area": "unused",
    },
    {
        "name": "미사용 EIP 탐지",
        "name_en": "Unused EIP Detection",
        "description": "미연결 Elastic IP 탐지",
        "description_en": "Detect unattached Elastic IPs",
        "permission": "read",
        "module": "eip_audit",
        "area": "unused",
    },
    {
        "name": "미사용 EBS Snapshot 탐지",
        "name_en": "Unused EBS Snapshot Detection",
        "description": "고아/오래된 EBS Snapshot 탐지",
        "description_en": "Detect orphaned/old EBS Snapshots",
        "permission": "read",
        "module": "snapshot_audit",
        "area": "unused",
    },
    {
        "name": "미사용 AMI 탐지",
        "name_en": "Unused AMI Detection",
        "description": "미사용 AMI 탐지",
        "description_en": "Detect unused AMIs",
        "permission": "read",
        "module": "ami_audit",
        "area": "unused",
    },
]
