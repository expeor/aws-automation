"""
plugins/resource_explorer/common/services/devops.py - DevOps 리소스 수집

CloudFormation Stack, CodePipeline, CodeBuild Project 수집.
"""

from core.parallel import get_client

from ..types import CloudFormationStack, CodeBuildProject, CodePipeline


def collect_cloudformation_stacks(
    session, account_id: str, account_name: str, region: str
) -> list[CloudFormationStack]:
    """CloudFormation Stack 수집"""
    cfn = get_client(session, "cloudformation", region_name=region)
    stacks = []

    paginator = cfn.get_paginator("describe_stacks")
    for page in paginator.paginate():
        for stack in page.get("Stacks", []):
            # 태그
            tags = {tag["Key"]: tag["Value"] for tag in stack.get("Tags", [])}

            stacks.append(
                CloudFormationStack(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    stack_id=stack.get("StackId", ""),
                    stack_name=stack.get("StackName", ""),
                    stack_status=stack.get("StackStatus", ""),
                    description=stack.get("Description", ""),
                    creation_time=stack.get("CreationTime"),
                    last_updated_time=stack.get("LastUpdatedTime"),
                    deletion_time=stack.get("DeletionTime"),
                    parent_id=stack.get("ParentId", ""),
                    root_id=stack.get("RootId", ""),
                    drift_status=stack.get("DriftInformation", {}).get("StackDriftStatus", ""),
                    enable_termination_protection=stack.get("EnableTerminationProtection", False),
                    role_arn=stack.get("RoleARN", ""),
                    tags=tags,
                )
            )

    return stacks


def collect_codepipelines(session, account_id: str, account_name: str, region: str) -> list[CodePipeline]:
    """CodePipeline 수집"""
    codepipeline = get_client(session, "codepipeline", region_name=region)
    pipelines = []

    try:
        paginator = codepipeline.get_paginator("list_pipelines")
        for page in paginator.paginate():
            for pipeline in page.get("pipelines", []):
                pipeline_name = pipeline.get("name", "")

                try:
                    # 상세 정보 조회
                    detail = codepipeline.get_pipeline(name=pipeline_name)
                    meta = detail.get("metadata", {})
                    pipeline_def = detail.get("pipeline", {})

                    pipeline_arn = meta.get("pipelineArn", "")

                    # 태그 조회
                    tags = {}
                    try:
                        tags_resp = codepipeline.list_tags_for_resource(resourceArn=pipeline_arn)
                        tags = {tag["key"]: tag["value"] for tag in tags_resp.get("tags", [])}
                    except Exception:
                        pass

                    pipelines.append(
                        CodePipeline(
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            pipeline_name=pipeline_name,
                            pipeline_arn=pipeline_arn,
                            pipeline_version=pipeline_def.get("version", 0),
                            stage_count=len(pipeline_def.get("stages", [])),
                            role_arn=pipeline_def.get("roleArn", ""),
                            execution_mode=pipeline_def.get("executionMode", ""),
                            pipeline_type=pipeline_def.get("pipelineType", ""),
                            created=pipeline.get("created"),
                            updated=pipeline.get("updated"),
                            tags=tags,
                        )
                    )
                except Exception:
                    pass
    except Exception:
        pass

    return pipelines


def collect_codebuild_projects(session, account_id: str, account_name: str, region: str) -> list[CodeBuildProject]:
    """CodeBuild Project 수집"""
    codebuild = get_client(session, "codebuild", region_name=region)
    projects = []

    try:
        # 프로젝트 이름 목록
        project_names = []
        paginator = codebuild.get_paginator("list_projects")
        for page in paginator.paginate():
            project_names.extend(page.get("projects", []))

        if not project_names:
            return projects

        # 배치로 상세 정보 조회 (100개씩)
        batch_size = 100
        for i in range(0, len(project_names), batch_size):
            batch = project_names[i : i + batch_size]
            try:
                resp = codebuild.batch_get_projects(names=batch)
                for proj in resp.get("projects", []):
                    # 태그
                    tags = {tag["key"]: tag["value"] for tag in proj.get("tags", [])}

                    source = proj.get("source", {})
                    environment = proj.get("environment", {})

                    projects.append(
                        CodeBuildProject(
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            project_name=proj.get("name", ""),
                            project_arn=proj.get("arn", ""),
                            description=proj.get("description", ""),
                            source_type=source.get("type", ""),
                            source_location=source.get("location", ""),
                            environment_type=environment.get("type", ""),
                            compute_type=environment.get("computeType", ""),
                            environment_image=environment.get("image", ""),
                            service_role=proj.get("serviceRole", ""),
                            timeout_in_minutes=proj.get("timeoutInMinutes", 0),
                            queued_timeout_in_minutes=proj.get("queuedTimeoutInMinutes", 0),
                            encryption_key=proj.get("encryptionKey", ""),
                            badge_enabled=proj.get("badge", {}).get("badgeEnabled", False),
                            last_modified=proj.get("lastModified"),
                            created=proj.get("created"),
                            tags=tags,
                        )
                    )
            except Exception:
                pass
    except Exception:
        pass

    return projects
