# 플러그인 메타데이터 스키마

`plugins/{service}/__init__.py` 파일의 메타데이터 스키마 정의입니다.

## CATEGORY 스키마

```python
CATEGORY = {
    "name": str,           # 서비스 식별자 (소문자, 영숫자)
    "display_name": str,   # 표시 이름 (예: "EC2", "Lambda")
    "description": str,    # 한글 설명
    "description_en": str, # 영어 설명
    "aliases": list[str],  # 별칭 목록 (검색용)
}
```

### 예시

```python
CATEGORY = {
    "name": "elasticache",
    "display_name": "ElastiCache",
    "description": "ElastiCache 클러스터 관리 도구",
    "description_en": "ElastiCache Cluster Management Tools",
    "aliases": ["redis", "memcached", "cache"],
}
```

### 필드 설명

| 필드 | 필수 | 설명 |
|------|------|------|
| `name` | O | 서비스 식별자, 폴더명과 일치 |
| `display_name` | O | UI에 표시되는 이름 |
| `description` | O | 한글 설명 (메뉴에서 표시) |
| `description_en` | O | 영어 설명 |
| `aliases` | O | 검색 별칭 (빈 리스트 가능) |

---

## TOOLS 스키마

```python
TOOLS = [
    {
        "name": str,           # 도구 이름 (한글)
        "name_en": str,        # 도구 이름 (영어)
        "description": str,    # 도구 설명 (한글)
        "description_en": str, # 도구 설명 (영어)
        "permission": str,     # "read" 또는 "write"
        "module": str,         # 모듈 파일명 (.py 제외)
        "area": str,           # ReportType 또는 ToolType
    },
]
```

### 예시

```python
TOOLS = [
    {
        "name": "미사용 클러스터 분석",
        "name_en": "Unused Cluster Analysis",
        "description": "연결 없는 ElastiCache 클러스터를 탐지합니다",
        "description_en": "Detect ElastiCache clusters with no connections",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
    {
        "name": "보안 점검",
        "name_en": "Security Audit",
        "description": "ElastiCache 보안 설정을 점검합니다",
        "description_en": "Audit ElastiCache security settings",
        "permission": "read",
        "module": "security",
        "area": "security",
    },
]
```

### 필드 설명

| 필드 | 필수 | 설명 |
|------|------|------|
| `name` | O | 도구 표시 이름 (한글) |
| `name_en` | O | 도구 표시 이름 (영어) |
| `description` | O | 도구 설명 (한글) |
| `description_en` | O | 도구 설명 (영어) |
| `permission` | O | `"read"` (조회) 또는 `"write"` (변경) |
| `module` | O | 구현 파일명 (`.py` 제외) |
| `area` | O | 도구 유형 (ReportType 또는 ToolType) |

---

## ReportType (10개)

상태 점검 보고서 유형 (read-only 분석):

| Type | 파일명 | 용도 | 키워드 |
|------|--------|------|--------|
| `inventory` | `inventory.py` | 리소스 현황 파악 | 목록, 현황, 인벤토리 |
| `security` | `security.py` | 보안 취약점 탐지 | 보안, 취약점, 권한, 노출 |
| `cost` | `cost.py` | 비용 최적화 기회 | 비용, 절감, 최적화 |
| `unused` | `unused.py` | 미사용 리소스 식별 | 미사용, unused, idle, 삭제 |
| `audit` | `audit.py` | 구성 설정 점검 | 설정, 구성, 베스트프랙티스 |
| `compliance` | `compliance.py` | 규정 준수 검증 | 규정, 정책, 표준 |
| `performance` | `performance.py` | 성능 병목 분석 | 성능, 병목, 느림 |
| `network` | `network.py` | 네트워크 구조 분석 | 네트워크, 연결, 라우팅 |
| `backup` | `backup.py` | 백업 체계 점검 | 백업, 복구, 스냅샷 |
| `quota` | `quota.py` | 서비스 한도 모니터링 | 한도, 쿼터, 제한 |

### 타입 선택 가이드

| 질문 | 타입 |
|------|------|
| "돈 아낄 수 있나?" | `cost` |
| "안 쓰는 거 있나?" | `unused` |
| "보안 문제 있나?" | `security` |
| "뭐가 있나?" | `inventory` |
| "설정 잘 되어있나?" | `audit` |
| "규정 준수하나?" | `compliance` |
| "느린 건 없나?" | `performance` |
| "네트워크 구조가 어떻게 되나?" | `network` |
| "백업 되고 있나?" | `backup` |
| "한도 다 찼나?" | `quota` |

---

## ToolType (5개)

도구 유형 (active operations):

| Type | 파일명 | 용도 | 키워드 |
|------|--------|------|--------|
| `log` | `log.py` | 로그 분석 및 검색 | 로그, 분석, 검색 |
| `search` | `search.py` | 리소스 역추적 | 검색, 찾기, 추적 |
| `cleanup` | `cleanup.py` | 리소스 정리/삭제 | 정리, 삭제, 제거 |
| `tag` | `tag.py` | 태그 일괄 적용 | 태그, 레이블 |
| `sync` | `sync.py` | 설정/태그 동기화 | 동기화, 복제 |

---

## 서브타입이 있는 서비스

AWS 서비스 중 여러 하위 타입이 있는 경우 파일명 프리픽스 패턴 사용:

### ELB (ALB, NLB, CLB, GWLB)

```
plugins/elb/
├── __init__.py
├── common.py           # 공통 유틸리티
├── alb_unused.py       # ALB 미사용
├── alb_security.py     # ALB 보안
├── nlb_unused.py       # NLB 미사용
├── clb_unused.py       # CLB 미사용
└── gwlb_inventory.py   # GWLB 인벤토리
```

```python
# __init__.py
CATEGORY = {
    "name": "elb",
    "display_name": "ELB",
    "description": "Elastic Load Balancer 관리 도구",
    "description_en": "Elastic Load Balancer Management Tools",
    "aliases": ["alb", "nlb", "clb", "gwlb", "loadbalancer"],
}

TOOLS = [
    {
        "name": "ALB 미사용 분석",
        "name_en": "ALB Unused Analysis",
        "description": "미사용 ALB 탐지",
        "description_en": "Detect unused ALBs",
        "permission": "read",
        "module": "alb_unused",  # 서브타입_타입
        "area": "unused",
    },
]
```

### ElastiCache (Redis, Memcached)

```
plugins/elasticache/
├── __init__.py
├── redis_unused.py
├── redis_security.py
├── memcached_unused.py
└── memcached_security.py
```

### 적용 대상 서비스

| 서비스 | 서브타입 | 파일명 프리픽스 | boto3 |
|--------|----------|-----------------|-------|
| `elb` | ALB, NLB, GWLB, CLB | `alb_`, `nlb_`, `gwlb_`, `clb_` | `elbv2`, `elb` |
| `elasticache` | Redis, Memcached | `redis_`, `memcached_` | `elasticache` |
| `mq` | RabbitMQ, ActiveMQ | `rabbitmq_`, `activemq_` | `mq` |
| `fsx` | Windows, Lustre, ONTAP, OpenZFS | `windows_`, `lustre_`, `ontap_`, `openzfs_` | `fsx` |

---

## 파일 구조 예시

### 단일 서비스

```
plugins/efs/
├── __init__.py     # CATEGORY, TOOLS 정의
├── unused.py       # area="unused"
└── security.py     # area="security"
```

### 서브타입이 있는 서비스

```
plugins/elb/
├── __init__.py
├── common.py       # 공통 유틸리티 (선택)
├── alb_unused.py
├── alb_security.py
├── nlb_unused.py
└── clb_unused.py
```

---

## 서비스 등록 (discovery.py)

새 서비스 추가 시 `core/tools/discovery.py`의 `AWS_SERVICE_NAMES`에 등록:

```python
# core/tools/discovery.py 라인 94~148
AWS_SERVICE_NAMES = {
    "ec2",
    "s3",
    "lambda",
    "rds",
    # ... 기존 서비스
    "bedrock",  # 새로 추가
}
```

---

## 검증 체크리스트

### CATEGORY 검증

- [ ] `name`이 폴더명과 일치
- [ ] `display_name`이 AWS 공식 명칭과 일치
- [ ] `description`과 `description_en` 모두 존재
- [ ] `aliases`에 관련 별칭 포함

### TOOLS 검증

- [ ] 모든 필수 필드 존재
- [ ] `module`이 실제 파일명과 일치 (.py 제외)
- [ ] `area`가 유효한 ReportType 또는 ToolType
- [ ] `permission`이 `"read"` 또는 `"write"`

### 파일 검증

- [ ] `discovery.py`에 서비스 등록
- [ ] `{module}.py` 파일에 `run(ctx)` 함수 존재
- [ ] 서브타입 서비스는 프리픽스 패턴 사용

---

## 참조

- `plugins/efs/__init__.py` - 단순 서비스 예시
- `plugins/elb/__init__.py` - 서브타입 서비스 예시
- `core/tools/discovery.py` - 서비스 등록
- `core/tools/output/report_types.py` - ReportType, ToolType 정의
- `.claude/commands/make-plugin-service.md` - 새 서비스 생성 가이드
- `.claude/commands/add-plugin-tool.md` - 기존 서비스에 도구 추가
