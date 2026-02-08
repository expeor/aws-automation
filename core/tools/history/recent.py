"""
core/tools/history/recent.py - 최근 사용 도구 관리

LRU 기반으로 최근 사용한 도구 이력 관리
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
    """최근 사용 항목"""

    category: str
    tool_name: str
    tool_module: str
    last_used: str  # ISO format
    use_count: int = 1

    def get_display_time(self) -> str:
        """상대 시간 표시 (예: '2분 전', '1시간 전')"""
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
    """최근 사용 이력 관리 (LRU 기반)"""

    MAX_ITEMS = 50
    _instance: RecentHistory | None = None
    _lock = threading.Lock()

    def __new__(cls) -> RecentHistory:
        """싱글톤 패턴 (double-check locking)"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._path = self._get_history_path()
        self._items: list[RecentItem] = []
        self._load()
        self._initialized = True

    def _get_history_path(self) -> Path:
        """이력 파일 경로"""
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
        """전체 이력"""
        return self._items.copy()

    def clear(self) -> None:
        """이력 초기화"""
        self._items.clear()
        self._save()

    def remove(self, category: str, tool_module: str) -> bool:
        """특정 항목 삭제

        Returns:
            삭제 성공 여부
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
        """파일에 원자적으로 저장 (write-to-temp-then-rename)"""
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
        """파일에서 다시 로드 (외부 변경 반영)"""
        self._load()
