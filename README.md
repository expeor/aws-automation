# AA (AWS Automation)

[![PyPI](https://img.shields.io/pypi/v/aws-automation?color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/aws-automation/)
[![CI](https://github.com/expeor/aws-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/expeor/aws-automation/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10--3.13-3776AB?logo=python&logoColor=white)](https://python.org/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

AWS 운영 자동화를 위한 CLI 도구입니다.

미사용 리소스 탐지, 보안 점검, IAM 감사, 로그 분석 등 40개 이상의 AWS 운영 도구를 제공합니다. 멀티 계정·멀티 리전을 지원하며, 결과는 Excel로 저장됩니다.

## 주요 기능

- **멀티 계정 & 리전**: 여러 AWS 계정과 리전을 동시에 분석
- **다중 인증 지원**: SSO Session, SSO Profile, Access Key 자동 감지
- **Excel 보고서**: 분석 결과를 Excel 파일로 자동 저장
- **키워드 검색**: 대화형 메뉴에서 도구를 빠르게 검색
- **플러그인 구조**: 새로운 도구를 쉽게 추가 가능

## 설치

### PyPI (권장)

```bash
pip install aws-automation
```

### 소스에서 설치

```bash
git clone https://github.com/expeor/aws-automation.git
cd aws-automation
pip install -e .
```

## 사용법

```bash
aa                # 대화형 메인 메뉴
aa ec2            # EC2 도구 바로 실행
aa vpc            # VPC 도구 바로 실행
```

### 메인 메뉴

| 키  | 설명                     |
| --- | ------------------------ |
| `a` | 전체 도구                |
| `s` | AWS 서비스별 (EC2, RDS…) |
| `c` | AWS 분류별 (Compute…)    |
| `t` | 점검 유형 (보안, 비용…)  |
| `f` | 즐겨찾기                 |
| `p` | 프로필                   |
| `g` | 프로필 그룹              |
| `q` | 종료                     |

### 검색

```bash
> rds              # 서비스명
> 미사용           # 한글 키워드 (비용)
> 보안             # 한글 키워드 (보안)
> snapshot         # 영문 키워드
```

## CLI 명령어

### 기본 사용법

```bash
aa                  # 대화형 메뉴
aa ec2              # EC2 도구 실행
aa --help           # 도움말
aa --version        # 버전 표시
```

### Headless 모드

대화형 프롬프트 없이 도구를 실행합니다. SSO Profile 또는 Access Key 프로파일을 지원합니다.

```bash
# 도구 경로 확인
aa list-tools

# 기본 실행
aa run ec2/ebs_audit -p my-profile -r ap-northeast-2

# 다중 리전
aa run ec2/ebs_audit -p my-profile -r ap-northeast-2 -r us-east-1

# 전체 리전
aa run ec2/ebs_audit -p my-profile -r all

# 프로파일 그룹으로 실행
aa run ec2/ebs_audit -g "개발 환경" -r ap-northeast-2

# JSON 출력
aa run ec2/ebs_audit -p my-profile -f json -o result.json
```

**옵션:**

| 옵션                  | 설명                                 |
| --------------------- | ------------------------------------ |
| `-p, --profile`       | SSO Profile 또는 Access Key 프로파일 |
| `-g, --profile-group` | 저장된 프로파일 그룹 이름            |
| `-r, --region`        | 리전 (다중 가능, `all` 또는 패턴)    |
| `-f, --format`        | 출력 형식 (`console`, `json`, `csv`) |
| `-o, --output`        | 출력 파일 경로                       |
| `-q, --quiet`         | 최소 출력 모드                       |

### 도구 목록 조회

```bash
aa list-tools              # 전체 도구 목록
aa list-tools -c ec2       # EC2 카테고리만
aa list-tools --json       # JSON 출력
```

### IP 검색

VPC 내 IP 주소를 빠르게 검색합니다.

```bash
aa ip                      # 대화형 모드
aa ip 10.0.1.50            # 단일 IP 검색
aa ip 10.0.0.0/8           # CIDR 범위 검색
aa ip 10.0.1.50 -d         # 상세 모드 (API 조회)
aa ip vpc-0a6d4f22 -c      # VPC 검색 + CSV 저장
```

### 프로파일 그룹 관리

여러 프로파일을 그룹으로 묶어 한 번에 실행할 수 있습니다.

```bash
aa group list              # 그룹 목록
aa group show "개발 환경"   # 그룹 상세
aa group create            # 그룹 생성 (인터랙티브)
aa group delete "개발 환경" # 그룹 삭제
```

## 지원 서비스

| 서비스          | 주요 도구                             |
| --------------- | ------------------------------------- |
| EC2             | EBS/EIP/Snapshot/AMI 미사용 분석      |
| VPC             | 보안 그룹 감사, NAT Gateway, IP 검색  |
| Lambda          | 미사용/버전/Provisioned 분석          |
| S3              | 빈 버킷 탐지                          |
| IAM             | 사용자/역할 감사, 정책 분석           |
| RDS             | 스냅샷 감사                           |
| ELB             | ALB/NLB 감사, 로그 분석, 마이그레이션 |
| DynamoDB        | 용량 모드 분석, 미사용 테이블 탐지    |
| CloudWatch      | 로그 그룹 감사, 알람 분석             |
| CloudTrail      | Trail 감사                            |
| CloudFormation  | 리소스 검색                           |
| Route53         | 빈 호스팅 영역 탐지                   |
| ECR             | 미사용 저장소 탐지                    |
| KMS             | 키 사용 감사                          |
| Secrets Manager | 미사용 시크릿 탐지                    |
| SSO             | SSO 구성 감사                         |
| ACM             | 미사용/만료 임박 인증서 탐지          |
| EFS             | 미사용 파일시스템 탐지                |
| SNS/SQS         | 미사용 토픽/큐 탐지                   |
| ElastiCache     | 미사용 클러스터 탐지                  |
| API Gateway     | 미사용 API 탐지                       |
| EventBridge     | 미사용 규칙 탐지                      |
| CodeCommit      | 미사용 리포지토리 탐지                |
| Health          | AWS Health 이벤트 분석                |
| Cost            | Cost Optimization Hub, 통합 분석      |
| Tag Editor      | MAP 2.0 태그 감사/적용                |

## 요구 사항

- Python 3.10 ~ 3.13
- AWS CLI 프로필 설정 (`~/.aws/config`)

## 업데이트

```bash
# PyPI 설치 시
pip install --upgrade aws-automation

# 소스 설치 시
git pull && pip install -e .
```

## 외부 데이터 출처

이 도구는 다음 외부 데이터를 사용합니다:

**IP 검색:**

- [AWS IP Ranges](https://ip-ranges.amazonaws.com/ip-ranges.json)
- [GCP IP Ranges](https://www.gstatic.com/ipranges/cloud.json)
- [Azure ServiceTags](https://www.microsoft.com/en-us/download/details.aspx?id=56519)
- [Oracle Cloud IP Ranges](https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json)

**ALB 로그 분석:**

- [IPdeny Country IP Blocks](https://www.ipdeny.com/ipblocks/)
- [AbuseIPDB Blocklist](https://github.com/borestad/blocklist-abuseipdb)

## 라이선스

MIT License - [LICENSE](LICENSE)
