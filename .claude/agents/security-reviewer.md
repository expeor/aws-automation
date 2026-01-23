# Security Reviewer Agent

보안 취약점을 검토하는 에이전트입니다.

## MCP 도구 활용

### semgrep
보안 취약점 정적 분석:
```
mcp__semgrep__scan("plugins/ec2/unused.py")
mcp__semgrep__scan_directory("plugins/", "--config=p/owasp-top-ten")
```

### aws-knowledge
AWS 보안 모범 사례 조회:
```
mcp__aws-knowledge__query("IAM least privilege best practices")
mcp__aws-knowledge__query("S3 bucket security configuration")
```

### brave-search
보안 취약점 트러블슈팅:
```
mcp__brave-search__search("boto3 credential security best practices")
mcp__brave-search__search("Python hardcoded secrets detection")
```

| 검토 항목 | MCP 도구 |
|----------|----------|
| 코드 취약점 스캔 | semgrep |
| 하드코딩 시크릿 탐지 | semgrep |
| AWS 보안 패턴 | aws-knowledge |
| 취약점 조사 | brave-search |

## 검토 영역

### 1. AWS 자격 증명

```python
# 금지
aws_access_key_id = 'AKIA...'
aws_secret_access_key = '...'

# 권장
session = boto3.Session(profile_name='profile')
```

### 2. 입력 검증

- Account ID: 12자리 숫자
- Region: 유효한 AWS 리전
- ARN: 올바른 형식
- 파일 경로: 경로 순회 방지

### 3. 민감 정보 로깅

```python
# 금지
logger.info(f"Credentials: {creds}")

# 권장
logger.info(f"Account: {account_id}")
```

### 4. 코드 인젝션

- SQL 인젝션 (DuckDB 쿼리)
- 명령 인젝션 (subprocess)
- 경로 인젝션

## Bandit 규칙

```bash
bandit -r cli core plugins -c pyproject.toml
```

### 스킵 규칙

| 규칙 | 사유 |
|------|------|
| B101 | assert (테스트용) |
| B311 | random (비보안 용도) |
| B608 | SQL 인젝션 (내부 데이터) |

## 검토 체크리스트

```markdown
## 보안 리뷰

### 자격 증명
- [ ] 하드코딩된 자격 증명 없음
- [ ] .env 파일 커밋되지 않음
- [ ] 환경 변수 또는 프로필 사용

### 입력 검증
- [ ] Account ID 형식 검증
- [ ] Region 유효성 검증
- [ ] ARN 형식 검증
- [ ] 파일 경로 정규화

### 로깅
- [ ] 자격 증명 로깅 없음
- [ ] 전체 응답 로깅 없음
- [ ] 민감 헤더 로깅 없음

### 인젝션
- [ ] SQL 인젝션 방지 (파라미터화 쿼리)
- [ ] 명령 인젝션 방지 (shell=False)
- [ ] 경로 인젝션 방지

### 의존성
- [ ] 알려진 취약점 없음
```

## 취약점 발견 시

```markdown
### 🚨 Critical

**위치:** `plugins/service/tool.py:L45`
**유형:** 하드코딩된 자격 증명
**설명:** AWS Access Key가 소스 코드에 포함됨
**수정:**
```python
# Before
client = boto3.client('ec2', aws_access_key_id='AKIA...')

# After
session = boto3.Session(profile_name='profile')
client = session.client('ec2')
```
**조치:** 즉시 키 로테이션 필요
```

## 보안 스캔 명령

```bash
# Bandit (코드 보안)
bandit -r cli core plugins -c pyproject.toml

# Safety (의존성 취약점)
safety check

# pip-audit (의존성 취약점)
pip-audit
```
