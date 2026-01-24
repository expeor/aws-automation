"""
plugins/vpc/ip_search/parser.py - ENI Description Parser

Single source of truth for ENI description -> resource mapping.
Consolidates parsing logic from private.py and detail.py.
"""

import re
from dataclasses import dataclass, field
from re import Pattern
from typing import Any


@dataclass
class ParsedResource:
    """Parsed resource information from ENI description"""

    resource_type: str  # "EC2", "Lambda", "ELB", "RDS", "EFS", etc.
    resource_id: str  # instance-id, function-name, fs-id, etc.
    resource_name: str  # Display name for the resource
    additional_info: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Return formatted display string"""
        if self.resource_id:
            return f"{self.resource_type}: {self.resource_id}"
        return self.resource_type


# =============================================================================
# Parser Patterns
# =============================================================================

# Compiled regex patterns for performance
_EFS_FS_ID_PATTERN: Pattern[str] = re.compile(r"fs-[a-zA-Z0-9]+")
_LAMBDA_FUNCTION_PATTERN: Pattern[str] = re.compile(r"AWS Lambda VPC ENI-(.+)")
_NAT_GATEWAY_PATTERN: Pattern[str] = re.compile(r"nat-[a-zA-Z0-9]+")
_TGW_ATTACHMENT_PATTERN: Pattern[str] = re.compile(r"tgw-attach-[a-zA-Z0-9]+")
_RDS_ID_PATTERNS: list[Pattern[str]] = [
    re.compile(r"RDSNetworkInterface[:\s-]+([a-zA-Z0-9_-]+)", re.IGNORECASE),
    re.compile(r"([a-zA-Z0-9_-]+)\..*\.rds\.amazonaws\.com", re.IGNORECASE),
]


# =============================================================================
# Main Parser Function
# =============================================================================


def parse_eni_description(
    description: str,
    interface_type: str = "",
    attachment: dict[str, Any] | None = None,
) -> ParsedResource | None:
    """
    Parse ENI description to identify the attached resource.

    This is the single source of truth for ENI description parsing.
    Consolidates logic from private.py and detail.py.

    Args:
        description: ENI Description field
        interface_type: ENI InterfaceType field
        attachment: ENI Attachment dict (contains InstanceId, etc.)

    Returns:
        ParsedResource with identified resource info, or None if unidentified
    """
    attachment = attachment or {}

    # Check EC2 attachment first (via attachment, not description)
    instance_id = attachment.get("InstanceId")
    if instance_id:
        return ParsedResource(
            resource_type="EC2",
            resource_id=instance_id,
            resource_name=instance_id,
        )

    if not description:
        return None

    # EFS Mount Target
    if "EFS" in description or "mount target" in description.lower():
        fs_match = _EFS_FS_ID_PATTERN.search(description)
        if fs_match:
            fs_id = fs_match.group(0)
            return ParsedResource(
                resource_type="EFS",
                resource_id=fs_id,
                resource_name=fs_id,
            )
        return ParsedResource(
            resource_type="EFS",
            resource_id="",
            resource_name="EFS Mount Target",
        )

    # Lambda
    if "AWS Lambda VPC ENI" in description:
        func_match = _LAMBDA_FUNCTION_PATTERN.search(description)
        if func_match:
            func_name = func_match.group(1).strip()
            return ParsedResource(
                resource_type="Lambda",
                resource_id=func_name,
                resource_name=func_name,
            )
        return ParsedResource(
            resource_type="Lambda",
            resource_id="",
            resource_name="Lambda Function",
        )

    # ELB (ALB, NLB, CLB)
    if "ELB" in description:
        if "app/" in description:
            # Application Load Balancer
            alb_name = description.split("app/")[1].split("/")[0]
            return ParsedResource(
                resource_type="ALB",
                resource_id=alb_name,
                resource_name=alb_name,
                additional_info={"lb_type": "application"},
            )
        elif "net/" in description:
            # Network Load Balancer
            nlb_name = description.split("net/")[1].split("/")[0]
            return ParsedResource(
                resource_type="NLB",
                resource_id=nlb_name,
                resource_name=nlb_name,
                additional_info={"lb_type": "network"},
            )
        else:
            # Classic Load Balancer
            clb_name = description.replace("ELB ", "").strip()
            return ParsedResource(
                resource_type="CLB",
                resource_id=clb_name,
                resource_name=clb_name,
                additional_info={"lb_type": "classic"},
            )

    # RDS
    if "RDSNetworkInterface" in description:
        for pattern in _RDS_ID_PATTERNS:
            match = pattern.search(description)
            if match:
                db_id = match.group(1)
                # Filter out generic words
                if db_id.lower() not in ["network", "interface", "eni"]:
                    return ParsedResource(
                        resource_type="RDS",
                        resource_id=db_id,
                        resource_name=db_id,
                    )
        return ParsedResource(
            resource_type="RDS",
            resource_id="",
            resource_name="RDS Instance",
        )

    # VPC Endpoint
    if "VPC Endpoint" in description:
        return ParsedResource(
            resource_type="VPC Endpoint",
            resource_id="",
            resource_name="VPC Endpoint",
        )

    # FSx
    if "FSx" in description or "fsx" in description.lower():
        fs_match = _EFS_FS_ID_PATTERN.search(description)  # Same pattern as EFS
        if fs_match:
            fs_id = fs_match.group(0)
            return ParsedResource(
                resource_type="FSx",
                resource_id=fs_id,
                resource_name=fs_id,
            )
        return ParsedResource(
            resource_type="FSx",
            resource_id="",
            resource_name="FSx File System",
        )

    # NAT Gateway
    if "NAT Gateway" in description or interface_type == "nat_gateway":
        nat_match = _NAT_GATEWAY_PATTERN.search(description)
        if nat_match:
            nat_id = nat_match.group(0)
            return ParsedResource(
                resource_type="NAT Gateway",
                resource_id=nat_id,
                resource_name=nat_id,
            )
        return ParsedResource(
            resource_type="NAT Gateway",
            resource_id="",
            resource_name="NAT Gateway",
        )

    # ECS Task
    if "ecs" in interface_type.lower() or "ecs" in description.lower():
        return ParsedResource(
            resource_type="ECS",
            resource_id="",
            resource_name="ECS Task",
        )

    # ElastiCache
    if "ElastiCache" in description:
        return ParsedResource(
            resource_type="ElastiCache",
            resource_id="",
            resource_name="ElastiCache Cluster",
        )

    # OpenSearch / Elasticsearch
    if "OpenSearch" in description or "Elasticsearch" in description:
        return ParsedResource(
            resource_type="OpenSearch",
            resource_id="",
            resource_name="OpenSearch Domain",
        )

    # Transit Gateway
    if "Transit Gateway" in description:
        tgw_match = _TGW_ATTACHMENT_PATTERN.search(description)
        if tgw_match:
            att_id = tgw_match.group(0)
            return ParsedResource(
                resource_type="Transit Gateway",
                resource_id=att_id,
                resource_name=att_id,
            )
        return ParsedResource(
            resource_type="Transit Gateway",
            resource_id="",
            resource_name="Transit Gateway",
        )

    # API Gateway
    if "API Gateway" in description:
        return ParsedResource(
            resource_type="API Gateway",
            resource_id="",
            resource_name="API Gateway",
        )

    # Route 53 Resolver
    if "Route 53 Resolver" in description.lower():
        return ParsedResource(
            resource_type="Route53 Resolver",
            resource_id="",
            resource_name="Route53 Resolver",
        )

    # EKS Fargate
    if "fargate" in description.lower():
        return ParsedResource(
            resource_type="EKS Fargate",
            resource_id="",
            resource_name="EKS Fargate Pod",
        )

    return None


def parse_eni_to_display_string(
    eni: dict[str, Any],
    include_type: bool = True,
) -> str:
    """
    Parse ENI to a display string for quick resource identification.

    This is a convenience wrapper around parse_eni_description that
    returns a formatted string instead of a ParsedResource object.

    Args:
        eni: Full ENI data dict from AWS API
        include_type: Include resource type prefix (default: True)

    Returns:
        Formatted display string like "EC2: i-abc123" or ""
    """
    parsed = parse_eni_description(
        description=eni.get("Description", ""),
        interface_type=eni.get("InterfaceType", ""),
        attachment=eni.get("Attachment"),
    )

    if not parsed:
        return ""

    if include_type:
        return str(parsed)
    return parsed.resource_id or parsed.resource_name
