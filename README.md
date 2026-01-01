# AA (AWS Automation)

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/expeor/aws-automation)

AWS 운영 자동화 CLI 도구

ALB 로그 분석, 미사용 리소스 탐지, 보안 점검, IAM 감사 등 목적별 분석 도구를 하나로 통합한 운영 도구입니다.
AWS 멀티 계정 환경에 최적화되어 있으며, SSO Session, SSO Profile, Access Key 등 다양한 인증 방식을 지원합니다.
여러 계정에 분산된 스크립트를 하나로 통합하고, 단일 명령으로 멀티 계정·멀티 리전을 동시에 분석할 수 있도록 설계했습니다.
대화형 메뉴에서 키워드 검색으로 필요한 도구를 빠르게 찾고, 결과는 Excel 보고서로 저장됩니다.

## Install

```bash
git clone https://github.com/expeor/aws-automation.git
cd aws-automation
pip install -e .
```

설치 후 `aa` 명령어 사용 가능

---

## 특징

- 대화형 프롬프트로 바로 실행
- 손쉬운 도구 추가 (플러그인 아키텍처)
- 다중 인증 지원 - `~/.aws/config`, `~/.aws/credentials`의 SSO, Access Key 프로필 자동 감지
- 멀티 계정 & 리전 동시 실행
- Excel 보고서 생성
- 한국어 UI

## 요구 사항

- **Python 3.10+** ([AWS Lambda 런타임 지원 기준](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html))
- **AWS 프로필 설정** - [AWS CLI 설정 가이드](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) 참조
- **OS**: Windows 10+, macOS 12+, Linux

## 실행

```bash
aa              # 대화형 메인 메뉴
aa rds          # RDS 도구 목록
aa ec2          # EC2 도구 목록
aa vpc          # VPC 도구 목록
```

### 메인 메뉴

```text
즐겨찾기
  1. EBS 미사용 볼륨 ec2
  2. IAM 사용자 감사 iam
  3. S3 빈 버킷 탐지 s3

명령어
  a 전체 도구    b 카테고리    f 즐겨찾기
  p 프로필       h 도움말      q 종료

검색: 키워드 또는 /cost /security /ops /inv
```

| 키 | 명령어 | 설명 |
| --- | --- | --- |
| `a` | 전체 도구 | 모든 도구를 한 화면에 표시 |
| `b` | 카테고리 | AWS 서비스별 카테고리 메뉴 |
| `f` | 즐겨찾기 | 자주 사용하는 도구 관리 |
| `p` | 프로필 | 사용 가능한 AWS 프로필 목록 조회 |
| `h` | 도움말 | 사용법 안내 |
| `q` | 종료 | 프로그램 종료 |

### 검색

```bash
> rds                    # AWS 서비스명 검색
> 미사용                 # 한글 키워드 검색
> /cost                  # 비용 절감 도구
> /security              # 보안 점검 도구
```

## 지원 AWS 서비스

| 카테고리        | 도구 수 | 설명                                    |
| --------------- | ------- | --------------------------------------- |
| EC2             | 5+      | 인스턴스 관리, AMI 감사, EIP 분석       |
| EBS             | 4+      | 볼륨 감사, 스냅샷 관리                  |
| VPC             | 6+      | 보안 그룹, ENI, NAT Gateway, 엔드포인트 |
| S3              | 3+      | 빈 버킷 탐지, 수명 주기 분석            |
| IAM             | 4+      | 사용자/역할 감사, 정책 분석             |
| Lambda          | 4+      | 미사용 함수 탐지, 버전 정리             |
| RDS             | 2+      | 스냅샷 감사, 인스턴스 분석              |
| ELB             | 5+      | ALB/NLB 감사, 대상 그룹                 |
| CloudWatch      | 2+      | 로그 그룹 감사                          |
| Route53         | 1+      | 빈 호스팅 영역 탐지                     |
| ECR             | 1+      | 미사용 저장소 탐지                      |
| KMS             | 1+      | 키 사용 감사                            |
| Secrets Manager | 1+      | 미사용 시크릿 탐지                      |
| Cost            | 2+      | 미사용 리소스 탐지                      |
| SSO             | 1+      | SSO 구성 감사                           |

## 업데이트

```bash
cd aws-automation
git pull
pip install -e .
```

## 라이선스

MIT License - [LICENSE](LICENSE)
