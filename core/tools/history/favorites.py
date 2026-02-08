"""
core/tools/history/favorites.py - 즐겨찾기 관리

사용자가 직접 등록한 즐겨찾기 도구 관리
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
class FavoriteItem:
    """즐겨찾기 항목

    Attributes:
        category: 카테고리 이름 (서비스명)
        tool_name: 도구 표시 이름 (item_type="category"일 경우 카테고리 표시 이름)
        tool_module: 도구 모듈 이름 (item_type="category"일 경우 빈 문자열)
        added_at: 추가 일시 (ISO format)
        order: 정렬 순서 (낮을수록 상위)
        item_type: 항목 타입 ("tool" 또는 "category")
        ref: 참조 정보 (category/module 형식, 미래 확장용)
    """

    category: str
    tool_name: str
    tool_module: str
    added_at: str  # ISO format
    order: int = 0  # 정렬 순서 (낮을수록 상위)
    item_type: str = "tool"  # "tool" 또는 "category"
    ref: str = ""  # 참조 (category/module 형식)


# _load()에서 사용할 필드 이름 집합 (모듈 로드 시 1회 계산)
_FAVORITE_FIELDS = {f.name for f in fields(FavoriteItem)}


class FavoritesManager:
    """즐겨찾기 관리"""

    MAX_ITEMS = 20
    _instance: FavoritesManager | None = None
    _lock = threading.Lock()
    _initialized: bool

    def __new__(cls) -> FavoritesManager:
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
        item_type: str = "tool",
    ) -> bool:
        """즐겨찾기 추가

        Args:
            category: 카테고리 이름
            tool_name: 도구 표시 이름 (item_type="category"일 경우 카테고리 표시 이름)
            tool_module: 도구 모듈 이름 (item_type="category"일 경우 빈 문자열)
            item_type: 항목 타입 ("tool" 또는 "category")

        Returns:
            추가 성공 여부 (이미 존재하면 False)
        """
        # 중복 체크
        for item in self._items:
            if item_type == "category":
                # 카테고리 중복: 같은 카테고리면 중복
                if item.item_type == "category" and item.category == category:
                    return False
            else:
                # 도구 중복: 같은 카테고리 + 모듈이면 중복
                if item.item_type == "tool" and item.category == category and item.tool_module == tool_module:
                    return False

        # 최대 개수 체크
        if len(self._items) >= self.MAX_ITEMS:
            return False

        # 새 항목 추가
        now = datetime.now().isoformat()
        max_order = max((item.order for item in self._items), default=-1)
        ref = category if item_type == "category" else f"{category}/{tool_module}"

        self._items.append(
            FavoriteItem(
                category=category,
                tool_name=tool_name,
                tool_module=tool_module,
                added_at=now,
                order=max_order + 1,
                item_type=item_type,
                ref=ref,
            )
        )

        self._save()
        return True

    def add_category(self, category: str, display_name: str) -> bool:
        """카테고리(서비스) 즐겨찾기 추가

        Args:
            category: 카테고리 이름 (예: "ec2", "vpc")
            display_name: 표시 이름 (예: "EC2", "VPC")

        Returns:
            추가 성공 여부
        """
        return self.add(category, display_name, "", item_type="category")

    def is_category_favorite(self, category: str) -> bool:
        """카테고리 즐겨찾기 여부 확인"""
        return any(item.item_type == "category" and item.category == category for item in self._items)

    def remove_category(self, category: str) -> bool:
        """카테고리 즐겨찾기 삭제"""
        for i, item in enumerate(self._items):
            if item.item_type == "category" and item.category == category:
                self._items.pop(i)
                self._save()
                return True
        return False

    def remove(self, category: str, tool_module: str) -> bool:
        """도구 즐겨찾기 삭제

        Returns:
            삭제 성공 여부
        """
        for i, item in enumerate(self._items):
            if item.item_type == "tool" and item.category == category and item.tool_module == tool_module:
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
        """도구 즐겨찾기 여부 확인"""
        return any(
            item.item_type == "tool" and item.category == category and item.tool_module == tool_module
            for item in self._items
        )

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

            items: list[FavoriteItem] = []
            for raw in data:
                if not isinstance(raw, dict):
                    continue
                try:
                    filtered = {k: v for k, v in raw.items() if k in _FAVORITE_FIELDS}
                    items.append(FavoriteItem(**filtered))
                except (TypeError, KeyError):
                    logger.debug("즐겨찾기 항목 로드 스킵: %s", raw)
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
            fd, tmp_path = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp", prefix=".favorites_")
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
        """파일에서 다시 로드"""
        self._load()

    def get_by_index(self, index: int) -> FavoriteItem | None:
        """인덱스로 즐겨찾기 항목 조회 (1-based)

        Args:
            index: 1부터 시작하는 인덱스 번호

        Returns:
            해당 인덱스의 FavoriteItem 또는 None (범위 초과 시)
        """
        items = self.get_all()
        if 1 <= index <= len(items):
            return items[index - 1]
        return None

    def remove_by_index(self, index: int) -> bool:
        """인덱스로 즐겨찾기 삭제 (1-based)

        Args:
            index: 1부터 시작하는 인덱스 번호

        Returns:
            삭제 성공 여부
        """
        item = self.get_by_index(index)
        if not item:
            return False

        if item.item_type == "category":
            return self.remove_category(item.category)
        return self.remove(item.category, item.tool_module)
