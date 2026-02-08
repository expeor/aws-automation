"""최근 사용 도구 관리.

LRU(Least Recently Used) 기반으로 최근 사용한 도구 이력을 관리합니다.
싱글톤 패턴으로 구현되며, JSON 파일 기반 영속성과 원자적 저장을 지원합니다.
"""

from __future__ import annotations

import json
import logging
import tempfile
import threading
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RecentItem:
    """최근 사용 항목.

    도구 사용 이력의 개별 항목을 나타냅니다.

    Attributes:
        category: 카테고리 이름 (예: "ec2", "vpc").
        tool_name: 도구 표시 이름 (예: "미사용 볼륨").
        tool_module: 도구 모듈 이름 (예: "unused").
        last_used: 마지막 사용 일시 (ISO format).
        use_count: 누적 사용 횟수 (기본값: 1).
    """

    category: str
    tool_name: str
    tool_module: str
    last_used: str
    use_count: int = 1

    def get_display_time(self) -> str:
        """마지막 사용 시각을 상대 시간 문자열로 반환합니다.

        Returns:
            상대 시간 표시 문자열 (예: "방금 전", "2분 전", "1시간 전",
            "3일 전", "01/15"). 파싱 실패 시 빈 문자열.
        """
        try:
            last = datetime.fromisoformat(self.last_used)
            now = datetime.now()
            diff = now - last

            seconds = diff.total_seconds()

            if seconds < 60:
                return "방금 전"
            elif seconds < 3600:
                minutes = int(seconds / 60)
                return f"{minutes}분 전"
            elif seconds < 86400:
                hours = int(seconds / 3600)
                return f"{hours}시간 전"
            elif seconds < 604800:
                days = int(seconds / 86400)
                return f"{days}일 전"
            else:
                return last.strftime("%m/%d")
        except (ValueError, TypeError):
            return ""


# _load()에서 사용할 필드 이름 집합 (모듈 로드 시 1회 계산)
_RECENT_FIELDS = {f.name for f in fields(RecentItem)}


class RecentHistory:
    """최근 사용 이력 관리 (LRU 기반).

    도구 사용 이력을 LRU 방식으로 관리합니다. 동일 도구 재사용 시
    사용 횟수가 증가하고 목록 맨 앞으로 이동합니다.
    싱글톤 패턴(double-check locking)으로 구현되어 애플리케이션 전체에서
    하나의 인스턴스만 사용됩니다.

    Attributes:
        MAX_ITEMS: 최대 이력 항목 수 (50개).
    """

    MAX_ITEMS = 50
    _instance: RecentHistory | None = None
    _lock = threading.Lock()
    _initialized: bool

    def __new__(cls) -> RecentHistory:
        """싱글톤 인스턴스를 반환합니다 (double-check locking).

        Returns:
            RecentHistory 싱글톤 인스턴스.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """RecentHistory를 초기화합니다.

        이미 초기화된 경우 재초기화를 건너뜁니다 (싱글톤).
        이력 파일에서 기존 데이터를 로드합니다.
        """
        if self._initialized:
            return
        self._path = self._get_history_path()
        self._items: list[RecentItem] = []
        self._load()
        self._initialized = True

    def _get_history_path(self) -> Path:
        """이력 JSON 파일 경로를 반환합니다.

        Returns:
            이력 파일의 Path 객체 (``temp/history/recent.json``).
        """
        from core.tools.cache import get_cache_path

        return Path(get_cache_path("history", "recent.json"))

    def add(
        self,
        category: str,
        tool_name: str,
        tool_module: str,
    ) -> None:
        """사용 기록 추가

        Args:
            category: 카테고리 이름 (예: "ebs")
            tool_name: 도구 표시 이름 (예: "미사용 볼륨")
            tool_module: 도구 모듈 이름 (예: "unused")
        """
        now = datetime.now().isoformat()

        # 기존 항목 찾기
        for i, item in enumerate(self._items):
            if item.category == category and item.tool_module == tool_module:
                # 기존 항목 업데이트
                item.last_used = now
                item.use_count += 1
                item.tool_name = tool_name  # 이름 변경 대응
                # 맨 앞으로 이동
                self._items.pop(i)
                self._items.insert(0, item)
                self._save()
                return

        # 새 항목 추가 (맨 앞에)
        self._items.insert(
            0,
            RecentItem(
                category=category,
                tool_name=tool_name,
                tool_module=tool_module,
                last_used=now,
                use_count=1,
            ),
        )

        # 최대 개수 제한
        if len(self._items) > self.MAX_ITEMS:
            self._items = self._items[: self.MAX_ITEMS]

        self._save()

    def get_recent(self, limit: int = 5) -> list[RecentItem]:
        """최근 사용 목록 (시간순)

        Args:
            limit: 반환할 최대 개수

        Returns:
            최근 사용 항목 리스트
        """
        return self._items[:limit]

    def get_frequent(self, limit: int = 5) -> list[RecentItem]:
        """자주 사용 목록 (사용 횟수순)

        Args:
            limit: 반환할 최대 개수

        Returns:
            자주 사용 항목 리스트
        """
        sorted_items = sorted(
            self._items,
            key=lambda x: x.use_count,
            reverse=True,
        )
        return sorted_items[:limit]

    def get_all(self) -> list[RecentItem]:
        """전체 사용 이력을 반환합니다.

        Returns:
            RecentItem 리스트의 복사본 (최근 사용순).
        """
        return self._items.copy()

    def clear(self) -> None:
        """전체 사용 이력을 초기화합니다.

        모든 항목을 삭제하고 파일에 빈 목록을 저장합니다.
        """
        self._items.clear()
        self._save()

    def remove(self, category: str, tool_module: str) -> bool:
        """특정 이력 항목을 삭제합니다.

        Args:
            category: 카테고리 이름.
            tool_module: 도구 모듈 이름.

        Returns:
            삭제 성공 여부 (존재하지 않으면 False).
        """
        for i, item in enumerate(self._items):
            if item.category == category and item.tool_module == tool_module:
                self._items.pop(i)
                self._save()
                return True
        return False

    def _load(self) -> None:
        """파일에서 로드

        개별 항목 파싱 실패 시 해당 항목만 건너뛰고 나머지는 유지.
        알 수 없는 필드는 무시하여 스키마 변경에 대한 하위 호환성 보장.
        """
        if not self._path.exists():
            self._items = []
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                self._items = []
                return

            items: list[RecentItem] = []
            for raw in data:
                if not isinstance(raw, dict):
                    continue
                try:
                    filtered = {k: v for k, v in raw.items() if k in _RECENT_FIELDS}
                    items.append(RecentItem(**filtered))
                except (TypeError, KeyError):
                    logger.debug("최근 사용 항목 로드 스킵: %s", raw)
                    continue

            self._items = items
        except (json.JSONDecodeError, OSError):
            self._items = []

    def _save(self) -> None:
        """파일에 원자적으로 저장합니다 (write-to-temp-then-rename).

        임시 파일에 먼저 기록한 후 rename하여 데이터 손실을 방지합니다.
        원자적 쓰기 실패 시 직접 쓰기로 fallback합니다.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(item) for item in self._items]
        content = json.dumps(data, ensure_ascii=False, indent=2)
        try:
            fd, tmp_path = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp", prefix=".recent_")
            try:
                with open(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                Path(tmp_path).replace(self._path)
            except BaseException:
                Path(tmp_path).unlink(missing_ok=True)
                raise
        except OSError:
            # Fallback: 원자적 쓰기 실패 시 직접 쓰기
            self._path.write_text(content, encoding="utf-8")

    def reload(self) -> None:
        """파일에서 이력 데이터를 다시 로드합니다.

        외부에서 파일이 변경된 경우 최신 상태를 반영할 때 사용합니다.
        """
        self._load()
