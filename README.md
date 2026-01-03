# AA (AWS Automation)

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/expeor/aws-automation)

AWS 운영 자동화를 위한 CLI 도구입니다.

미사용 리소스 탐지, 보안 점검, IAM 감사, ALB 로그 분석 등 AWS 운영에 필요한 도구들을 하나로 통합했습니다. 멀티 계정·멀티 리전 환경을 지원하며, 대화형 메뉴에서 키워드 검색으로 필요한 도구를 빠르게 찾을 수 있습니다. 분석 결과는 Excel 보고서로 저장됩니다. 현재 14개 AWS 서비스를 지원하며, 지속적으로 새로운 도구를 추가할 예정입니다.

## 주요 기능

- **멀티 계정 & 리전**: 여러 AWS 계정과 리전을 동시에 분석
- **다중 인증 지원**: SSO Session, SSO Profile, Access Key 자동 감지
- **Excel 보고서**: 분석 결과를 Excel 파일로 자동 저장
- **키워드 검색**: 대화형 메뉴에서 도구를 빠르게 검색
- **플러그인 구조**: 새로운 도구를 쉽게 추가 가능

## 설치

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

```text
명령어
  a 전체 도구    b 서비스별    c 카테고리    f 즐겨찾기
  p 프로필       h 도움말      q 종료

검색: 키워드 또는 /cost /security /ops /inv
```

| 키  | 설명              |
| --- | ----------------- |
| `a` | 모든 도구 표시    |
| `b` | AWS 서비스별 보기 |
| `c` | 카테고리별 보기   |
| `f` | 즐겨찾기 관리     |
| `p` | AWS 프로필 목록   |
| `q` | 종료              |

### 검색

```bash
> rds              # 서비스명으로 검색
> 미사용           # 한글 키워드 검색
> /cost            # 비용 절감 관련 도구
> /security        # 보안 점검 관련 도구
```

## 지원 서비스

| 서비스          | 주요 도구                                |
| --------------- | ---------------------------------------- |
| EC2             | 인스턴스 관리, AMI 감사, EIP 분석        |
| EBS             | 미사용 볼륨 탐지, 스냅샷 관리            |
| VPC             | 보안 그룹, ENI, NAT Gateway, 엔드포인트  |
| S3              | 빈 버킷 탐지, 수명 주기 분석             |
| IAM             | 사용자/역할 감사, 정책 분석              |
| Lambda          | 미사용 함수 탐지, 버전 정리              |
| RDS             | 스냅샷 감사, 인스턴스 분석               |
| ELB             | ALB/NLB 감사, 로그 분석                  |
| CloudWatch      | 로그 그룹 감사                           |
| Route53         | 빈 호스팅 영역 탐지                      |
| ECR             | 미사용 저장소 탐지                       |
| KMS             | 키 사용 감사                             |
| Secrets Manager | 미사용 시크릿 탐지                       |
| SSO             | SSO 구성 감사                            |

## 요구 사항

- Python 3.10+
- AWS CLI 프로필 설정 (`~/.aws/config`)

## 업데이트

```bash
git pull && pip install -e .
```

## 라이선스

MIT License - [LICENSE](LICENSE)
