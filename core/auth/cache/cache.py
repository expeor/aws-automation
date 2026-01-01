# internal/auth/cache/cache.py
"""
AWS 인증 캐시 관리 구현

- TokenCache: SSO 토큰 데이터 구조
- TokenCacheManager: 토큰 캐시 파일 관리
- AccountCache: 메모리 기반 계정 캐시
- CredentialsCache: 메모리 기반 자격증명 캐시

설계 원칙:
- 파일 캐시는 SSO 토큰만 (AWS CLI 호환 필수)
- 나머지는 메모리 캐시로 단순화
- 토큰 만료 시간은 IAM Identity Center 설정을 따름
"""

import hashlib
import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Generic, Optional, TypeVar

from ..types import AccountInfo, TokenExpiredError

# =============================================================================
# Generic Cache Entry
# =============================================================================

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """캐시 항목을 나타내는 제네릭 데이터 클래스

    Attributes:
        value: 캐시된 값
        created_at: 생성 시간 (UTC)
        expires_at: 만료 시간 (UTC, None이면 만료되지 않음)
    """

    value: T
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """캐시 항목이 만료되었는지 확인

        Args:
            buffer_seconds: 만료 전 버퍼 시간 (초) - 기본 1분

        Returns:
            True if 만료됨, False otherwise
        """
        if self.expires_at is None:
            return False

        buffer = timedelta(seconds=buffer_seconds)
        return datetime.now(timezone.utc) >= (self.expires_at - buffer)

    def remaining_seconds(self) -> Optional[int]:
        """남은 시간을 초 단위로 반환

        Returns:
            남은 초 또는 None (만료되지 않는 경우)
        """
        if self.expires_at is None:
            return None

        remaining = self.expires_at - datetime.now(timezone.utc)
        return max(0, int(remaining.total_seconds()))


# =============================================================================
# Token Cache
# =============================================================================


@dataclass
class TokenCache:
    """SSO 토큰 캐시 데이터 구조

    AWS CLI와 호환되는 형식으로 저장됩니다.
    ~/.aws/sso/cache/{hash}.json

    Attributes:
        access_token: SSO 액세스 토큰
        expires_at: 만료 시간 (ISO 8601 형식)
        client_id: OIDC 클라이언트 ID
        client_secret: OIDC 클라이언트 시크릿
        refresh_token: 갱신 토큰 (옵션)
        region: SSO 리전
        start_url: SSO 시작 URL
    """

    access_token: str
    expires_at: str  # ISO 8601 format: "2024-01-01T00:00:00Z"
    client_id: str = ""
    client_secret: str = ""
    refresh_token: Optional[str] = None
    region: Optional[str] = None
    start_url: Optional[str] = None

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """토큰이 만료되었는지 확인

        Args:
            buffer_seconds: 만료 전 버퍼 시간 (초)

        Returns:
            True if 만료됨
        """
        try:
            # ISO 8601 형식 파싱
            expires_at = datetime.strptime(
                self.expires_at, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)

            buffer = timedelta(seconds=buffer_seconds)
            return datetime.now(timezone.utc) >= (expires_at - buffer)
        except Exception:
            return True

    def get_expires_at_datetime(self) -> Optional[datetime]:
        """만료 시간을 datetime 객체로 반환"""
        try:
            return datetime.strptime(self.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except Exception:
            return None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (JSON 저장용)"""
        data = {
            "accessToken": self.access_token,
            "expiresAt": self.expires_at,
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
        }
        if self.refresh_token:
            data["refreshToken"] = self.refresh_token
        if self.region:
            data["region"] = self.region
        if self.start_url:
            data["startUrl"] = self.start_url
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenCache":
        """딕셔너리에서 생성 (JSON 로드용)"""
        return cls(
            access_token=data.get("accessToken", ""),
            expires_at=data.get("expiresAt", ""),
            client_id=data.get("clientId", ""),
            client_secret=data.get("clientSecret", ""),
            refresh_token=data.get("refreshToken"),
            region=data.get("region"),
            start_url=data.get("startUrl"),
        )


class TokenCacheManager:
    """SSO 토큰 캐시 파일 관리자

    AWS CLI와 호환되는 방식으로 토큰을 저장/로드합니다.
    캐시 파일 위치: ~/.aws/sso/cache/{session_name_hash}.json
    """

    def __init__(
        self,
        session_name: str,
        start_url: str,
        cache_dir: Optional[str] = None,
    ):
        """TokenCacheManager 초기화

        Args:
            session_name: SSO 세션 이름
            start_url: SSO 시작 URL
            cache_dir: 캐시 디렉토리 (기본: ~/.aws/sso/cache)
        """
        self.session_name = session_name
        self.start_url = start_url

        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            home_dir = Path.home()
            self.cache_dir = home_dir / ".aws" / "sso" / "cache"

        self._cache_key = self._generate_cache_key()

    def _generate_cache_key(self) -> str:
        """캐시 파일명에 사용할 해시 키 생성

        AWS CLI와 동일한 방식으로 해시를 생성합니다.
        """
        # session_name이 있으면 session_name 사용, 없으면 start_url 사용
        input_str = self.session_name if self.session_name else self.start_url
        return hashlib.sha1(input_str.encode("utf-8")).hexdigest()

    @property
    def cache_path(self) -> Path:
        """캐시 파일 전체 경로"""
        return self.cache_dir / f"{self._cache_key}.json"

    def load(self) -> Optional[TokenCache]:
        """토큰 캐시를 파일에서 로드

        Returns:
            TokenCache 객체 또는 None (파일이 없거나 파싱 실패 시)
        """
        try:
            if not self.cache_path.exists():
                return None

            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return TokenCache.from_dict(data)
        except Exception:
            return None

    def save(self, token_cache: TokenCache) -> None:
        """토큰 캐시를 파일에 저장

        Args:
            token_cache: 저장할 TokenCache 객체

        Raises:
            IOError: 파일 저장 실패 시
        """
        # 캐시 디렉토리 생성
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(token_cache.to_dict(), f, indent=2)

    def delete(self) -> bool:
        """캐시 파일 삭제

        Returns:
            True if 삭제 성공
        """
        try:
            if self.cache_path.exists():
                self.cache_path.unlink()
            return True
        except Exception:
            return False

    def exists(self) -> bool:
        """캐시 파일 존재 여부"""
        return self.cache_path.exists()


# =============================================================================
# Memory-based Caches
# =============================================================================


class AccountCache:
    """메모리 기반 계정 캐시

    Thread-safe 구현.
    """

    def __init__(self, default_ttl_seconds: int = 3600):
        """AccountCache 초기화

        Args:
            default_ttl_seconds: 기본 TTL (초) - 기본 1시간
        """
        self._cache: Dict[str, CacheEntry[AccountInfo]] = {}
        self._lock = threading.RLock()
        self._default_ttl = timedelta(seconds=default_ttl_seconds)

    def get(self, account_id: str) -> Optional[AccountInfo]:
        """계정 정보 조회

        Args:
            account_id: AWS 계정 ID

        Returns:
            AccountInfo 또는 None
        """
        with self._lock:
            entry = self._cache.get(account_id)
            if entry is None:
                return None
            if entry.is_expired():
                del self._cache[account_id]
                return None
            return entry.value

    def get_all(self) -> Dict[str, AccountInfo]:
        """모든 유효한 계정 정보 조회

        Returns:
            {account_id: AccountInfo} 딕셔너리
        """
        with self._lock:
            result = {}
            expired_keys = []

            for account_id, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(account_id)
                else:
                    result[account_id] = entry.value

            # 만료된 항목 정리
            for key in expired_keys:
                del self._cache[key]

            return result

    def set(
        self,
        account_id: str,
        account_info: AccountInfo,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """계정 정보 저장

        Args:
            account_id: AWS 계정 ID
            account_info: AccountInfo 객체
            ttl_seconds: TTL (초) - None이면 기본값 사용
        """
        ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self._default_ttl
        expires_at = datetime.now(timezone.utc) + ttl

        with self._lock:
            self._cache[account_id] = CacheEntry(
                value=account_info,
                expires_at=expires_at,
            )

    def set_all(
        self,
        accounts: Dict[str, AccountInfo],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """여러 계정 정보 일괄 저장

        Args:
            accounts: {account_id: AccountInfo} 딕셔너리
            ttl_seconds: TTL (초)
        """
        for account_id, account_info in accounts.items():
            self.set(account_id, account_info, ttl_seconds)

    def invalidate(self, account_id: str) -> bool:
        """특정 계정 캐시 무효화

        Args:
            account_id: AWS 계정 ID

        Returns:
            True if 삭제됨
        """
        with self._lock:
            if account_id in self._cache:
                del self._cache[account_id]
                return True
            return False

    def clear(self) -> None:
        """모든 캐시 클리어"""
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        """유효한 캐시 항목 수"""
        return len(self.get_all())


class CredentialsCache:
    """메모리 기반 자격증명 캐시

    임시 자격증명(Role credentials)을 캐시하여 불필요한 STS 호출을 줄입니다.
    기본 TTL: 30분 (STS 임시 자격증명의 일반적인 유효 시간 고려)

    Thread-safe 구현.
    """

    # 캐시 키 생성에 사용할 구분자
    KEY_SEPARATOR = ":"

    def __init__(self, default_ttl_seconds: int = 1800):  # 30분
        """CredentialsCache 초기화

        Args:
            default_ttl_seconds: 기본 TTL (초) - 기본 30분
        """
        self._cache: Dict[str, CacheEntry[Dict[str, str]]] = {}
        self._lock = threading.RLock()
        self._default_ttl = timedelta(seconds=default_ttl_seconds)

    def _make_key(self, account_id: str, role_name: str) -> str:
        """캐시 키 생성"""
        return f"{account_id}{self.KEY_SEPARATOR}{role_name}"

    def get(self, account_id: str, role_name: str) -> Optional[Dict[str, str]]:
        """자격증명 조회

        Args:
            account_id: AWS 계정 ID
            role_name: 역할 이름

        Returns:
            자격증명 딕셔너리 (access_key_id, secret_access_key, session_token) 또는 None
        """
        key = self._make_key(account_id, role_name)

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._cache[key]
                return None
            return entry.value

    def set(
        self,
        account_id: str,
        role_name: str,
        credentials: Dict[str, str],
        expires_at: Optional[datetime] = None,
    ) -> None:
        """자격증명 저장

        Args:
            account_id: AWS 계정 ID
            role_name: 역할 이름
            credentials: 자격증명 딕셔너리
            expires_at: 만료 시간 (None이면 기본 TTL 적용)
        """
        key = self._make_key(account_id, role_name)

        if expires_at is None:
            expires_at = datetime.now(timezone.utc) + self._default_ttl

        with self._lock:
            self._cache[key] = CacheEntry(
                value=credentials,
                expires_at=expires_at,
            )

    def invalidate(self, account_id: str, role_name: str) -> bool:
        """특정 자격증명 캐시 무효화"""
        key = self._make_key(account_id, role_name)

        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def invalidate_account(self, account_id: str) -> int:
        """특정 계정의 모든 자격증명 캐시 무효화

        Args:
            account_id: AWS 계정 ID

        Returns:
            삭제된 항목 수
        """
        prefix = f"{account_id}{self.KEY_SEPARATOR}"
        count = 0

        with self._lock:
            keys_to_delete = [
                key for key in self._cache.keys() if key.startswith(prefix)
            ]
            for key in keys_to_delete:
                del self._cache[key]
                count += 1

        return count

    def clear(self) -> None:
        """모든 캐시 클리어"""
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        """유효한 캐시 항목 수"""
        with self._lock:
            # 만료된 항목 제외하고 카운트
            count = 0
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
                else:
                    count += 1
            # 만료된 항목 정리
            for key in expired_keys:
                del self._cache[key]
            return count
