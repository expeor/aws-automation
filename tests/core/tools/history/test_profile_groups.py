"""
tests/core/tools/history/test_profile_groups.py - 프로필 그룹 테스트
"""

import json
from unittest.mock import patch

import pytest


class TestProfileGroup:
    """ProfileGroup 클래스 테스트"""

    def test_basic_group(self):
        """기본 그룹 생성"""
        from core.tools.history.profile_groups import ProfileGroup

        group = ProfileGroup(
            name="production",
            kind="sso_profile",
            profiles=["prod-1", "prod-2"],
        )

        assert group.name == "production"
        assert group.kind == "sso_profile"
        assert len(group.profiles) == 2

    def test_default_values(self):
        """기본값 확인"""
        from core.tools.history.profile_groups import ProfileGroup

        group = ProfileGroup(name="test", kind="static")

        assert group.profiles == []
        assert group.added_at != ""  # 자동 생성됨
        assert group.order == 0

    def test_auto_added_at(self):
        """added_at 자동 설정"""
        from core.tools.history.profile_groups import ProfileGroup

        group = ProfileGroup(name="test", kind="sso_profile")

        assert group.added_at != ""
        # ISO format 확인
        assert "T" in group.added_at


class TestProfileGroupsManager:
    """ProfileGroupsManager 클래스 테스트"""

    @pytest.fixture
    def reset_singleton(self):
        """싱글톤 리셋"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        ProfileGroupsManager._instance = None
        yield
        ProfileGroupsManager._instance = None

    def test_singleton_pattern(self, reset_singleton, tmp_path):
        """싱글톤 패턴 확인"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager1 = ProfileGroupsManager()
            manager2 = ProfileGroupsManager()

            assert manager1 is manager2

    def test_add_group(self, reset_singleton, tmp_path):
        """그룹 추가"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            result = manager.add("production", "sso_profile", ["prod-1", "prod-2"])

            assert result is True
            assert manager.get_by_name("production") is not None

    def test_add_duplicate_group(self, reset_singleton, tmp_path):
        """중복 그룹 추가 실패"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            manager.add("test", "sso_profile", ["p1"])
            result = manager.add("test", "sso_profile", ["p2"])

            assert result is False

    def test_add_empty_profiles(self, reset_singleton, tmp_path):
        """빈 프로필 목록으로 추가 실패"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            result = manager.add("test", "sso_profile", [])

            assert result is False

    def test_add_max_groups(self, reset_singleton, tmp_path):
        """최대 그룹 수 초과"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()

            # MAX_GROUPS만큼 추가
            for i in range(ProfileGroupsManager.MAX_GROUPS):
                manager.add(f"group_{i}", "sso_profile", [f"p{i}"])

            # 초과 추가 시도
            result = manager.add("extra", "sso_profile", ["p"])
            assert result is False

    def test_add_truncates_profiles(self, reset_singleton, tmp_path):
        """프로필 개수 제한"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            many_profiles = [f"p{i}" for i in range(50)]
            result = manager.add("test", "sso_profile", many_profiles)

            assert result is True
            group = manager.get_by_name("test")
            assert len(group.profiles) == ProfileGroupsManager.MAX_PROFILES_PER_GROUP

    def test_update_group_name(self, reset_singleton, tmp_path):
        """그룹 이름 변경"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            manager.add("old_name", "sso_profile", ["p1"])

            result = manager.update("old_name", new_name="new_name")

            assert result is True
            assert manager.get_by_name("old_name") is None
            assert manager.get_by_name("new_name") is not None

    def test_update_group_profiles(self, reset_singleton, tmp_path):
        """그룹 프로필 변경"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            manager.add("test", "sso_profile", ["p1"])

            result = manager.update("test", profiles=["p2", "p3"])

            assert result is True
            group = manager.get_by_name("test")
            assert group.profiles == ["p2", "p3"]

    def test_update_nonexistent_group(self, reset_singleton, tmp_path):
        """존재하지 않는 그룹 업데이트"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            result = manager.update("nonexistent", new_name="new")

            assert result is False

    def test_update_duplicate_name(self, reset_singleton, tmp_path):
        """중복 이름으로 변경 실패"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            manager.add("group1", "sso_profile", ["p1"])
            manager.add("group2", "sso_profile", ["p2"])

            result = manager.update("group1", new_name="group2")

            assert result is False

    def test_remove_group(self, reset_singleton, tmp_path):
        """그룹 삭제"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            manager.add("test", "sso_profile", ["p1"])

            result = manager.remove("test")

            assert result is True
            assert manager.get_by_name("test") is None

    def test_remove_nonexistent_group(self, reset_singleton, tmp_path):
        """존재하지 않는 그룹 삭제"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            result = manager.remove("nonexistent")

            assert result is False

    def test_get_by_name_found(self, reset_singleton, tmp_path):
        """이름으로 그룹 찾기 - 존재"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            manager.add("test", "sso_profile", ["p1"])

            group = manager.get_by_name("test")

            assert group is not None
            assert group.name == "test"

    def test_get_by_name_not_found(self, reset_singleton, tmp_path):
        """이름으로 그룹 찾기 - 없음"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            group = manager.get_by_name("nonexistent")

            assert group is None

    def test_get_all(self, reset_singleton, tmp_path):
        """전체 그룹 목록"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            manager.add("group1", "sso_profile", ["p1"])
            manager.add("group2", "static", ["p2"])

            groups = manager.get_all()

            assert len(groups) == 2

    def test_get_by_kind(self, reset_singleton, tmp_path):
        """타입별 그룹 필터링"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            manager.add("sso_group", "sso_profile", ["p1"])
            manager.add("static_group", "static", ["p2"])

            sso_groups = manager.get_by_kind("sso_profile")
            static_groups = manager.get_by_kind("static")

            assert len(sso_groups) == 1
            assert sso_groups[0].name == "sso_group"
            assert len(static_groups) == 1
            assert static_groups[0].name == "static_group"

    def test_move_up(self, reset_singleton, tmp_path):
        """그룹 순서 올리기"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            manager.add("group1", "sso_profile", ["p1"])
            manager.add("group2", "sso_profile", ["p2"])

            result = manager.move_up("group2")

            assert result is True
            groups = manager.get_all()
            assert groups[0].name == "group2"

    def test_move_up_first_item(self, reset_singleton, tmp_path):
        """첫 번째 아이템은 올리기 불가"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            manager.add("group1", "sso_profile", ["p1"])

            result = manager.move_up("group1")

            assert result is False

    def test_move_down(self, reset_singleton, tmp_path):
        """그룹 순서 내리기"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            manager.add("group1", "sso_profile", ["p1"])
            manager.add("group2", "sso_profile", ["p2"])

            result = manager.move_down("group1")

            assert result is True
            groups = manager.get_all()
            assert groups[1].name == "group1"

    def test_move_down_last_item(self, reset_singleton, tmp_path):
        """마지막 아이템은 내리기 불가"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            manager.add("group1", "sso_profile", ["p1"])

            result = manager.move_down("group1")

            assert result is False

    def test_clear(self, reset_singleton, tmp_path):
        """전체 초기화"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        with patch("core.tools.cache.get_cache_path", return_value=tmp_path / "groups.json"):
            manager = ProfileGroupsManager()
            manager.add("group1", "sso_profile", ["p1"])
            manager.add("group2", "sso_profile", ["p2"])

            manager.clear()

            assert len(manager.get_all()) == 0

    def test_persistence(self, reset_singleton, tmp_path):
        """저장 및 로드 테스트"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        file_path = tmp_path / "groups.json"

        with patch("core.tools.cache.get_cache_path", return_value=file_path):
            manager = ProfileGroupsManager()
            manager.add("persistent_group", "sso_profile", ["p1", "p2"])

            # 저장 확인
            assert file_path.exists()

            # 새 매니저로 로드 (싱글톤 리셋)
            ProfileGroupsManager._instance = None
            manager2 = ProfileGroupsManager()

            group = manager2.get_by_name("persistent_group")
            assert group is not None
            assert group.profiles == ["p1", "p2"]

    def test_reload(self, reset_singleton, tmp_path):
        """다시 로드"""
        from core.tools.history.profile_groups import ProfileGroupsManager

        file_path = tmp_path / "groups.json"

        with patch("core.tools.cache.get_cache_path", return_value=file_path):
            manager = ProfileGroupsManager()
            manager.add("test", "sso_profile", ["p1"])

            # 파일 직접 수정
            data = [{"name": "modified", "kind": "static", "profiles": ["new"], "added_at": "", "order": 0}]
            file_path.write_text(json.dumps(data), encoding="utf-8")

            manager.reload()

            assert manager.get_by_name("test") is None
            assert manager.get_by_name("modified") is not None
