"""
functions/analyzers/ec2 - EC2 분석 도구

EC2 인스턴스, EBS 볼륨, EIP, Snapshot, AMI 등 컴퓨팅 리소스를
분석하고 미사용/저사용 리소스를 탐지합니다. 보안 점검(EBS 암호화)과
리소스 정리(Snapshot/AMI 삭제) 기능도 제공합니다.

도구 목록:
    - unused: 유휴/저사용 EC2 인스턴스 탐지 (CloudWatch 기반)
    - ebs_audit: 미연결 EBS 볼륨 탐지
    - ebs_encryption: 암호화되지 않은 EBS 볼륨 및 연결된 인스턴스 탐지
    - eip_audit: 미연결 Elastic IP 탐지
    - snapshot_audit: 고아/오래된 EBS Snapshot 탐지
    - ami_audit: 미사용 AMI 탐지
    - inventory: EC2 인스턴스 및 Security Group 인벤토리 조회
    - snapshot_cleanup: 고아/오래된 EBS Snapshot 삭제 (Dry-run 지원)
    - ami_cleanup: 미사용 AMI 및 연관 스냅샷 삭제 (Dry-run 지원)
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
        "name": "암호화되지 않은 EBS 볼륨 탐지",
        "name_en": "Unencrypted EBS Volume Detection",
        "description": "암호화되지 않은 EBS 볼륨 및 연결된 인스턴스 탐지",
        "description_en": "Detect unencrypted EBS volumes and attached instances",
        "permission": "read",
        "module": "ebs_encryption",
        "area": "security",
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
    {
        "name": "EC2 인벤토리",
        "name_en": "EC2 Inventory",
        "description": "EC2 인스턴스 및 Security Group 인벤토리 조회",
        "description_en": "List EC2 instances and Security Groups",
        "permission": "read",
        "module": "inventory",
        "area": "inventory",
    },
    {
        "name": "미사용 EBS Snapshot 정리",
        "name_en": "Unused EBS Snapshot Cleanup",
        "description": "고아/오래된 EBS Snapshot 삭제 (Dry-run 지원)",
        "description_en": "Delete orphaned/old EBS Snapshots (dry-run supported)",
        "permission": "delete",
        "module": "snapshot_cleanup",
        "area": "unused",
    },
    {
        "name": "미사용 AMI 정리",
        "name_en": "Unused AMI Cleanup",
        "description": "미사용 AMI 및 연관 스냅샷 삭제 (Dry-run 지원)",
        "description_en": "Delete unused AMIs and associated snapshots (dry-run supported)",
        "permission": "delete",
        "module": "ami_cleanup",
        "area": "unused",
    },
]
