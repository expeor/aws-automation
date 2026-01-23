# 플러그인 개발 가이드

새로운 AWS 분석 도구 플러그인 작성 방법입니다.

## 플러그인 구조

```
plugins/
└── {service}/
    ├── __init__.py       # (선택) 패키지 초기화
    ├── {tool_name}.py    # 도구 구현
    └── common.py         # (선택) 공통 유틸리티
```

## 기본 도구 작성

### 1. 도구 파일 생성

```python
# plugins/elasticache/unused.py
"""ElastiCache 미사용 클러스터 탐지"""

from dataclasses import dataclass
from core.tools.base import BaseToolRunner


@dataclass
class ToolRunner(BaseToolRunner):
    """ElastiCache 미사용 클러스터 분석"""

    def get_tools(self) -> dict:
        return {
            "미사용 클러스터": self._find_unused_clusters,
        }

    def _find_unused_clusters(self) -> list[dict]:
        """미사용 클러스터 탐지"""
        results = []

        for region, session in self.iterate_regions():
            client = session.client('elasticache')
            clusters = self._get_clusters(client)

            for cluster in clusters:
                if self._is_unused(cluster):
                    results.append({
                        'Region': region,
                        'ClusterId': cluster['CacheClusterId'],
                        'Engine': cluster['Engine'],
                        'Status': cluster['CacheClusterStatus'],
                    })

        return results

    def _get_clusters(self, client) -> list:
        """클러스터 목록 조회 (paginator 사용)"""
        clusters = []
        paginator = client.get_paginator('describe_cache_clusters')

        for page in paginator.paginate():
            clusters.extend(page['CacheClusters'])

        return clusters

    def _is_unused(self, cluster: dict) -> bool:
        """미사용 여부 판단 로직"""
        # 구현...
        return False
```

### 2. 메뉴 등록

`cli/tools/menu.py`에 도구 메타데이터 추가:

```python
from cli.tools.types import ToolMetadata

TOOLS = {
    # ... 기존 도구들

    "elasticache/unused": ToolMetadata(
        name="미사용 클러스터",
        service="ElastiCache",
        category="Database",
        area="Cost",
        description="미사용 ElastiCache 클러스터 탐지",
    ),
}
```

## 도구 메타데이터 필드

| 필드 | 설명 | 예시 |
|------|------|------|
| name | 도구 표시 이름 | "미사용 클러스터" |
| service | AWS 서비스명 | "ElastiCache" |
| category | AWS 카테고리 | "Database" |
| area | 점검 영역 | "Cost", "Security", "Operation" |
| description | 도구 설명 | "미사용 ElastiCache 클러스터 탐지" |

## 병렬 처리 패턴

대량 리소스 처리 시:

```python
from core.parallel import run_parallel

def _find_unused_clusters(self) -> list[dict]:
    results = run_parallel(
        items=self.regions,
        func=self._analyze_region,
        desc="리전 분석 중",
    )
    return [item for sublist in results if sublist for item in sublist]

def _analyze_region(self, region: str) -> list[dict]:
    session = self.get_session(region)
    client = session.client('elasticache')
    # ...
```

## Excel 출력

core/output 모듈 사용:

```python
from core.output import ExcelWriter

def _find_unused_clusters(self) -> list[dict]:
    results = self._collect_results()

    if results:
        writer = ExcelWriter("elasticache_unused")
        writer.write_sheet("미사용 클러스터", results)
        writer.save()

    return results
```

## 에러 핸들링

```python
from botocore.exceptions import ClientError
from rich.console import Console

console = Console()

def _analyze_region(self, region: str) -> list[dict]:
    try:
        session = self.get_session(region)
        client = session.client('elasticache')
        return self._get_unused(client, region)
    except ClientError as e:
        if e.response['Error']['Code'] == 'AccessDenied':
            console.print(f"[yellow]⚠️ {region}: 권한 부족[/yellow]")
            return []
        raise
```

## 테스트 작성

```python
# tests/plugins/elasticache/test_unused.py
import pytest
from moto import mock_aws
from plugins.elasticache.unused import ToolRunner


@mock_aws
def test_find_unused_clusters():
    runner = ToolRunner(regions=['ap-northeast-2'])
    results = runner._find_unused_clusters()
    assert isinstance(results, list)
```

## 체크리스트

- [ ] BaseToolRunner 상속
- [ ] get_tools() 구현
- [ ] Paginator 사용 (대량 리소스)
- [ ] 에러 핸들링 (AccessDenied 등)
- [ ] 메뉴 등록 (cli/tools/menu.py)
- [ ] 테스트 작성
- [ ] 린트 통과 (`ruff check`)
