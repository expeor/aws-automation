"""공유 유틸리티 - analyzers와 reports에서 공통 사용.

이 패키지는 다음 두 가지 카테고리의 공유 유틸리티를 제공합니다:

- aws: AWS 관련 유틸리티 (메트릭, 가격, 인벤토리, IP 범위 등)
- io: 입출력 유틸리티 (Excel, HTML, CSV, 파일 I/O 등)

의존성 구조:
    core (인프라)
       ↑
    shared (공유 유틸리티)
       ↑
    analyzers / reports
"""

from . import aws, io

__all__ = ["aws", "io"]
