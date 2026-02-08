"""
cli/i18n/messages/excel.py - Excel Export Messages

Contains translations for Excel column headers and sheet names.
These are commonly used across multiple tools.
"""

from __future__ import annotations

EXCEL_MESSAGES = {
    # =========================================================================
    # Common Sheet Names
    # =========================================================================
    "sheet_summary": {
        "ko": "분석 요약",
        "en": "Summary",
    },
    "sheet_results": {
        "ko": "결과",
        "en": "Results",
    },
    "sheet_details": {
        "ko": "상세 정보",
        "en": "Details",
    },
    # =========================================================================
    # Common Column Headers - Identity
    # =========================================================================
    "col_account_id": {
        "ko": "계정 ID",
        "en": "Account ID",
    },
    "col_account_name": {
        "ko": "계정명",
        "en": "Account Name",
    },
    "col_region": {
        "ko": "리전",
        "en": "Region",
    },
    "col_resource_id": {
        "ko": "리소스 ID",
        "en": "Resource ID",
    },
    "col_resource_name": {
        "ko": "리소스명",
        "en": "Resource Name",
    },
    "col_arn": {
        "ko": "ARN",
        "en": "ARN",
    },
    # =========================================================================
    # Common Column Headers - EC2
    # =========================================================================
    "col_instance_id": {
        "ko": "인스턴스 ID",
        "en": "Instance ID",
    },
    "col_instance_name": {
        "ko": "인스턴스명",
        "en": "Instance Name",
    },
    "col_instance_type": {
        "ko": "인스턴스 타입",
        "en": "Instance Type",
    },
    "col_instance_state": {
        "ko": "상태",
        "en": "State",
    },
    "col_private_ip": {
        "ko": "프라이빗 IP",
        "en": "Private IP",
    },
    "col_public_ip": {
        "ko": "퍼블릭 IP",
        "en": "Public IP",
    },
    "col_vpc_id": {
        "ko": "VPC ID",
        "en": "VPC ID",
    },
    "col_subnet_id": {
        "ko": "서브넷 ID",
        "en": "Subnet ID",
    },
    "col_security_groups": {
        "ko": "보안 그룹",
        "en": "Security Groups",
    },
    "col_ami_id": {
        "ko": "AMI ID",
        "en": "AMI ID",
    },
    "col_launch_time": {
        "ko": "시작 시간",
        "en": "Launch Time",
    },
    # =========================================================================
    # Common Column Headers - EBS
    # =========================================================================
    "col_volume_id": {
        "ko": "볼륨 ID",
        "en": "Volume ID",
    },
    "col_volume_name": {
        "ko": "볼륨명",
        "en": "Volume Name",
    },
    "col_volume_type": {
        "ko": "볼륨 타입",
        "en": "Volume Type",
    },
    "col_volume_size": {
        "ko": "크기(GB)",
        "en": "Size (GB)",
    },
    "col_iops": {
        "ko": "IOPS",
        "en": "IOPS",
    },
    "col_throughput": {
        "ko": "처리량",
        "en": "Throughput",
    },
    "col_attached_to": {
        "ko": "연결 대상",
        "en": "Attached To",
    },
    "col_snapshot_id": {
        "ko": "스냅샷 ID",
        "en": "Snapshot ID",
    },
    # =========================================================================
    # Common Column Headers - S3
    # =========================================================================
    "col_bucket_name": {
        "ko": "버킷명",
        "en": "Bucket Name",
    },
    "col_bucket_size": {
        "ko": "버킷 크기",
        "en": "Bucket Size",
    },
    "col_object_count": {
        "ko": "객체 수",
        "en": "Object Count",
    },
    "col_versioning": {
        "ko": "버전 관리",
        "en": "Versioning",
    },
    "col_encryption": {
        "ko": "암호화",
        "en": "Encryption",
    },
    "col_public_access": {
        "ko": "퍼블릭 액세스",
        "en": "Public Access",
    },
    # =========================================================================
    # Common Column Headers - RDS
    # =========================================================================
    "col_db_instance_id": {
        "ko": "DB 인스턴스 ID",
        "en": "DB Instance ID",
    },
    "col_db_engine": {
        "ko": "엔진",
        "en": "Engine",
    },
    "col_db_engine_version": {
        "ko": "엔진 버전",
        "en": "Engine Version",
    },
    "col_db_class": {
        "ko": "인스턴스 클래스",
        "en": "Instance Class",
    },
    "col_db_storage": {
        "ko": "스토리지(GB)",
        "en": "Storage (GB)",
    },
    "col_multi_az": {
        "ko": "Multi-AZ",
        "en": "Multi-AZ",
    },
    # =========================================================================
    # Common Column Headers - IAM
    # =========================================================================
    "col_user_name": {
        "ko": "사용자명",
        "en": "User Name",
    },
    "col_role_name": {
        "ko": "역할명",
        "en": "Role Name",
    },
    "col_policy_name": {
        "ko": "정책명",
        "en": "Policy Name",
    },
    "col_last_used": {
        "ko": "마지막 사용",
        "en": "Last Used",
    },
    "col_created_date": {
        "ko": "생성일",
        "en": "Created Date",
    },
    "col_access_key_id": {
        "ko": "액세스 키 ID",
        "en": "Access Key ID",
    },
    "col_access_key_status": {
        "ko": "키 상태",
        "en": "Key Status",
    },
    "col_mfa_enabled": {
        "ko": "MFA 활성화",
        "en": "MFA Enabled",
    },
    # =========================================================================
    # Common Column Headers - Cost
    # =========================================================================
    "col_monthly_cost": {
        "ko": "월 비용",
        "en": "Monthly Cost",
    },
    "col_estimated_savings": {
        "ko": "예상 절감액",
        "en": "Estimated Savings",
    },
    "col_cost_per_hour": {
        "ko": "시간당 비용",
        "en": "Cost/Hour",
    },
    # =========================================================================
    # Common Column Headers - Status
    # =========================================================================
    "col_status": {
        "ko": "상태",
        "en": "Status",
    },
    "col_reason": {
        "ko": "사유",
        "en": "Reason",
    },
    "col_recommendation": {
        "ko": "권장 조치",
        "en": "Recommendation",
    },
    "col_severity": {
        "ko": "심각도",
        "en": "Severity",
    },
    "col_risk_level": {
        "ko": "위험도",
        "en": "Risk Level",
    },
    # =========================================================================
    # Common Column Headers - Tags
    # =========================================================================
    "col_tags": {
        "ko": "태그",
        "en": "Tags",
    },
    "col_tag_name": {
        "ko": "Name 태그",
        "en": "Name Tag",
    },
    "col_tag_environment": {
        "ko": "환경",
        "en": "Environment",
    },
    "col_tag_owner": {
        "ko": "소유자",
        "en": "Owner",
    },
    # =========================================================================
    # Common Column Headers - Metrics
    # =========================================================================
    "col_cpu_utilization": {
        "ko": "CPU 사용률(%)",
        "en": "CPU Utilization (%)",
    },
    "col_memory_utilization": {
        "ko": "메모리 사용률(%)",
        "en": "Memory Utilization (%)",
    },
    "col_network_in": {
        "ko": "네트워크 In",
        "en": "Network In",
    },
    "col_network_out": {
        "ko": "네트워크 Out",
        "en": "Network Out",
    },
    "col_disk_read": {
        "ko": "디스크 읽기",
        "en": "Disk Read",
    },
    "col_disk_write": {
        "ko": "디스크 쓰기",
        "en": "Disk Write",
    },
    "col_connections": {
        "ko": "연결 수",
        "en": "Connections",
    },
}
