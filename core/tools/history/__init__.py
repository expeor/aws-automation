"""사용 이력 관리.

최근 사용 도구 이력(LRU 기반), 즐겨찾기, 프로파일 그룹을 관리합니다.
모든 매니저 클래스는 싱글톤 패턴으로 구현되어 있으며,
JSON 파일 기반 영속성을 제공합니다.

Modules:
    recent: 최근 사용 도구 이력 관리 (RecentHistory, RecentItem).
    favorites: 즐겨찾기 관리 (FavoritesManager, FavoriteItem).
    profile_groups: 프로파일 그룹 관리 (ProfileGroupsManager, ProfileGroup).
"""

from .favorites import FavoriteItem, FavoritesManager
from .profile_groups import ProfileGroup, ProfileGroupsManager
from .recent import RecentHistory, RecentItem

__all__: list[str] = [
    "RecentHistory",
    "RecentItem",
    "FavoritesManager",
    "FavoriteItem",
    "ProfileGroupsManager",
    "ProfileGroup",
]
