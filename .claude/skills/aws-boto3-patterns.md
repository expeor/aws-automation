# AWS boto3 패턴

이 프로젝트의 boto3 사용 패턴입니다.

## Paginator 사용

대량 리소스 조회 시 필수:

```python
def list_all_instances(client) -> list:
    """모든 EC2 인스턴스 조회"""
    instances = []
    paginator = client.get_paginator('describe_instances')

    for page in paginator.paginate():
        for reservation in page['Reservations']:
            instances.extend(reservation['Instances'])

    return instances
```

## 세션 관리

ExecutionContext 사용 권장:

```python
class ToolRunner(BaseToolRunner):
    def _run_tool(self):
        for region, session in self.iterate_regions():
            client = session.client('ec2')
            # ...
```

멀티 계정:

```python
def _run_tool(self):
    for account_id, region, session in self.iterate_accounts_and_regions():
        client = session.client('ec2')
        # account_id가 None이면 단일 계정 모드
```

## 에러 핸들링

```python
from botocore.exceptions import ClientError, BotoCoreError

try:
    response = client.describe_instances()
except ClientError as e:
    error_code = e.response['Error']['Code']

    if error_code == 'AccessDenied':
        console.print(f"[yellow]권한 부족: {region}[/yellow]")
        return []
    elif error_code == 'InvalidParameterValue':
        console.print(f"[red]잘못된 파라미터[/red]")
        raise
    else:
        raise
except BotoCoreError as e:
    console.print(f"[red]AWS 연결 오류: {e}[/red]")
    raise
```

## 병렬 리전 처리

core/parallel 모듈 사용:

```python
from core.parallel import run_parallel

def _analyze_all_regions(self):
    results = run_parallel(
        items=self.regions,
        func=self._analyze_region,
        desc="리전 분석 중",
        max_workers=10,
    )
    return [r for r in results if r is not None]

def _analyze_region(self, region: str) -> dict | None:
    session = self.get_session(region)
    client = session.client('ec2')
    # ...
```

## Waiter 사용

상태 대기:

```python
waiter = client.get_waiter('instance_running')
waiter.wait(
    InstanceIds=['i-1234567890abcdef0'],
    WaiterConfig={'Delay': 5, 'MaxAttempts': 20}
)
```

## 태그 필터링

```python
response = client.describe_instances(
    Filters=[
        {'Name': 'tag:Environment', 'Values': ['production']},
        {'Name': 'instance-state-name', 'Values': ['running']},
    ]
)
```

## 리전 목록 조회

```python
def get_enabled_regions(session) -> list[str]:
    """활성화된 리전 목록 조회"""
    ec2 = session.client('ec2', region_name='us-east-1')
    response = ec2.describe_regions(
        Filters=[{'Name': 'opt-in-status', 'Values': ['opt-in-not-required', 'opted-in']}]
    )
    return [r['RegionName'] for r in response['Regions']]
```

## 자격 증명 Best Practices

- 하드코딩 금지
- 환경 변수 또는 AWS 프로필 사용
- IAM Role 사용 권장 (EC2, Lambda)
- 세션 토큰 만료 처리

```python
# SSO 세션 갱신 필요 시
if self.ctx and self.ctx.provider:
    try:
        session = self.ctx.provider.get_session(region=region)
    except TokenExpiredError:
        console.print("[yellow]SSO 토큰 만료. 재인증 필요.[/yellow]")
        raise
```
