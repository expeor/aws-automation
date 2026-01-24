# /sync-index - 프로젝트 인덱스 갱신

프로젝트 구조를 스캔하여 `.claude/project-index.md`를 갱신합니다.
Claude Code의 토큰 사용량을 줄이고 프로젝트 탐색을 빠르게 합니다.

## 사용법

```
/sync-index [section]
```

예시:
```
/sync-index           # 전체 갱신
/sync-index plugins   # 플러그인만 갱신
```

## 실행 순서

### 1. 스크립트 실행

```bash
python scripts/generate_index.py
```

스크립트가 수행하는 작업:
1. `plugins/*/__init__.py` 스캔 → CATEGORY, TOOLS 추출
2. `core/` 디렉토리 구조 수집
3. `git status`로 최근 변경 확인
4. `.claude/project-index.md` 갱신

### 2. 결과 확인

생성된 인덱스 파일 읽기:

```bash
head -50 .claude/project-index.md
```

### 3. 결과 요약 출력

```
/sync-index 완료

[인덱스 생성]
  ✓ 플러그인: 34개 서비스, 70+ 도구
  ✓ Core 모듈: 5개
  ✓ 파일: 388개 Python 파일
  ✓ 최근 변경: 4개 new, 12개 modified

출력 파일: .claude/project-index.md
```

## 생성되는 인덱스 구조

```markdown
# Project Index

## Quick Stats
- Files, Plugins count
- Core modules
- Branch info

## Directory Map
- cli/, core/, plugins/, tests/

## Core Modules
- auth, parallel, tools, region

## Plugin Registry
- 34 services with tool counts

## Core API Summary
- parallel_collect, get_client
- generate_reports, Workbook

## Recent Changes
- New/modified files from git

## Plugin Details (collapsed)
- Full tool list per service
```

## 자동 갱신 트리거

`.claude/hooks.json`에 설정된 훅:

1. **플러그인 메타데이터 변경 시**:
   - `plugins/**/__init__.py` 수정 시 알림
   - `/sync-index` 실행 권장

2. **새 플러그인 추가 시**:
   - `/make-plugin-service` 실행 후 자동 갱신 권장

## 참조 파일

- `scripts/generate_index.py` - 인덱스 생성 스크립트
- `.claude/project-index.md` - 생성된 인덱스 (읽기 전용)
- `CLAUDE.md` - 프로젝트 규칙 (Progressive Disclosure)

## 주의사항

1. **읽기 전용**: `project-index.md`는 직접 수정하지 마세요
2. **Git 제외**: `.claude/project-index.md`는 `.gitignore`에 추가 권장
3. **캐시 갱신**: 플러그인 추가/삭제 후 반드시 실행
