# AA (AWS Automation)

[![CI](https://github.com/expeor/aws-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/expeor/aws-automation/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/expeor/aws-automation/branch/master/graph/badge.svg)](https://codecov.io/gh/expeor/aws-automation)
[![Python](https://img.shields.io/badge/Python-3.10--3.14-3776AB?logo=python&logoColor=white)](https://python.org/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

AWS 콘솔을 열지 않고, 터미널 한 줄로 미사용 리소스를 찾고 보고서를 만듭니다.

> CLI tool for AWS operational automation — detect unused resources, audit security,
> and generate Excel/HTML reports across multiple accounts and regions.

```
$ aa ec2/ebs_audit -p prod -r ap-northeast-2 -r us-east-1

EBS 미사용 분석 시작...

⠙ 리소스 수집 48✓ 2✗ / 50 ████████████████████████████████ 00:12

전체 EBS: 312개 (28.5 TB)
  미사용: 67개 (4.2 TB) — 예상 절감: $420.00/월
  사용 중: 245개

완료! C:\output\prod\ec2\ebs_audit\20260208\ebs_audit.xlsx
완료! C:\output\prod\ec2\ebs_audit\20260208\ebs_audit.html
```

35개 AWS 서비스에 걸쳐 **74개 분석 도구**와 **5개 종합 리포트**를 제공합니다.

## 왜 AA인가

**Console에서 수동 확인하면** 20개 계정 × 15개 리전을 하나씩 돌아야 합니다. 한 서비스에 30분, 전체 점검에 며칠.

**AA를 쓰면** 한 명령으로 모든 계정·리전을 병렬 수집합니다. 결과는 Excel + HTML로 즉시 공유 가능.

| | Console 수동 | AA |
| --- | --- | --- |
| 20개 계정 EBS 점검 | ~3시간 | **2분** |
| 전체 미사용 리소스 리포트 | 하루+ | **5분** |
| 결과 공유 | 스크린샷 복붙 | **Excel/HTML 자동 생성** |

## 한눈에 보기

### 비용 절감

미사용 EC2, EBS, EIP, Snapshot, AMI, Lambda, ELB, RDS 등 **28개 탐지 도구**가 방치된 리소스를 찾아냅니다. Cost Dashboard 리포트는 전체 미사용 현황을 한 페이지로 요약합니다.

```bash
aa ec2/ebs_audit -p prod -r all          # 전체 리전 EBS 점검
aa report/cost_dashboard -p prod -r all   # 미사용 종합 대시보드
```

### 보안 감사

IAM 사용자/역할, Security Group, CloudTrail, KMS, Lambda 런타임 지원 중단까지. **8개 보안 도구**로 취약점을 점검합니다.

```bash
aa iam/iam_audit -p prod -r all          # IAM 보안 점검
aa vpc/sg_audit -p prod -r ap-northeast-2 # Security Group 감사
```

### 운영 효율화

`parallel_collect`가 멀티 계정 × 멀티 리전을 Map-Reduce로 병렬 실행합니다. 서비스별 Token Bucket Rate Limiting이 자동 적용되어 API 스로틀링 없이 수집합니다.

```bash
# SSO Session으로 멀티 계정 실행
aa ec2/ebs_audit -s my-sso --account 111122223333 --account 444455556666 --role ReadOnly

# 프로파일 그룹 (여러 프로필을 묶어서)
aa ec2/ebs_audit -g "전체 계정" -r all
```

### 정기 점검

일간/월간/분기/반기/연간 단위로 거버넌스 작업을 스케줄링합니다. 어떤 점검을 언제 돌려야 하는지 관리하고, 놓친 작업을 추적합니다.

```bash
aa report/scheduled -p prod -r ap-northeast-2    # 정기 작업 관리
```

### 보고서

모든 도구의 결과는 **Excel + HTML** 듀얼 포맷으로 저장됩니다. HTML 보고서는 ECharts 기반 차트를 포함합니다. 완료 시 탐색기가 자동으로 열립니다.

## Quick Start

```bash
# 설치
pip install aws-automation

# 대화형 메뉴 (처음이라면 여기서 시작)
aa

# 또는 도구 직접 실행
aa ec2/ebs_audit -p my-profile -r ap-northeast-2
```

## 설치

```bash
# PyPI
pip install aws-automation

# 소스
git clone https://github.com/expeor/aws-automation.git
cd aws-automation
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS/Linux
pip install -e .
```

업데이트: `pip install --upgrade aws-automation` 또는 `git pull && pip install -e .`

## 사용법

### 대화형 모드

`aa`를 실행하면 대화형 메뉴가 나타납니다:

```
$ aa

    /\      /\
   /  \    /  \       AWS Automation CLI  v0.4.3
  / /\ \  / /\ \     ━━━━━━━━━━━━━━━━━━━━━━━━━━
 / ____ \/ ____ \    ⚡ 79 Tools Ready
/_/    \_\/    \_\

? 메뉴를 선택하세요:
  a  전체 도구
  s  AWS 서비스별 (EC2, RDS…)
  c  AWS 분류별 (Compute…)
  t  점검 유형 (보안, 비용…)
  f  즐겨찾기
  p  프로필
  g  프로필 그룹
  q  종료
```

서비스 이름이나 키워드를 입력하면 바로 검색됩니다:

```bash
aa ec2              # EC2 도구 메뉴
aa vpc              # VPC 도구 메뉴
aa --lang en ec2    # 영문 출력
```

### Headless 모드

CI/CD 파이프라인이나 스크립트에서 대화형 프롬프트 없이 실행합니다.

```bash
# 도구 경로 확인
aa tools
aa tools -c ec2                # 카테고리 필터
aa tools --json                # JSON (스크립트 연동)

# 인증 방식별 실행
aa ec2/ebs_audit -p my-profile -r ap-northeast-2              # SSO Profile
aa ec2/ebs_audit -s my-sso --account 111122223333 --role Admin # SSO Session
aa ec2/ebs_audit -g "개발 환경" -r ap-northeast-2              # 프로파일 그룹

# 리전 옵션
aa ec2/ebs_audit -p prod -r ap-northeast-2 -r us-east-1       # 다중 리전
aa ec2/ebs_audit -p prod -r all                                # 전체 리전

# 출력 형식
aa ec2/ebs_audit -p prod -f both                   # Excel + HTML (기본)
aa ec2/ebs_audit -p prod -f json -o result.json    # JSON
aa ec2/ebs_audit -p prod -f csv -o result.csv      # CSV
aa ec2/ebs_audit -p prod -f console -q             # 콘솔만, 최소 출력
```

<details>
<summary>전체 옵션 레퍼런스</summary>

**Headless 옵션:**

| 옵션 | 설명 |
| ---- | ---- |
| `-p, --profile` | SSO Profile 또는 Access Key 프로파일 |
| `-s, --sso-session` | SSO Session 이름 (멀티 계정) |
| `--account` | 계정 ID (SSO Session용, 다중 가능) |
| `--role` | Role 이름 (SSO Session용) |
| `-g, --profile-group` | 저장된 프로파일 그룹 이름 |
| `-r, --region` | 리전 (다중 가능, `all` 또는 패턴) |
| `-f, --format` | `both` (기본 = Excel + HTML), `excel`, `html` |
| `-o, --output` | 출력 파일 경로 |
| `-q, --quiet` | 최소 출력 모드 |

**전역 옵션:**

| 옵션 | 설명 |
| ---- | ---- |
| `--help` | 도움말 |
| `--version` | 버전 |
| `--lang ko\|en` | 출력 언어 (기본: ko) |

**환경 변수:**

| 변수 | 설명 |
| ---- | ---- |
| `NO_COLOR` | 색상 출력 비활성화 |
| `AWS_DEFAULT_REGION` | 기본 리전 |
| `AWS_PROFILE` | 기본 프로필 |

**Exit Codes:** `0` 성공 · `1` 일반 오류 · `2` 인증 오류

</details>

### 프로파일 그룹

여러 프로파일을 그룹으로 묶어 한 번에 실행할 수 있습니다.

```bash
aa group create            # 그룹 생성 (인터랙티브)
aa group list              # 그룹 목록
aa group show "개발 환경"   # 그룹 상세
aa group delete "개발 환경" # 그룹 삭제
```

## 지원 서비스

35개 서비스, 74개 분석 도구:

| 서비스 | 도구 | 주요 기능 |
| ------ | ---: | --------- |
| **EC2** | 9 | 미사용 인스턴스/EBS/EIP/Snapshot/AMI, 인벤토리, 암호화 점검, 정리 |
| **ELB** | 7 | 미사용 ELB/Target Group, 보안 점검, CLB 마이그레이션, 로그 분석 |
| **Lambda** | 5 | 미사용 함수/버전, 런타임 지원 중단, Provisioned 비용, 종합 분석 |
| **Cost Explorer** | 4 | Cost Optimization Hub — 라이트사이징, 유휴, 커밋먼트 권장 |
| **VPC** | 4 | Security Group 감사/인벤토리, 미사용 네트워크, 리소스 인벤토리 |
| **Health** | 3 | Health 이벤트, 패치 현황, 서비스 장애 |
| **IAM** | 3 | IAM 보안 점검, 사용자 스냅샷, 미사용 역할 |
| **KMS** | 3 | 미사용 키, 키 사용 조회, 보안 점검 |
| **Tag Editor** | 3 | MAP 태그 현황/적용, EC2→EBS 태그 동기화 |

<details>
<summary>나머지 26개 서비스</summary>

| 서비스 | 도구 | 서비스 | 도구 |
| ------ | ---: | ------ | ---: |
| ACM | 1 | Glue | 1 |
| API Gateway | 1 | Kinesis | 1 |
| Backup | 2 | OpenSearch | 1 |
| CloudFormation | 2 | RDS | 2 |
| CloudTrail | 2 | Redshift | 1 |
| CloudWatch | 2 | Route 53 | 1 |
| CodeCommit | 2 | S3 | 1 |
| DynamoDB | 2 | SageMaker | 1 |
| ECR | 1 | Secrets Manager | 1 |
| EFS | 1 | SNS | 1 |
| ElastiCache | 1 | SQS | 1 |
| EventBridge | 1 | SSO (Identity Center) | 1 |
| FSx | 1 | Transfer Family | 1 |

</details>

## 종합 리포트

분석 도구 외에 계정 전체를 조망하는 5개 리포트:

| 리포트 | 설명 |
| ------ | ---- |
| **Cost Dashboard** | EBS, EIP, ELB, NAT Gateway 등 10개+ 리소스의 미사용 현황을 한 페이지로. 계정별 절감 추정치 포함 |
| **Resource Inventory** | EC2, VPC, ELB 등 주요 리소스를 계정·리전별로 종합 조회 |
| **IP Search** | Public/Private IP 검색. AWS·GCP·Azure·Oracle Cloud IP 대역 자동 매칭 |
| **Log Analyzer** | ALB/NLB 액세스 로그 분석. DuckDB 기반 대용량 처리, GeoIP 국가 매핑, TPS/SLA/보안 이벤트 |
| **Scheduled Operations** | 일간/월간/분기/반기/연간 정기 거버넌스 작업 관리 |

```bash
aa report/cost_dashboard -p prod -r all
aa report/inventory -p prod -r ap-northeast-2
aa ip 10.0.1.50
```

## AA의 한계

- **실시간 모니터링** — AA는 주기적 점검 도구이며, CloudWatch/Datadog 같은 상시 모니터링을 대체하지 않습니다
- **단일 리소스 디버깅** — 특정 리소스 하나를 상세 조사할 때는 AWS Console이나 CLI가 더 적합합니다

<details>
<summary>아키텍처 (기여자용)</summary>

```
aws-automation/
├── core/                  # CLI 인프라
│   ├── auth/              #   인증 (SSO Session, SSO Profile, Static)
│   ├── parallel/          #   병렬 실행, Rate Limiting, Quotas
│   ├── tools/             #   도구 관리, 캐시, 히스토리
│   ├── region/            #   리전 데이터, 가용성, 필터링
│   ├── cli/               #   Click CLI, 대화형 메뉴, i18n
│   └── shared/            #   공유 유틸리티
│       ├── aws/           #     메트릭, 요금, 인벤토리, IP 대역
│       └── io/            #     Excel, HTML, CSV 출력
├── functions/             # 기능 모듈
│   ├── analyzers/         #   35개 서비스, 74개 분석 도구
│   └── reports/           #   5개 종합 리포트
└── tests/                 # pytest 테스트
```

**실행 흐름:**

```
CLI 입력 → 인증 → parallel_collect (계정 × 리전)
  → Rate Limiting (Token Bucket, 서비스별 자동 적용)
    → _collect_and_analyze 콜백 (재시도 포함)
      → Excel + HTML 보고서 생성
```

자세한 내용은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요.

</details>

## 요구 사항

- Python 3.10 ~ 3.14
- AWS CLI 프로필 설정 (`~/.aws/config`)

## 외부 데이터 출처

**IP 검색:** [AWS](https://ip-ranges.amazonaws.com/ip-ranges.json) · [GCP](https://www.gstatic.com/ipranges/cloud.json) · [Azure](https://www.microsoft.com/en-us/download/details.aspx?id=56519) · [Oracle](https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json)

**ALB 로그 분석:** [IPdeny Country Blocks](https://www.ipdeny.com/ipblocks/) · [AbuseIPDB Blocklist](https://github.com/borestad/blocklist-abuseipdb)

## Contributing

기여를 환영합니다! [CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요.

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 라이선스

MIT License - [LICENSE](LICENSE)
