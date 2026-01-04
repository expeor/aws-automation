"""
pkg/history/favorites.py - 즐겨찾기 관리

사용자가 직접 등록한 즐겨찾기 도구 관리
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class FavoriteItem:
    """즐겨찾기 항목"""

    category: str
    tool_name: str
    tool_module: str
    added_at: str  # ISO format
    order: int = 0  # 정렬 순서 (낮을수록 상위)


class FavoritesManager:
    """즐겨찾기 관리"""

    MAX_ITEMS = 20
    _instance: Optional["FavoritesManager"] = None

    def __new__(cls) -> "FavoritesManager":
        """싱글톤 패턴"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._path = self._get_favorites_path()
        self._items: list[FavoriteItem] = []
        self._load()
        self._initialized = True

    def _get_favorites_path(self) -> Path:
        """즐겨찾기 파일 경로"""
        from core.tools.cache import get_cache_path

        return Path(get_cache_path("history", "favorites.json"))

    def add(
        self,
        category: str,
        tool_name: str,
        tool_module: str,
    ) -> bool:
        """즐겨찾기 추가

        Args:
            category: 카테고리 이름
            tool_name: 도구 표시 이름
            tool_module: 도구 모듈 이름

        Returns:
            추가 성공 여부 (이미 존재하면 False)
        """
        # 중복 체크
        for item in self._items:
            if item.category == category and item.tool_module == tool_module:
                return False

        # 최대 개수 체크
        if len(self._items) >= self.MAX_ITEMS:
            return False

        # 새 항목 추가
        now = datetime.now().isoformat()
        max_order = max((item.order for item in self._items), default=-1)

        self._items.append(
            FavoriteItem(
                category=category,
                tool_name=tool_name,
                tool_module=tool_module,
                added_at=now,
                order=max_order + 1,
            )
        )

        self._save()
        return True

    def remove(self, category: str, tool_module: str) -> bool:
        """즐겨찾기 삭제

        Returns:
            삭제 성공 여부
        """
        for i, item in enumerate(self._items):
            if item.category == category and item.tool_module == tool_module:
                self._items.pop(i)
                self._save()
                return True
        return False

    def toggle(
        self,
        category: str,
        tool_name: str,
        tool_module: str,
    ) -> bool:
        """즐겨찾기 토글 (있으면 삭제, 없으면 추가)

        Returns:
            토글 후 즐겨찾기 상태 (True: 추가됨, False: 삭제됨)
        """
        if self.is_favorite(category, tool_module):
            self.remove(category, tool_module)
            return False
        else:
            self.add(category, tool_name, tool_module)
            return True

    def is_favorite(self, category: str, tool_module: str) -> bool:
        """즐겨찾기 여부 확인"""
        return any(item.category == category and item.tool_module == tool_module for item in self._items)

    def get_all(self) -> list[FavoriteItem]:
        """전체 즐겨찾기 목록 (순서대로)"""
        return sorted(self._items, key=lambda x: x.order)

    def move_up(self, category: str, tool_module: str) -> bool:
        """순서 올리기"""
        items = self.get_all()
        for i, item in enumerate(items):
            if item.category == category and item.tool_module == tool_module:
                if i == 0:
                    return False  # 이미 최상위
                # 이전 항목과 순서 교환
                items[i].order, items[i - 1].order = (
                    items[i - 1].order,
                    items[i].order,
                )
                self._items = items
                self._save()
                return True
        return False

    def move_down(self, category: str, tool_module: str) -> bool:
        """순서 내리기"""
        items = self.get_all()
        for i, item in enumerate(items):
            if item.category == category and item.tool_module == tool_module:
                if i == len(items) - 1:
                    return False  # 이미 최하위
                # 다음 항목과 순서 교환
                items[i].order, items[i + 1].order = (
                    items[i + 1].order,
                    items[i].order,
                )
                self._items = items
                self._save()
                return True
        return False

    def clear(self) -> None:
        """전체 초기화"""
        self._items.clear()
        self._save()

    def _load(self) -> None:
        """파일에서 로드"""
        if not self._path.exists():
            self._items = []
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._items = [FavoriteItem(**item) for item in data]
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
        """파일에서 다시 로드"""
        self._load()
