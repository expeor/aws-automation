"""
tests/test_history.py - 사용 이력 테스트
"""

from unittest.mock import patch

import pytest


class TestRecentHistory:
    """RecentHistory 테스트"""

    @pytest.fixture
    def temp_history_path(self, tmp_path):
        """임시 이력 파일 경로"""
        return tmp_path / "history" / "recent.json"

    @pytest.fixture
    def history(self, temp_history_path):
        """테스트용 RecentHistory 인스턴스"""
        from core.tools.history.recent import RecentHistory

        # 싱글톤 초기화
        RecentHistory._instance = None

        with patch(
            "core.tools.history.recent.RecentHistory._get_history_path",
            return_value=temp_history_path,
        ):
            return RecentHistory()

    def test_add_and_get_recent(self, history):
        """이력 추가 및 조회"""
        history.add("ebs", "미사용 볼륨", "unused")
        history.add("ec2", "인스턴스 목록", "instances")

        recent = history.get_recent(5)
        assert len(recent) == 2
        # 최근 것이 먼저
        assert recent[0].category == "ec2"
        assert recent[1].category == "ebs"

    def test_duplicate_add_updates(self, history):
        """중복 추가 시 업데이트"""
        history.add("ebs", "미사용 볼륨", "unused")
        history.add("ec2", "인스턴스 목록", "instances")
        history.add("ebs", "미사용 볼륨", "unused")  # 중복

        recent = history.get_recent(5)
        assert len(recent) == 2
        # ebs가 맨 앞으로
        assert recent[0].category == "ebs"
        assert recent[0].use_count == 2

    def test_max_items_limit(self, history):
        """최대 항목 수 제한"""
        # MAX_ITEMS보다 많이 추가
        for i in range(60):
            history.add(f"cat{i}", f"Tool {i}", f"tool{i}")

        assert len(history.get_all()) == history.MAX_ITEMS

    def test_get_frequent(self, history):
        """자주 사용 목록"""
        history.add("ebs", "미사용 볼륨", "unused")
        history.add("ec2", "인스턴스 목록", "instances")
        # ebs 한 번 더 추가
        history.add("ebs", "미사용 볼륨", "unused")
        history.add("ebs", "미사용 볼륨", "unused")

        frequent = history.get_frequent(5)
        assert frequent[0].category == "ebs"
        assert frequent[0].use_count == 3

    def test_remove(self, history):
        """항목 삭제"""
        history.add("ebs", "미사용 볼륨", "unused")
        history.add("ec2", "인스턴스 목록", "instances")

        result = history.remove("ebs", "unused")
        assert result is True
        assert len(history.get_all()) == 1

    def test_clear(self, history):
        """전체 초기화"""
        history.add("ebs", "미사용 볼륨", "unused")
        history.add("ec2", "인스턴스 목록", "instances")

        history.clear()
        assert len(history.get_all()) == 0


class TestFavoritesManager:
    """FavoritesManager 테스트"""

    @pytest.fixture
    def temp_favorites_path(self, tmp_path):
        """임시 즐겨찾기 파일 경로"""
        return tmp_path / "history" / "favorites.json"

    @pytest.fixture
    def favorites(self, temp_favorites_path):
        """테스트용 FavoritesManager 인스턴스"""
        from core.tools.history.favorites import FavoritesManager

        # 싱글톤 초기화
        FavoritesManager._instance = None

        with patch(
            "core.tools.history.favorites.FavoritesManager._get_favorites_path",
            return_value=temp_favorites_path,
        ):
            return FavoritesManager()

    def test_add_and_get_all(self, favorites):
        """즐겨찾기 추가 및 조회"""
        favorites.add("ebs", "미사용 볼륨", "unused")
        favorites.add("ec2", "인스턴스 목록", "instances")

        all_favs = favorites.get_all()
        assert len(all_favs) == 2

    def test_duplicate_add_returns_false(self, favorites):
        """중복 추가 시 False 반환"""
        result1 = favorites.add("ebs", "미사용 볼륨", "unused")
        result2 = favorites.add("ebs", "미사용 볼륨", "unused")

        assert result1 is True
        assert result2 is False
        assert len(favorites.get_all()) == 1

    def test_toggle(self, favorites):
        """토글 기능"""
        # 추가
        result1 = favorites.toggle("ebs", "미사용 볼륨", "unused")
        assert result1 is True
        assert favorites.is_favorite("ebs", "unused")

        # 삭제
        result2 = favorites.toggle("ebs", "미사용 볼륨", "unused")
        assert result2 is False
        assert not favorites.is_favorite("ebs", "unused")

    def test_is_favorite(self, favorites):
        """즐겨찾기 여부 확인"""
        favorites.add("ebs", "미사용 볼륨", "unused")

        assert favorites.is_favorite("ebs", "unused") is True
        assert favorites.is_favorite("ec2", "instances") is False

    def test_remove(self, favorites):
        """삭제"""
        favorites.add("ebs", "미사용 볼륨", "unused")

        result = favorites.remove("ebs", "unused")
        assert result is True
        assert len(favorites.get_all()) == 0

    def test_clear(self, favorites):
        """전체 초기화"""
        favorites.add("ebs", "미사용 볼륨", "unused")
        favorites.add("ec2", "인스턴스 목록", "instances")

        favorites.clear()
        assert len(favorites.get_all()) == 0
