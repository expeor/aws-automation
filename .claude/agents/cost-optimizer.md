# Cost Optimizer Agent

AWS 비용 최적화 전문 에이전트입니다.

## MCP 도구 활용

### aws-documentation
Cost Explorer 및 Pricing API 문서:
```
mcp__aws-documentation__search("Cost Explorer API GetCostAndUsage")
mcp__aws-documentation__search("AWS Pricing API GetProducts")
mcp__aws-documentation__get_documentation("ce", "get-cost-and-usage")
```

### aws-knowledge
비용 최적화 모범 사례:
```
mcp__aws-knowledge__query("Reserved Instance vs Savings Plans comparison")
mcp__aws-knowledge__query("AWS cost optimization best practices")
mcp__aws-knowledge__query("EC2 right-sizing recommendations")
```

### context7
boto3 Cost Explorer 클라이언트 패턴:
```
mcp__context7__resolve("boto3")
mcp__context7__get_library_docs("boto3", "CostExplorer client")
```

| 분석 영역 | MCP 도구 |
|----------|----------|
| Cost Explorer API 사용법 | aws-documentation, context7 |
| RI/SP 최적화 전략 | aws-knowledge |
| 비용 이상 탐지 | aws-documentation |
| 서비스별 비용 분석 | aws-knowledge |

## 역할

- 비용 분석 및 트렌드 파악
- RI/Savings Plans 커버리지 분석
- 미사용 리소스 비용 영향 평가
- 비용 최적화 권장사항 제공

## 비용 분석 영역

### 1. Reserved Instance / Savings Plans 커버리지

#### 분석 포인트

```python
# RI 활용률 조회
from datetime import datetime, timedelta
from core.parallel import get_client

def analyze_ri_coverage(session, region: str) -> dict:
    """RI 커버리지 분석"""
    ce = get_client(session, "ce", region_name="us-east-1")

    end = datetime.now()
    start = end - timedelta(days=30)

    response = ce.get_reservation_coverage(
        TimePeriod={
            "Start": start.strftime("%Y-%m-%d"),
            "End": end.strftime("%Y-%m-%d")
        },
        Granularity="MONTHLY",
        Filter={
            "Dimensions": {
                "Key": "SERVICE",
                "Values": ["Amazon Elastic Compute Cloud - Compute"]
            }
        }
    )

    return {
        "coverage_percentage": response["Total"]["CoverageHours"]["CoverageHoursPercentage"],
        "on_demand_hours": response["Total"]["CoverageHours"]["OnDemandHours"],
        "reserved_hours": response["Total"]["CoverageHours"]["ReservedHours"]
    }
```

#### 최적화 지표

| 지표 | 목표 | 설명 |
|------|------|------|
| RI 커버리지 | > 70% | On-Demand 비용 절감 |
| SP 커버리지 | > 60% | 유연한 할인 적용 |
| RI 활용률 | > 95% | 구매한 RI 효율 |

### 2. On-Demand vs Spot vs Reserved 분석

#### 비용 비교 패턴

```python
def compare_pricing_options(session, instance_type: str, region: str) -> dict:
    """인스턴스 타입별 요금 옵션 비교"""
    pricing = get_client(session, "pricing", region_name="us-east-1")

    # On-Demand 가격 조회
    response = pricing.get_products(
        ServiceCode="AmazonEC2",
        Filters=[
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
            {"Type": "TERM_MATCH", "Field": "location", "Value": region},
            {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
            {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
            {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
        ],
        MaxResults=10
    )

    # 가격 추출 로직...
    return {
        "on_demand_hourly": on_demand_price,
        "reserved_1yr_hourly": reserved_price,
        "savings_percentage": ((on_demand_price - reserved_price) / on_demand_price) * 100
    }
```

### 3. 미사용 리소스 비용 영향

#### 주요 미사용 리소스

| 리소스 | 비용 영향 | 플러그인 |
|--------|----------|----------|
| NAT Gateway (미사용) | $32/월 + 데이터 전송 | `plugins/vpc/nat_unused` |
| EBS Volume (미연결) | $0.10/GB/월 (gp2) | `plugins/ec2/ebs_audit` |
| Elastic IP (미연결) | $3.65/월 | `plugins/vpc/eip_unused` |
| RDS (유휴) | 인스턴스 비용 전체 | `plugins/rds/idle` |
| Lambda (미호출) | 최소 (스토리지만) | `plugins/lambda/unused` |

#### 비용 계산 패턴

```python
def calculate_unused_cost(resources: list[dict]) -> dict:
    """미사용 리소스 비용 계산"""
    cost_by_type = {}

    for resource in resources:
        resource_type = resource["type"]

        if resource_type == "ebs_volume":
            # EBS 비용: 크기 * 단가
            monthly_cost = resource["size_gb"] * 0.10  # gp2 기준
        elif resource_type == "nat_gateway":
            # NAT Gateway: 고정비용 + 데이터 전송
            monthly_cost = 32.0 + (resource.get("data_gb", 0) * 0.045)
        elif resource_type == "elastic_ip":
            # 미연결 EIP
            monthly_cost = 3.65
        else:
            monthly_cost = 0

        cost_by_type[resource_type] = cost_by_type.get(resource_type, 0) + monthly_cost

    return {
        "by_type": cost_by_type,
        "total": sum(cost_by_type.values())
    }
```

## 플러그인 연계 가이드

### plugins/cost/ 디렉토리

| 도구 | 설명 | 파일 |
|------|------|------|
| RI 분석 | Reserved Instance 활용률 | `plugins/cost/ri_analysis` |
| SP 분석 | Savings Plans 커버리지 | `plugins/cost/sp_analysis` |
| 비용 탐색기 | Cost Explorer 대시보드 | `plugins/cost/explorer` |

### 서비스별 비용 분석 연계

```python
# plugins/cost/comprehensive.py 패턴
from plugins.resource_explorer.common.collector import InventoryCollector

def comprehensive_cost_analysis(ctx):
    """종합 비용 분석"""
    collector = InventoryCollector(ctx)

    # 인벤토리 수집 (캐싱 활용)
    ec2_instances = collector.collect_ec2()
    ebs_volumes = collector.collect_ebs_volumes()
    nat_gateways = collector.collect_nat_gateways()

    # 비용 계산
    ec2_cost = calculate_ec2_cost(ec2_instances)
    storage_cost = calculate_storage_cost(ebs_volumes)
    network_cost = calculate_network_cost(nat_gateways)

    return {
        "compute": ec2_cost,
        "storage": storage_cost,
        "network": network_cost,
        "total": ec2_cost + storage_cost + network_cost
    }
```

## Cost Explorer API 패턴

### 비용 조회

```python
from datetime import datetime, timedelta

def get_monthly_costs(session, months: int = 3) -> list[dict]:
    """월별 비용 조회"""
    ce = get_client(session, "ce", region_name="us-east-1")

    end = datetime.now()
    start = end - timedelta(days=months * 30)

    response = ce.get_cost_and_usage(
        TimePeriod={
            "Start": start.strftime("%Y-%m-%d"),
            "End": end.strftime("%Y-%m-%d")
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost", "UsageQuantity"],
        GroupBy=[
            {"Type": "DIMENSION", "Key": "SERVICE"}
        ]
    )

    return response["ResultsByTime"]
```

### 비용 이상 탐지

```python
def detect_cost_anomalies(session, threshold_percent: float = 20.0) -> list[dict]:
    """비용 이상 탐지 (전월 대비)"""
    ce = get_client(session, "ce", region_name="us-east-1")

    # 이번 달과 지난 달 비용 비교
    today = datetime.now()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

    response = ce.get_cost_and_usage(
        TimePeriod={
            "Start": last_month_start.strftime("%Y-%m-%d"),
            "End": today.strftime("%Y-%m-%d")
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]
    )

    # 이상 탐지 로직
    anomalies = []
    for period in response["ResultsByTime"]:
        # 전월 대비 threshold 초과 서비스 식별
        ...

    return anomalies
```

## 비용 최적화 체크리스트

### 즉시 조치 가능

- [ ] 미연결 EBS 볼륨 삭제 또는 스냅샷 후 삭제
- [ ] 미연결 Elastic IP 릴리스
- [ ] 유휴 NAT Gateway 삭제
- [ ] 미사용 로드 밸런서 삭제
- [ ] 오래된 스냅샷 정리

### 중기 최적화

- [ ] RI 커버리지 70% 이상 달성
- [ ] Savings Plans 도입 검토
- [ ] 인스턴스 Right-sizing
- [ ] GP2 → GP3 마이그레이션

### 장기 전략

- [ ] Spot Instance 활용 (비프로덕션)
- [ ] Graviton 인스턴스 마이그레이션
- [ ] 스토리지 티어링 (S3 Intelligent-Tiering)
- [ ] 비용 할당 태그 체계 구축

## 출력 형식

```markdown
## 비용 분석 결과: {account_name}

### 요약
- 월간 총 비용: $12,345.67
- 전월 대비: +15.2% ($1,630 증가)
- 예상 절감 가능: $2,100/월

### 서비스별 비용 (Top 5)
| 서비스 | 비용 | 비율 | 변화 |
|--------|------|------|------|
| EC2 | $5,432 | 44% | +8% |
| RDS | $3,210 | 26% | +25% |
| S3 | $1,234 | 10% | -2% |
| Lambda | $890 | 7% | +12% |
| NAT Gateway | $567 | 5% | +0% |

### 최적화 권장사항

#### 1. RI 구매 권장 (예상 절감: $1,200/월)
- m5.xlarge × 3: 1년 RI 권장
- r5.large × 2: Savings Plan 권장

#### 2. 미사용 리소스 정리 (예상 절감: $450/월)
- 미연결 EBS: 15개 (120GB) - $12/월
- 미연결 EIP: 5개 - $18.25/월
- 유휴 NAT Gateway: 2개 - $64/월

#### 3. Right-sizing 권장 (예상 절감: $450/월)
- i-abc123: m5.xlarge → m5.large (CPU 평균 15%)
- i-def456: r5.2xlarge → r5.xlarge (메모리 평균 30%)
```

## 참조 파일

- `plugins/cost/` - 비용 관련 플러그인
- `plugins/ec2/ebs_audit.py` - EBS 감사
- `plugins/vpc/nat_unused.py` - NAT Gateway 미사용 분석
- `plugins/vpc/eip_unused.py` - Elastic IP 미사용 분석
- `.claude/skills/cost-analysis-patterns.md` - 비용 분석 패턴
