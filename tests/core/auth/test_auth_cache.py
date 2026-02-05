# tests/test_auth_cache.py
"""
core/auth/cache/cache.py 단위 테스트

CacheEntry, TokenCache, TokenCacheManager, AccountCache, CredentialsCache 테스트.
"""

import threading
from datetime import datetime, timedelta, timezone

from core.auth.cache.cache import (
    AccountCache,
    CacheEntry,
    CredentialsCache,
    TokenCache,
    TokenCacheManager,
)
from core.auth.types import AccountInfo

# =============================================================================
# CacheEntry 테스트
# =============================================================================


class TestCacheEntry:
    """CacheEntry 테스트"""

    def test_init_with_defaults(self):
        """기본 초기화"""
        entry = CacheEntry(value="test_value")

        assert entry.value == "test_value"
        assert entry.created_at is not None
        assert entry.expires_at is None

    def test_is_expired_with_no_expiry(self):
        """만료 시간 없으면 만료되지 않음"""
        entry = CacheEntry(value="test")
        assert entry.is_expired() is False

    def test_is_expired_with_future_expiry(self):
        """미래 만료 시간이면 만료되지 않음"""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        entry = CacheEntry(value="test", expires_at=future)
        assert entry.is_expired() is False

    def test_is_expired_with_past_expiry(self):
        """과거 만료 시간이면 만료됨"""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        entry = CacheEntry(value="test", expires_at=past)
        assert entry.is_expired() is True

    def test_is_expired_with_buffer(self):
        """버퍼 시간 내이면 만료로 간주"""
        # 30초 후 만료, 버퍼 60초 -> 만료로 간주
        near_future = datetime.now(timezone.utc) + timedelta(seconds=30)
        entry = CacheEntry(value="test", expires_at=near_future)
        assert entry.is_expired(buffer_seconds=60) is True
        assert entry.is_expired(buffer_seconds=10) is False

    def test_remaining_seconds_no_expiry(self):
        """만료 없으면 None 반환"""
        entry = CacheEntry(value="test")
        assert entry.remaining_seconds() is None

    def test_remaining_seconds_with_expiry(self):
        """남은 시간 계산"""
        future = datetime.now(timezone.utc) + timedelta(seconds=100)
        entry = CacheEntry(value="test", expires_at=future)
        remaining = entry.remaining_seconds()
        assert remaining is not None
        assert 95 <= remaining <= 100

    def test_remaining_seconds_expired(self):
        """만료됐으면 0 반환"""
        past = datetime.now(timezone.utc) - timedelta(seconds=100)
        entry = CacheEntry(value="test", expires_at=past)
        assert entry.remaining_seconds() == 0


# =============================================================================
# TokenCache 테스트
# =============================================================================


class TestTokenCache:
    """TokenCache 테스트"""

    def test_init(self):
        """기본 초기화"""
        token = TokenCache(
            access_token="test-token",
            expires_at="2025-12-31T23:59:59Z",
            client_id="client-123",
            client_secret="secret-456",
        )

        assert token.access_token == "test-token"
        assert token.expires_at == "2025-12-31T23:59:59Z"
        assert token.client_id == "client-123"
        assert token.refresh_token is None

    def test_is_expired_future(self):
        """미래 시간이면 만료되지 않음"""
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        token = TokenCache(access_token="test", expires_at=future)
        assert token.is_expired() is False

    def test_is_expired_past(self):
        """과거 시간이면 만료됨"""
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        token = TokenCache(access_token="test", expires_at=past)
        assert token.is_expired() is True

    def test_is_expired_invalid_format(self):
        """잘못된 형식이면 만료로 간주"""
        token = TokenCache(access_token="test", expires_at="invalid-date")
        assert token.is_expired() is True

    def test_get_expires_at_datetime(self):
        """만료 시간 datetime 변환"""
        token = TokenCache(access_token="test", expires_at="2025-06-15T10:30:00Z")
        dt = token.get_expires_at_datetime()
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 6
        assert dt.day == 15

    def test_get_expires_at_datetime_invalid(self):
        """잘못된 형식이면 None"""
        token = TokenCache(access_token="test", expires_at="invalid")
        assert token.get_expires_at_datetime() is None

    def test_to_dict(self):
        """딕셔너리 변환"""
        token = TokenCache(
            access_token="test-token",
            expires_at="2025-01-01T00:00:00Z",
            client_id="client-123",
            client_secret="secret-456",
            refresh_token="refresh-789",
            region="us-east-1",
            start_url="https://example.awsapps.com/start",
        )

        # 암호화 없이 딕셔너리 변환 (테스트용)
        data = token.to_dict(encrypt=False)

        assert data["accessToken"] == "test-token"
        assert data["expiresAt"] == "2025-01-01T00:00:00Z"
        assert data["clientId"] == "client-123"
        assert data["refreshToken"] == "refresh-789"
        assert data["region"] == "us-east-1"
        assert data["startUrl"] == "https://example.awsapps.com/start"
        assert data["_encrypted"] is False

    def test_to_dict_without_optional(self):
        """선택 필드 없이 딕셔너리 변환"""
        token = TokenCache(
            access_token="test-token",
            expires_at="2025-01-01T00:00:00Z",
        )

        data = token.to_dict(encrypt=False)

        assert "refreshToken" not in data
        assert "region" not in data
        assert "startUrl" not in data

    def test_from_dict(self):
        """딕셔너리에서 생성"""
        data = {
            "accessToken": "test-token",
            "expiresAt": "2025-01-01T00:00:00Z",
            "clientId": "client-123",
            "clientSecret": "secret-456",
            "refreshToken": "refresh-789",
            "region": "us-east-1",
            "startUrl": "https://example.awsapps.com/start",
        }

        token = TokenCache.from_dict(data)

        assert token.access_token == "test-token"
        assert token.expires_at == "2025-01-01T00:00:00Z"
        assert token.refresh_token == "refresh-789"
        assert token.region == "us-east-1"

    def test_from_dict_missing_fields(self):
        """필드 누락 시 기본값"""
        data = {}
        token = TokenCache.from_dict(data)

        assert token.access_token == ""
        assert token.expires_at == ""
        assert token.refresh_token is None

    def test_encryption_roundtrip(self):
        """암호화/복호화 라운드트립 테스트"""
        token = TokenCache(
            access_token="secret-access-token",
            expires_at="2025-01-01T00:00:00Z",
            client_id="client-123",
            client_secret="super-secret",
            refresh_token="refresh-token-xyz",
            region="us-east-1",
            start_url="https://example.awsapps.com/start",
        )

        # 암호화하여 딕셔너리로 변환
        encrypted_data = token.to_dict(encrypt=True)

        # 암호화된 상태에서 복원
        restored_token = TokenCache.from_dict(encrypted_data)

        # 원본과 동일해야 함
        assert restored_token.access_token == "secret-access-token"
        assert restored_token.client_secret == "super-secret"
        assert restored_token.refresh_token == "refresh-token-xyz"
        assert restored_token.expires_at == "2025-01-01T00:00:00Z"
        assert restored_token.region == "us-east-1"


# =============================================================================
# TokenCacheManager 테스트
# =============================================================================


class TestTokenCacheManager:
    """TokenCacheManager 테스트"""

    def test_init(self):
        """초기화"""
        manager = TokenCacheManager(
            session_name="my-session",
            start_url="https://example.awsapps.com/start",
        )

        assert manager.session_name == "my-session"
        assert manager.start_url == "https://example.awsapps.com/start"

    def test_init_custom_cache_dir(self, tmp_path):
        """커스텀 캐시 디렉토리"""
        manager = TokenCacheManager(
            session_name="test",
            start_url="https://example.com",
            cache_dir=str(tmp_path),
        )
        assert manager.cache_dir == tmp_path

    def test_cache_key_generation(self):
        """캐시 키(해시) 생성"""
        manager = TokenCacheManager(
            session_name="my-session",
            start_url="https://example.com",
        )
        # session_name이 있으면 session_name 기반 해시
        assert len(manager._cache_key) == 40  # SHA1 해시 길이

    def test_cache_key_uses_start_url_when_no_session(self):
        """session_name 없으면 start_url 사용"""
        manager1 = TokenCacheManager(
            session_name="",
            start_url="https://example.com",
        )
        manager2 = TokenCacheManager(
            session_name="",
            start_url="https://example.com",
        )
        assert manager1._cache_key == manager2._cache_key

    def test_cache_path(self, tmp_path):
        """캐시 파일 경로"""
        manager = TokenCacheManager(
            session_name="test",
            start_url="https://example.com",
            cache_dir=str(tmp_path),
        )
        path = manager.cache_path
        assert path.parent == tmp_path
        assert path.suffix == ".json"

    def test_save_and_load(self, tmp_path):
        """저장 및 로드"""
        manager = TokenCacheManager(
            session_name="test",
            start_url="https://example.com",
            cache_dir=str(tmp_path),
        )

        token = TokenCache(
            access_token="my-access-token",
            expires_at="2025-12-31T23:59:59Z",
            client_id="client-123",
            client_secret="secret-456",
        )

        manager.save(token)
        loaded = manager.load()

        assert loaded is not None
        assert loaded.access_token == "my-access-token"
        assert loaded.client_id == "client-123"

    def test_load_nonexistent(self, tmp_path):
        """존재하지 않는 파일 로드"""
        manager = TokenCacheManager(
            session_name="nonexistent",
            start_url="https://example.com",
            cache_dir=str(tmp_path),
        )
        assert manager.load() is None

    def test_load_invalid_json(self, tmp_path):
        """잘못된 JSON 파일"""
        manager = TokenCacheManager(
            session_name="test",
            start_url="https://example.com",
            cache_dir=str(tmp_path),
        )

        # 잘못된 JSON 작성
        manager.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(manager.cache_path, "w") as f:
            f.write("not valid json")

        assert manager.load() is None

    def test_delete(self, tmp_path):
        """캐시 삭제"""
        manager = TokenCacheManager(
            session_name="test",
            start_url="https://example.com",
            cache_dir=str(tmp_path),
        )

        token = TokenCache(access_token="test", expires_at="2025-01-01T00:00:00Z")
        manager.save(token)
        assert manager.exists() is True

        result = manager.delete()
        assert result is True
        assert manager.exists() is False

    def test_delete_nonexistent(self, tmp_path):
        """존재하지 않는 파일 삭제"""
        manager = TokenCacheManager(
            session_name="nonexistent",
            start_url="https://example.com",
            cache_dir=str(tmp_path),
        )
        assert manager.delete() is True  # 에러 없이 성공


# =============================================================================
# AccountCache 테스트
# =============================================================================


class TestAccountCache:
    """AccountCache 테스트"""

    def test_init(self):
        """초기화"""
        cache = AccountCache(default_ttl_seconds=1800)
        assert len(cache) == 0

    def test_set_and_get(self):
        """저장 및 조회"""
        cache = AccountCache()
        account = AccountInfo(id="111111111111", name="Test Account")

        cache.set("111111111111", account)
        result = cache.get("111111111111")

        assert result is not None
        assert result.id == "111111111111"
        assert result.name == "Test Account"

    def test_get_nonexistent(self):
        """존재하지 않는 항목 조회"""
        cache = AccountCache()
        assert cache.get("nonexistent") is None

    def test_get_expired(self):
        """만료된 항목 조회"""
        cache = AccountCache()
        account = AccountInfo(id="111111111111", name="Test")

        # 과거 만료 시간을 직접 설정
        cache.set("111111111111", account, ttl_seconds=3600)
        # 캐시 엔트리의 만료 시간을 과거로 강제 변경
        entry = cache._cache["111111111111"]
        entry.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        assert cache.get("111111111111") is None

    def test_get_all(self):
        """모든 항목 조회"""
        cache = AccountCache()
        cache.set("111111111111", AccountInfo(id="111111111111", name="Account 1"))
        cache.set("222222222222", AccountInfo(id="222222222222", name="Account 2"))

        all_accounts = cache.get_all()
        assert len(all_accounts) == 2
        assert "111111111111" in all_accounts
        assert "222222222222" in all_accounts

    def test_get_all_excludes_expired(self):
        """만료된 항목 제외"""
        cache = AccountCache()
        cache.set(
            "111111111111",
            AccountInfo(id="111111111111", name="Valid"),
            ttl_seconds=3600,
        )
        cache.set(
            "222222222222",
            AccountInfo(id="222222222222", name="Expired"),
            ttl_seconds=3600,
        )

        # 만료 시간을 과거로 강제 변경
        cache._cache["222222222222"].expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        all_accounts = cache.get_all()
        assert len(all_accounts) == 1
        assert "111111111111" in all_accounts
        assert "222222222222" not in all_accounts

    def test_set_all(self):
        """일괄 저장"""
        cache = AccountCache()
        accounts = {
            "111111111111": AccountInfo(id="111111111111", name="Account 1"),
            "222222222222": AccountInfo(id="222222222222", name="Account 2"),
        }

        cache.set_all(accounts)
        assert len(cache) == 2

    def test_invalidate(self):
        """특정 항목 무효화"""
        cache = AccountCache()
        cache.set("111111111111", AccountInfo(id="111111111111", name="Test"))

        result = cache.invalidate("111111111111")
        assert result is True
        assert cache.get("111111111111") is None

    def test_invalidate_nonexistent(self):
        """존재하지 않는 항목 무효화"""
        cache = AccountCache()
        assert cache.invalidate("nonexistent") is False

    def test_clear(self):
        """모든 캐시 클리어"""
        cache = AccountCache()
        cache.set("111111111111", AccountInfo(id="111111111111", name="Test"))
        cache.set("222222222222", AccountInfo(id="222222222222", name="Test2"))

        cache.clear()
        assert len(cache) == 0

    def test_thread_safety(self):
        """스레드 안전성"""
        cache = AccountCache()
        errors = []

        def worker(account_id):
            try:
                for _ in range(100):
                    cache.set(account_id, AccountInfo(id=account_id, name="Test"))
                    cache.get(account_id)
                    cache.get_all()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"{i}11111111111",)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# =============================================================================
# CredentialsCache 테스트
# =============================================================================


class TestCredentialsCache:
    """CredentialsCache 테스트"""

    def test_init(self):
        """초기화"""
        cache = CredentialsCache(default_ttl_seconds=900)
        assert len(cache) == 0

    def test_set_and_get(self):
        """저장 및 조회"""
        cache = CredentialsCache()
        credentials = {
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "secret_access_key": "wJalrXUtnFEMI",
            "session_token": "FwoGZXIvYXdzEBY...",
        }

        cache.set("111111111111", "AdminRole", credentials)
        result = cache.get("111111111111", "AdminRole")

        assert result is not None
        assert result["access_key_id"] == "AKIAIOSFODNN7EXAMPLE"

    def test_get_nonexistent(self):
        """존재하지 않는 항목 조회"""
        cache = CredentialsCache()
        assert cache.get("111111111111", "NonexistentRole") is None

    def test_get_expired(self):
        """만료된 항목 조회"""
        cache = CredentialsCache()
        credentials = {"access_key_id": "AKIAIOSFODNN7EXAMPLE"}

        # 과거 만료 시간 설정
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        cache.set("111111111111", "AdminRole", credentials, expires_at=past)

        assert cache.get("111111111111", "AdminRole") is None

    def test_different_roles_different_cache(self):
        """다른 역할은 다른 캐시"""
        cache = CredentialsCache()
        creds1 = {"access_key_id": "KEY1"}
        creds2 = {"access_key_id": "KEY2"}

        cache.set("111111111111", "Role1", creds1)
        cache.set("111111111111", "Role2", creds2)

        assert cache.get("111111111111", "Role1")["access_key_id"] == "KEY1"
        assert cache.get("111111111111", "Role2")["access_key_id"] == "KEY2"

    def test_invalidate(self):
        """특정 자격증명 무효화"""
        cache = CredentialsCache()
        cache.set("111111111111", "AdminRole", {"key": "value"})

        result = cache.invalidate("111111111111", "AdminRole")
        assert result is True
        assert cache.get("111111111111", "AdminRole") is None

    def test_invalidate_account(self):
        """계정의 모든 자격증명 무효화"""
        cache = CredentialsCache()
        cache.set("111111111111", "Role1", {"key": "value1"})
        cache.set("111111111111", "Role2", {"key": "value2"})
        cache.set("222222222222", "Role1", {"key": "value3"})

        count = cache.invalidate_account("111111111111")
        assert count == 2
        assert cache.get("111111111111", "Role1") is None
        assert cache.get("111111111111", "Role2") is None
        assert cache.get("222222222222", "Role1") is not None

    def test_clear(self):
        """모든 캐시 클리어"""
        cache = CredentialsCache()
        cache.set("111111111111", "Role1", {"key": "value"})
        cache.set("222222222222", "Role2", {"key": "value"})

        cache.clear()
        assert len(cache) == 0

    def test_len_excludes_expired(self):
        """len은 만료된 항목 제외"""
        cache = CredentialsCache()

        # 유효한 항목
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        cache.set("111111111111", "Role1", {"key": "value"}, expires_at=future)

        # 만료된 항목
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        cache.set("222222222222", "Role2", {"key": "value"}, expires_at=past)

        assert len(cache) == 1

    def test_thread_safety(self):
        """스레드 안전성"""
        cache = CredentialsCache()
        errors = []

        def worker(account_id):
            try:
                for i in range(100):
                    cache.set(account_id, f"Role{i}", {"key": "value"})
                    cache.get(account_id, f"Role{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"{i}11111111111",)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
