# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.2] - 2026-02-07

### Changed
- refactor: standardize report patterns with `generate_dual_report()` as primary API
  - Refactor `analyzers/rds/unused.py`, `analyzers/fn/comprehensive.py`, `analyzers/vpc/nat_audit.py` as reference implementations
  - Add `html_builder` parameter to `generate_dual_report()` for custom HTML generation
  - Add `build_workbook()` method to `NATExcelReporter` (backward-compatible)

### Fixed
- fix(skills): update stale `core.tools.io.*` import paths to `shared.io.*` in skill documents
- fix(skills): add missing `@safe_aws_call`, `RetryConfig` documentation to error-handling skill

### Added
- docs: add `analyzers-vs-reports.md` skill for analyzer/report boundary guidance
- docs: add `debugging-troubleshooting.md` skill for test/debug patterns

## [0.4.1] - 2026-01-30

### Fixed
- fix(discovery): scan root folder `__init__.py` for report category registration
  - `aa report` command now works correctly with aliases (reports, rpt)
- fix(category): sort categories alphabetically for consistency with main menu
  - `aa report` → `0` now shows same order as `aa` → `s` (service view)

## [0.4.0] - 2026-01-30

### Added
- feat(iam): add user snapshot report with Excel/HTML output
- feat(iam): add unused roles detection tool
- feat(ec2): add unencrypted EBS volume detection tool
- feat(log_analyzer): add TPS (transactions per second) reporter
- feat(log_analyzer): add SLA compliance reporter
- feat(log_analyzer): add SSL/TLS security reporter
- feat(log_analyzer): add connection failure reporter
- feat(log_analyzer): add processing time reporter
- feat(log_analyzer): add target performance reporter
- feat(log_analyzer): add security events reporter
- feat(scheduled): add execution history tracking
- feat(cli): add code-review skill for self-review checklist
- feat(ip_search): add region/service filtering for public IP lookup
- feat(ip_search): add selective provider cache refresh support
- feat(cli): add service selector UI with 's' shortcut for service-based navigation

### Changed
- refactor(cli): main menu UI improvements and banner updates
- refactor(cli): redesign ASCII banner with mountain-style logo
- refactor(cli): reorder main menu shortcuts for better UX
- refactor(log_analyzer): enhance ALB log analyzer with 7 new reporters
- refactor(scheduled): improve scheduled reports menu with history view
- refactor(ip_search): enhance private IP lookup functionality
- refactor(ip_search): improve public IP search result display

## [0.3.1] - 2026-01-24

### Changed
- refactor: standardize report completion output with `print_report_complete()` common function

## [0.3.0] - 2026-01-24

### Added
- feat(html): add time series chart with CloudWatch-style adaptive resolution
- feat(html): add dynamic chart sizing based on data complexity
- feat: add Claude Code commands for plugin development workflow
- feat: add automation hooks for test, mypy, and metadata validation
- feat: add agents for doc-generator, migration, and performance
- feat: add pattern skills for Excel, error handling, and parallel execution
- feat: add brave-search MCP and update all agents with MCP guidance
- feat: add context7 and semgrep MCP for code review
- feat: add MCP tool guidance to aws-expert agent

### Changed
- refactor: standardize area field and relocate core/data to plugins
- refactor: remove MCPs requiring API keys

## [0.2.0] - 2026-01-23

### Added
- feat: complete i18n implementation for all UI components
- feat: add i18n support with --lang option for English UI

### Changed
- refactor: increase tool name display length in CategoryStep
- refactor: remove permission and area legend printing from CategoryStep
- refactor: standardize tool naming conventions across all plugins
- refactor: improve IP search with parser consolidation and parallel enrichment
- refactor: implement core/data architecture with inventory caching layer
- refactor: adjust column widths in category and main menu tables for better display
- refactor: pricing 모듈 개선 및 버그 수정
- refactor: simplify principal handling and optimize Athena work group retrieval
- refactor: area 분류 체계 표준화 (15개 영역)

### Fixed
- fix: restore VPC audit modules used by network_analysis and unused_all
- fix: use ASCII-compatible characters in banner for Windows cp949 encoding

## [0.1.1] - 2026-01-05

### Changed
- Development Status: Alpha → Beta
- Python 3.14 지원 제거 (미출시)

### Added
- PyPI 배지 및 `pip install aws-automation` 설치 방법 추가
- classifiers 보강 (Intended Audience, Topic, OS)

### Fixed
- CI ruff format/lint 및 mypy 타입 체크 수정
- `sys.platform` 기반 플랫폼 감지로 변경

## [0.1.0] - 2026-01-04

### Added
- **Core**
  - 멀티 계정 & 멀티 리전 동시 분석 지원
  - SSO Session, SSO Profile, Access Key 자동 감지
  - Excel 보고서 자동 생성
  - 대화형 메뉴 키워드 검색
  - Headless 모드 (CI/CD용)
  - 프로필 그룹 관리

- **Plugins (19개 AWS 서비스)**
  - EC2: EBS/EIP/Snapshot/AMI 미사용 분석
  - VPC: 보안 그룹 감사, NAT Gateway, 엔드포인트, IP 검색
  - S3: 빈 버킷 탐지
  - IAM: 사용자/역할 감사, 정책 분석
  - RDS: 스냅샷 감사
  - ELB: ALB/NLB 감사, 로그 분석, 마이그레이션 어드바이저
  - Lambda: 미사용/버전/Provisioned Concurrency 분석
  - CloudWatch: 로그 그룹 감사
  - CloudTrail: Trail 감사
  - CloudFormation: 리소스 검색
  - Route53: 빈 호스팅 영역 탐지
  - ECR: 미사용 저장소 탐지
  - KMS: 키 사용 감사
  - Secrets Manager: 미사용 시크릿 탐지
  - SSO: SSO 구성 감사
  - ACM: 미사용/만료 임박 인증서 탐지
  - EFS: 미사용 파일시스템 탐지
  - SNS/SQS: 미사용 토픽/큐 탐지
  - ElastiCache: 미사용 클러스터 탐지
  - API Gateway: 미사용 API 탐지
  - EventBridge: 미사용 규칙 탐지
  - DynamoDB: 용량 모드 분석, 미사용 테이블 탐지
  - CodeCommit: 미사용 리포지토리 탐지

- **Cost Optimization**
  - AWS Cost Optimization Hub 연동
  - 전체 미사용 리소스 통합 분석
  - 리소스별 예상 비용 계산

- **Tag Editor**
  - MAP 2.0 태그 감사/적용
  - EC2→EBS 태그 동기화

- **Health Dashboard**
  - AWS Personal Health Dashboard 연동
  - 패치 분석

### Security
- CI/CD 파이프라인 보안 강화
- ruff, mypy, bandit 린팅/타입 체크

[0.4.1]: https://github.com/expeor/aws-automation/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/expeor/aws-automation/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/expeor/aws-automation/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/expeor/aws-automation/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/expeor/aws-automation/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/expeor/aws-automation/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/expeor/aws-automation/releases/tag/v0.1.0
