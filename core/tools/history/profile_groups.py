"""
core/tools/history/profile_groups.py - 프로파일 그룹 관리

자주 사용하는 프로파일 조합을 그룹으로 저장하여 빠르게 선택
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class ProfileGroup:
    """프로파일 그룹 항목"""

    name: str  # 그룹 이름 (예: "개발 환경")
    kind: str  # "sso_profile" 또는 "static" (ProviderKind.value)
    profiles: List[str] = field(default_factory=list)  # 프로파일 이름 목록
    added_at: str = ""  # ISO format
    order: int = 0  # 정렬 순서 (낮을수록 상위)

    def __post_init__(self):
        if not self.added_at:
            self.added_at = datetime.now().isoformat()


class ProfileGroupsManager:
    """프로파일 그룹 관리

    사용자가 자주 쓰는 프로파일 조합을 그룹으로 저장하고 관리합니다.
    같은 타입(SSO 프로파일 또는 Access Key)끼리만 그룹화 가능합니다.
    """

    MAX_GROUPS = 20
    MAX_PROFILES_PER_GROUP = 20
    _instance: Optional["ProfileGroupsManager"] = None

    def __new__(cls) -> "ProfileGroupsManager":
        """싱글톤 패턴"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._path = self._get_path()
        self._groups: List[ProfileGroup] = []
        self._load()
        self._initialized = True

    def _get_path(self) -> Path:
        """그룹 파일 경로"""
        from core.tools.cache import get_cache_path

        return Path(get_cache_path("history", "profile_groups.json"))

    def add(
        self,
        name: str,
        kind: str,
        profiles: List[str],
    ) -> bool:
        """그룹 추가

        Args:
            name: 그룹 이름
            kind: 인증 타입 ("sso_profile" 또는 "static")
            profiles: 프로파일 이름 목록

        Returns:
            추가 성공 여부 (이미 존재하면 False)
        """
        # 이름 중복 체크
        if self.get_by_name(name):
            return False

        # 최대 개수 체크
        if len(self._groups) >= self.MAX_GROUPS:
            return False

        # 프로파일 개수 체크
        if len(profiles) > self.MAX_PROFILES_PER_GROUP:
            profiles = profiles[: self.MAX_PROFILES_PER_GROUP]

        # 빈 프로파일 체크
        if not profiles:
            return False

        max_order = max((g.order for g in self._groups), default=-1)

        self._groups.append(
            ProfileGroup(
                name=name,
                kind=kind,
                profiles=profiles,
                order=max_order + 1,
            )
        )

        self._save()
        return True

    def update(
        self,
        name: str,
        new_name: Optional[str] = None,
        profiles: Optional[List[str]] = None,
    ) -> bool:
        """그룹 수정

        Args:
            name: 기존 그룹 이름
            new_name: 새 이름 (변경 시)
            profiles: 새 프로파일 목록 (변경 시)

        Returns:
            수정 성공 여부
        """
        group = self.get_by_name(name)
        if not group:
            return False

        # 새 이름 중복 체크
        if new_name and new_name != name:
            if self.get_by_name(new_name):
                return False
            group.name = new_name

        if profiles is not None:
            if len(profiles) > self.MAX_PROFILES_PER_GROUP:
                profiles = profiles[: self.MAX_PROFILES_PER_GROUP]
            group.profiles = profiles

        self._save()
        return True

    def remove(self, name: str) -> bool:
        """그룹 삭제

        Returns:
            삭제 성공 여부
        """
        for i, group in enumerate(self._groups):
            if group.name == name:
                self._groups.pop(i)
                self._save()
                return True
        return False

    def get_by_name(self, name: str) -> Optional[ProfileGroup]:
        """이름으로 그룹 찾기"""
        for group in self._groups:
            if group.name == name:
                return group
        return None

    def get_all(self) -> List[ProfileGroup]:
        """전체 그룹 목록 (순서대로)"""
        return sorted(self._groups, key=lambda x: x.order)

    def get_by_kind(self, kind: str) -> List[ProfileGroup]:
        """특정 타입의 그룹만 반환"""
        return [g for g in self.get_all() if g.kind == kind]

    def move_up(self, name: str) -> bool:
        """순서 올리기"""
        groups = self.get_all()
        for i, group in enumerate(groups):
            if group.name == name:
                if i == 0:
                    return False
                groups[i].order, groups[i - 1].order = (
                    groups[i - 1].order,
                    groups[i].order,
                )
                self._groups = groups
                self._save()
                return True
        return False

    def move_down(self, name: str) -> bool:
        """순서 내리기"""
        groups = self.get_all()
        for i, group in enumerate(groups):
            if group.name == name:
                if i == len(groups) - 1:
                    return False
                groups[i].order, groups[i + 1].order = (
                    groups[i + 1].order,
                    groups[i].order,
                )
                self._groups = groups
                self._save()
                return True
        return False

    def clear(self) -> None:
        """전체 초기화"""
        self._groups.clear()
        self._save()

    def _load(self) -> None:
        """파일에서 로드"""
        if not self._path.exists():
            self._groups = []
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._groups = [ProfileGroup(**item) for item in data]
        except (json.JSONDecodeError, TypeError, KeyError):
            self._groups = []

    def _save(self) -> None:
        """파일에 저장"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(group) for group in self._groups]
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def reload(self) -> None:
        """파일에서 다시 로드"""
        self._load()
