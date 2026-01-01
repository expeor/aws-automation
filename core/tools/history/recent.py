"""
pkg/history/recent.py - 최근 사용 도구 관리

LRU 기반으로 최근 사용한 도구 이력 관리
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


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


class RecentHistory:
    """최근 사용 이력 관리 (LRU 기반)"""

    MAX_ITEMS = 50
    _instance: Optional["RecentHistory"] = None

    def __new__(cls) -> "RecentHistory":
        """싱글톤 패턴"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._path = self._get_history_path()
        self._items: List[RecentItem] = []
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

    def get_recent(self, limit: int = 5) -> List[RecentItem]:
        """최근 사용 목록 (시간순)

        Args:
            limit: 반환할 최대 개수

        Returns:
            최근 사용 항목 리스트
        """
        return self._items[:limit]

    def get_frequent(self, limit: int = 5) -> List[RecentItem]:
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

    def get_all(self) -> List[RecentItem]:
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
        """파일에서 로드"""
        if not self._path.exists():
            self._items = []
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._items = [RecentItem(**item) for item in data]
        except (json.JSONDecodeError, TypeError, KeyError):
            self._items = []

    def _save(self) -> None:
        """파일에 저장"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(item) for item in self._items]
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def reload(self) -> None:
        """파일에서 다시 로드 (외부 변경 반영)"""
        self._load()
