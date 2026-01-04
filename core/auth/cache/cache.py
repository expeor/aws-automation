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

import base64
import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Generic, Optional, TypeVar

from ..types import AccountInfo

logger = logging.getLogger(__name__)

# =============================================================================
# Token Encryption
# =============================================================================


class TokenEncryption:
    """토큰 암호화/복호화를 담당하는 클래스

    PBKDF2 키 유도 + Fernet 대칭 암호화를 사용합니다.
    암호화 키는 머신 고유 정보를 기반으로 생성됩니다.
    """

    _instance: Optional["TokenEncryption"] = None
    _lock = threading.Lock()
    _initialized: bool

    def __new__(cls) -> "TokenEncryption":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._fernet: Any | None = None
        self._encryption_available = False
        self._init_encryption()

    def _init_encryption(self) -> None:
        """암호화 모듈 초기화"""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

            # 머신 고유 키 생성 (사용자명 + 홈 디렉토리 기반)
            machine_id = f"{os.getenv('USERNAME', os.getenv('USER', 'default'))}"
            machine_id += str(Path.home())

            # PBKDF2로 키 유도
            salt = b"aws_automation_toolkit_v1"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
            self._fernet = Fernet(key)
            self._encryption_available = True
            logger.debug("토큰 암호화 초기화 완료")
        except ImportError:
            logger.warning("cryptography 모듈 없음 - 토큰이 평문으로 저장됩니다")
            self._encryption_available = False
        except Exception as e:
            logger.warning(f"암호화 초기화 실패 - 토큰이 평문으로 저장됩니다: {e}")
            self._encryption_available = False

    @property
    def is_available(self) -> bool:
        """암호화 사용 가능 여부"""
        return self._encryption_available

    def encrypt(self, data: str) -> str:
        """문자열 데이터 암호화

        Args:
            data: 암호화할 문자열

        Returns:
            암호화된 base64 문자열, 암호화 불가시 원본 반환
        """
        if not self._encryption_available or not self._fernet:
            return data
        try:
            encrypted = self._fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.debug(f"암호화 실패: {e}")
            return data

    def decrypt(self, data: str) -> str:
        """암호화된 데이터 복호화

        Args:
            data: 복호화할 base64 문자열

        Returns:
            복호화된 문자열, 복호화 불가시 원본 반환
        """
        if not self._encryption_available or not self._fernet:
            return data
        try:
            decoded = base64.urlsafe_b64decode(data.encode())
            decrypted: bytes = self._fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception:
            # 복호화 실패 시 평문으로 간주
            return data


def get_token_encryption() -> TokenEncryption:
    """TokenEncryption 싱글톤 인스턴스 반환"""
    return TokenEncryption()


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
    expires_at: datetime | None = None

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

    def remaining_seconds(self) -> int | None:
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
    refresh_token: str | None = None
    region: str | None = None
    start_url: str | None = None

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """토큰이 만료되었는지 확인

        Args:
            buffer_seconds: 만료 전 버퍼 시간 (초)

        Returns:
            True if 만료됨
        """
        try:
            # ISO 8601 형식 파싱
            expires_at = datetime.strptime(self.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

            buffer = timedelta(seconds=buffer_seconds)
            return datetime.now(timezone.utc) >= (expires_at - buffer)
        except (ValueError, TypeError):
            # 날짜 파싱 실패 시 만료된 것으로 처리
            return True

    def get_expires_at_datetime(self) -> datetime | None:
        """만료 시간을 datetime 객체로 반환"""
        try:
            return datetime.strptime(self.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None

    def to_dict(self, encrypt: bool = True) -> dict[str, Any]:
        """딕셔너리로 변환 (JSON 저장용)

        Args:
            encrypt: True이면 민감한 필드를 암호화

        Returns:
            JSON 저장용 딕셔너리
        """
        encryption = get_token_encryption() if encrypt else None

        # 민감한 필드 암호화
        access_token = self.access_token
        client_secret = self.client_secret
        refresh_token = self.refresh_token

        if encryption and encryption.is_available:
            if access_token:
                access_token = encryption.encrypt(access_token)
            if client_secret:
                client_secret = encryption.encrypt(client_secret)
            if refresh_token:
                refresh_token = encryption.encrypt(refresh_token)

        data = {
            "accessToken": access_token,
            "expiresAt": self.expires_at,
            "clientId": self.client_id,
            "clientSecret": client_secret,
            "_encrypted": encryption.is_available if encryption else False,
        }
        if refresh_token:
            data["refreshToken"] = refresh_token
        if self.region:
            data["region"] = self.region
        if self.start_url:
            data["startUrl"] = self.start_url
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenCache":
        """딕셔너리에서 생성 (JSON 로드용)

        암호화된 필드는 자동으로 복호화됩니다.
        """
        encryption = get_token_encryption()
        is_encrypted = data.get("_encrypted", False)

        # 민감한 필드 복호화
        access_token = data.get("accessToken", "")
        client_secret = data.get("clientSecret", "")
        refresh_token = data.get("refreshToken")

        if is_encrypted and encryption.is_available:
            if access_token:
                access_token = encryption.decrypt(access_token)
            if client_secret:
                client_secret = encryption.decrypt(client_secret)
            if refresh_token:
                refresh_token = encryption.decrypt(refresh_token)

        return cls(
            access_token=access_token,
            expires_at=data.get("expiresAt", ""),
            client_id=data.get("clientId", ""),
            client_secret=client_secret,
            refresh_token=refresh_token,
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
        cache_dir: str | None = None,
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
        return hashlib.sha1(input_str.encode("utf-8"), usedforsecurity=False).hexdigest()

    @property
    def cache_path(self) -> Path:
        """캐시 파일 전체 경로"""
        return self.cache_dir / f"{self._cache_key}.json"

    def load(self) -> TokenCache | None:
        """토큰 캐시를 파일에서 로드

        Returns:
            TokenCache 객체 또는 None (파일이 없거나 파싱 실패 시)
        """
        try:
            if not self.cache_path.exists():
                return None

            with open(self.cache_path, encoding="utf-8") as f:
                data = json.load(f)

            return TokenCache.from_dict(data)
        except (FileNotFoundError, PermissionError) as e:
            logger.debug(f"토큰 캐시 파일 접근 실패: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"토큰 캐시 파일 파싱 실패: {e}")
            return None
        except (KeyError, TypeError) as e:
            logger.debug(f"토큰 캐시 데이터 형식 오류: {e}")
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
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.debug(f"토큰 캐시 파일 삭제 실패: {e}")
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
        self._cache: dict[str, CacheEntry[AccountInfo]] = {}
        self._lock = threading.RLock()
        self._default_ttl = timedelta(seconds=default_ttl_seconds)

    def get(self, account_id: str) -> AccountInfo | None:
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

    def get_all(self) -> dict[str, AccountInfo]:
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
        ttl_seconds: int | None = None,
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
        accounts: dict[str, AccountInfo],
        ttl_seconds: int | None = None,
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
        self._cache: dict[str, CacheEntry[dict[str, str]]] = {}
        self._lock = threading.RLock()
        self._default_ttl = timedelta(seconds=default_ttl_seconds)

    def _make_key(self, account_id: str, role_name: str) -> str:
        """캐시 키 생성"""
        return f"{account_id}{self.KEY_SEPARATOR}{role_name}"

    def get(self, account_id: str, role_name: str) -> dict[str, str] | None:
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
        credentials: dict[str, str],
        expires_at: datetime | None = None,
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
            keys_to_delete = [key for key in self._cache if key.startswith(prefix)]
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
