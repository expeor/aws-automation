"""
plugins/resource_explorer/common/services/iam.py - IAM/Security 리소스 수집

IAM Role, IAM User, IAM Policy, ACM Certificate, WAF WebACL 수집.
"""

from core.parallel import get_client

from ..types import ACMCertificate, IAMPolicy, IAMRole, IAMUser, WAFWebACL


def collect_iam_roles(session, account_id: str, account_name: str, region: str) -> list[IAMRole]:
    """IAM Role 수집 (글로벌 - us-east-1에서만)"""
    if region != "us-east-1":
        return []

    iam = get_client(session, "iam", region_name=region)
    roles = []

    paginator = iam.get_paginator("list_roles")
    for page in paginator.paginate():
        for role in page.get("Roles", []):
            role_name = role.get("RoleName", "")

            # Last Used 정보
            last_used_date = None
            last_used_region = ""
            try:
                detail = iam.get_role(RoleName=role_name)
                last_used = detail.get("Role", {}).get("RoleLastUsed", {})
                last_used_date = last_used.get("LastUsedDate")
                last_used_region = last_used.get("Region", "")
            except Exception:
                pass

            # 연결된 정책 수
            attached_count = 0
            inline_count = 0
            try:
                attached_resp = iam.list_attached_role_policies(RoleName=role_name)
                attached_count = len(attached_resp.get("AttachedPolicies", []))
                inline_resp = iam.list_role_policies(RoleName=role_name)
                inline_count = len(inline_resp.get("PolicyNames", []))
            except Exception:
                pass

            # 태그
            tags = {}
            try:
                tags_resp = iam.list_role_tags(RoleName=role_name)
                tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("Tags", [])}
            except Exception:
                pass

            roles.append(
                IAMRole(
                    account_id=account_id,
                    account_name=account_name,
                    region="global",
                    role_id=role.get("RoleId", ""),
                    role_name=role_name,
                    role_arn=role.get("Arn", ""),
                    path=role.get("Path", "/"),
                    description=role.get("Description", ""),
                    max_session_duration=role.get("MaxSessionDuration", 3600),
                    create_date=role.get("CreateDate"),
                    last_used_date=last_used_date,
                    last_used_region=last_used_region,
                    attached_policies_count=attached_count,
                    inline_policies_count=inline_count,
                    tags=tags,
                )
            )

    return roles


def collect_iam_users(session, account_id: str, account_name: str, region: str) -> list[IAMUser]:
    """IAM User 수집 (글로벌 - us-east-1에서만)"""
    if region != "us-east-1":
        return []

    iam = get_client(session, "iam", region_name=region)
    users = []

    paginator = iam.get_paginator("list_users")
    for page in paginator.paginate():
        for user in page.get("Users", []):
            user_name = user.get("UserName", "")

            # Access Key 정보
            has_access_keys = False
            access_key_count = 0
            try:
                keys_resp = iam.list_access_keys(UserName=user_name)
                access_key_count = len(keys_resp.get("AccessKeyMetadata", []))
                has_access_keys = access_key_count > 0
            except Exception:
                pass

            # MFA 정보
            mfa_enabled = False
            try:
                mfa_resp = iam.list_mfa_devices(UserName=user_name)
                mfa_enabled = len(mfa_resp.get("MFADevices", [])) > 0
            except Exception:
                pass

            # Login Profile (Console Access)
            has_console_access = False
            try:
                iam.get_login_profile(UserName=user_name)
                has_console_access = True
            except Exception:
                pass

            # 그룹 목록
            groups = []
            try:
                groups_resp = iam.list_groups_for_user(UserName=user_name)
                groups = [g.get("GroupName", "") for g in groups_resp.get("Groups", [])]
            except Exception:
                pass

            # 정책 수
            attached_count = 0
            inline_count = 0
            try:
                attached_resp = iam.list_attached_user_policies(UserName=user_name)
                attached_count = len(attached_resp.get("AttachedPolicies", []))
                inline_resp = iam.list_user_policies(UserName=user_name)
                inline_count = len(inline_resp.get("PolicyNames", []))
            except Exception:
                pass

            # 태그
            tags = {}
            try:
                tags_resp = iam.list_user_tags(UserName=user_name)
                tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("Tags", [])}
            except Exception:
                pass

            users.append(
                IAMUser(
                    account_id=account_id,
                    account_name=account_name,
                    region="global",
                    user_id=user.get("UserId", ""),
                    user_name=user_name,
                    user_arn=user.get("Arn", ""),
                    path=user.get("Path", "/"),
                    create_date=user.get("CreateDate"),
                    password_last_used=user.get("PasswordLastUsed"),
                    has_console_access=has_console_access,
                    has_access_keys=has_access_keys,
                    access_key_count=access_key_count,
                    mfa_enabled=mfa_enabled,
                    attached_policies_count=attached_count,
                    inline_policies_count=inline_count,
                    groups=groups,
                    tags=tags,
                )
            )

    return users


def collect_iam_policies(session, account_id: str, account_name: str, region: str) -> list[IAMPolicy]:
    """IAM Policy (Customer Managed) 수집 (글로벌 - us-east-1에서만)"""
    if region != "us-east-1":
        return []

    iam = get_client(session, "iam", region_name=region)
    policies = []

    paginator = iam.get_paginator("list_policies")
    for page in paginator.paginate(Scope="Local"):  # Customer Managed만
        for policy in page.get("Policies", []):
            policy_arn = policy.get("Arn", "")

            # 태그
            tags = {}
            try:
                tags_resp = iam.list_policy_tags(PolicyArn=policy_arn)
                tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("Tags", [])}
            except Exception:
                pass

            policies.append(
                IAMPolicy(
                    account_id=account_id,
                    account_name=account_name,
                    region="global",
                    policy_id=policy.get("PolicyId", ""),
                    policy_name=policy.get("PolicyName", ""),
                    policy_arn=policy_arn,
                    path=policy.get("Path", "/"),
                    description=policy.get("Description", ""),
                    is_attachable=policy.get("IsAttachable", True),
                    attachment_count=policy.get("AttachmentCount", 0),
                    permissions_boundary_usage_count=policy.get("PermissionsBoundaryUsageCount", 0),
                    default_version_id=policy.get("DefaultVersionId", ""),
                    create_date=policy.get("CreateDate"),
                    update_date=policy.get("UpdateDate"),
                    tags=tags,
                )
            )

    return policies


def collect_acm_certificates(session, account_id: str, account_name: str, region: str) -> list[ACMCertificate]:
    """ACM Certificate 수집"""
    acm = get_client(session, "acm", region_name=region)
    certificates = []

    try:
        paginator = acm.get_paginator("list_certificates")
        for page in paginator.paginate():
            for cert in page.get("CertificateSummaryList", []):
                cert_arn = cert.get("CertificateArn", "")

                try:
                    # 상세 정보 조회
                    detail = acm.describe_certificate(CertificateArn=cert_arn)
                    cert_detail = detail.get("Certificate", {})

                    # 태그
                    tags = {}
                    try:
                        tags_resp = acm.list_tags_for_certificate(CertificateArn=cert_arn)
                        tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("Tags", [])}
                    except Exception:
                        pass

                    certificates.append(
                        ACMCertificate(
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            certificate_arn=cert_arn,
                            domain_name=cert_detail.get("DomainName", ""),
                            status=cert_detail.get("Status", ""),
                            certificate_type=cert_detail.get("Type", ""),
                            key_algorithm=cert_detail.get("KeyAlgorithm", ""),
                            issuer=cert_detail.get("Issuer", ""),
                            subject_alternative_names=cert_detail.get("SubjectAlternativeNames", []),
                            in_use_by=cert_detail.get("InUseBy", []),
                            not_before=cert_detail.get("NotBefore"),
                            not_after=cert_detail.get("NotAfter"),
                            created_at=cert_detail.get("CreatedAt"),
                            renewal_eligibility=cert_detail.get("RenewalEligibility", ""),
                            tags=tags,
                        )
                    )
                except Exception:
                    pass
    except Exception:
        pass

    return certificates


def collect_waf_web_acls(session, account_id: str, account_name: str, region: str) -> list[WAFWebACL]:
    """WAF WebACL 수집"""
    wafv2 = get_client(session, "wafv2", region_name=region)
    web_acls = []

    # Regional WebACLs
    try:
        resp = wafv2.list_web_acls(Scope="REGIONAL")
        for acl in resp.get("WebACLs", []):
            acl_arn = acl.get("ARN", "")
            acl_id = acl.get("Id", "")
            acl_name = acl.get("Name", "")

            try:
                # 상세 정보
                detail = wafv2.get_web_acl(Name=acl_name, Scope="REGIONAL", Id=acl_id)
                web_acl = detail.get("WebACL", {})

                # 태그
                tags = {}
                try:
                    tags_resp = wafv2.list_tags_for_resource(ResourceARN=acl_arn)
                    tag_info = tags_resp.get("TagInfoForResource", {})
                    tags = {tag["Key"]: tag["Value"] for tag in tag_info.get("TagList", [])}
                except Exception:
                    pass

                default_action = web_acl.get("DefaultAction", {})
                action_type = "Allow" if "Allow" in default_action else "Block"

                web_acls.append(
                    WAFWebACL(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        web_acl_id=acl_id,
                        web_acl_arn=acl_arn,
                        name=acl_name,
                        scope="REGIONAL",
                        description=web_acl.get("Description", ""),
                        capacity=web_acl.get("Capacity", 0),
                        rule_count=len(web_acl.get("Rules", [])),
                        default_action=action_type,
                        visibility_config_metric_name=web_acl.get("VisibilityConfig", {}).get("MetricName", ""),
                        managed_by_firewall_manager=web_acl.get("ManagedByFirewallManager", False),
                        tags=tags,
                    )
                )
            except Exception:
                pass
    except Exception:
        pass

    # CloudFront WebACLs (us-east-1에서만)
    if region == "us-east-1":
        try:
            resp = wafv2.list_web_acls(Scope="CLOUDFRONT")
            for acl in resp.get("WebACLs", []):
                acl_arn = acl.get("ARN", "")
                acl_id = acl.get("Id", "")
                acl_name = acl.get("Name", "")

                try:
                    detail = wafv2.get_web_acl(Name=acl_name, Scope="CLOUDFRONT", Id=acl_id)
                    web_acl = detail.get("WebACL", {})

                    tags = {}
                    try:
                        tags_resp = wafv2.list_tags_for_resource(ResourceARN=acl_arn)
                        tag_info = tags_resp.get("TagInfoForResource", {})
                        tags = {tag["Key"]: tag["Value"] for tag in tag_info.get("TagList", [])}
                    except Exception:
                        pass

                    default_action = web_acl.get("DefaultAction", {})
                    action_type = "Allow" if "Allow" in default_action else "Block"

                    web_acls.append(
                        WAFWebACL(
                            account_id=account_id,
                            account_name=account_name,
                            region="global",
                            web_acl_id=acl_id,
                            web_acl_arn=acl_arn,
                            name=acl_name,
                            scope="CLOUDFRONT",
                            description=web_acl.get("Description", ""),
                            capacity=web_acl.get("Capacity", 0),
                            rule_count=len(web_acl.get("Rules", [])),
                            default_action=action_type,
                            visibility_config_metric_name=web_acl.get("VisibilityConfig", {}).get("MetricName", ""),
                            managed_by_firewall_manager=web_acl.get("ManagedByFirewallManager", False),
                            tags=tags,
                        )
                    )
                except Exception:
                    pass
        except Exception:
            pass

    return web_acls
