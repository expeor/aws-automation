"""
core/shared/aws/pricing/cache.py - 가격 정보 로컬 파일 캐시

AWS Pricing API 응답을 JSON 파일로 캐싱하여 반복 API 호출을 최소화한다.
가격 변동이 드물기 때문에 기본 TTL은 7일이며, 필요 시 수동 무효화 가능.

캐시 경로:
    ``{project_root}/temp/pricing/{service}_{region}.json``

동시성 보호:
    - 쓰기: ``filelock`` 라이브러리로 멀티 프로세스 환경에서 안전하게 보호
    - 읽기: 락 없이 수행하여 성능 최적화 (stale read 허용)

사용법:
    from core.shared.aws.pricing.cache import PriceCache, clear_cache

    cache = PriceCache(ttl_days=7)
    cached = cache.get("ec2", "ap-northeast-2")
    cache.set("ec2", "ap-northeast-2", {"t3.medium": 0.0416})
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

from core.tools.cache.path import get_cache_dir

logger = logging.getLogger(__name__)

# 기본 캐시 만료 (7일)
DEFAULT_TTL_DAYS = 7

# 파일 락 타임아웃 (초)
FILE_LOCK_TIMEOUT = 10


def _get_pricing_cache_dir() -> Path:
    """pricing 캐시 디렉토리 반환"""
    return Path(get_cache_dir("pricing"))


class PriceCache:
    """가격 정보 파일 기반 캐시 관리자.

    서비스/리전 조합별로 JSON 파일을 생성하여 가격 데이터를 캐싱한다.
    ``filelock`` 라이브러리로 멀티 프로세스 동시 쓰기를 방지하며,
    읽기는 락 없이 수행하여 성능을 최적화한다.

    Attributes:
        ttl_days: 캐시 만료 일수 (기본: 7일)
        cache_dir: 캐시 파일 저장 디렉토리 (``pathlib.Path``)
    """

    def __init__(self, ttl_days: int = DEFAULT_TTL_DAYS):
        """
        Args:
            ttl_days: 캐시 만료 일수
        """
        self.ttl_days = ttl_days
        self.cache_dir = _get_pricing_cache_dir()

    def _get_cache_path(self, service: str, region: str) -> Path:
        """서비스/리전 조합의 캐시 파일 경로를 반환한다.

        Args:
            service: AWS 서비스 코드 (예: ``"ec2"``, ``"ebs"``)
            region: AWS 리전 코드 (예: ``"ap-northeast-2"``)

        Returns:
            ``{cache_dir}/{service}_{region}.json`` 형태의 ``Path`` 객체
        """
        return self.cache_dir / f"{service}_{region}.json"

    def _get_lock_path(self, service: str, region: str) -> Path:
        """서비스/리전 조합의 락 파일 경로를 반환한다.

        Args:
            service: AWS 서비스 코드
            region: AWS 리전 코드

        Returns:
            ``{cache_dir}/{service}_{region}.json.lock`` 형태의 ``Path`` 객체
        """
        return self.cache_dir / f"{service}_{region}.json.lock"

    def get(self, service: str, region: str) -> dict[str, Any] | None:
        """캐시된 가격 데이터를 조회한다 (락 없이 읽기).

        파일이 존재하고 TTL 이내이면 가격 딕셔너리를 반환하고,
        파일이 없거나 만료되었으면 ``None`` 을 반환한다.

        Args:
            service: AWS 서비스 코드 (예: ``"ec2"``, ``"ebs"``, ``"rds"``)
            region: AWS 리전 코드 (예: ``"ap-northeast-2"``)

        Returns:
            캐시된 가격 딕셔너리 (예: ``{"t3.medium": 0.0416}``),
            또는 캐시가 없거나 만료된 경우 ``None``
        """
        cache_path = self._get_cache_path(service, region)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

            # 만료 확인
            cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
            if datetime.now() - cached_at > timedelta(days=self.ttl_days):
                logger.debug(f"캐시 만료: {service}/{region}")
                return None

            prices = data.get("prices", {})
            return dict(prices) if prices else {}

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"캐시 읽기 오류: {e}")
            return None

    def set(self, service: str, region: str, prices: dict[str, Any]) -> None:
        """가격 데이터를 캐시 파일에 저장한다 (파일 락으로 동시 쓰기 방지).

        ``filelock`` 으로 동시 쓰기를 방지하며, 타임아웃(10초) 초과 시 저장을 건너뛴다.

        Args:
            service: AWS 서비스 코드 (예: ``"ec2"``)
            region: AWS 리전 코드 (예: ``"ap-northeast-2"``)
            prices: 가격 데이터 딕셔너리 (예: ``{"t3.medium": 0.0416}``)
        """
        cache_path = self._get_cache_path(service, region)
        lock_path = self._get_lock_path(service, region)

        data = {
            "cached_at": datetime.now().isoformat(),
            "service": service,
            "region": region,
            "prices": prices,
        }

        try:
            with FileLock(lock_path, timeout=FILE_LOCK_TIMEOUT):
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                logger.debug(f"캐시 저장: {service}/{region} ({len(prices)} items)")
        except Timeout:
            logger.warning(f"캐시 저장 타임아웃: {service}/{region} (락 획득 실패)")
        except Exception as e:
            logger.warning(f"캐시 저장 오류: {e}")

    def invalidate(self, service: str, region: str) -> bool:
        """특정 서비스/리전의 캐시 파일을 삭제한다.

        Args:
            service: AWS 서비스 코드 (예: ``"ec2"``)
            region: AWS 리전 코드 (예: ``"ap-northeast-2"``)

        Returns:
            캐시 파일이 존재하여 삭제한 경우 ``True``, 파일이 없었으면 ``False``
        """
        cache_path = self._get_cache_path(service, region)

        if cache_path.exists():
            cache_path.unlink()
            return True
        return False

    def get_info(self) -> dict[str, Any]:
        """전체 캐시 상태 정보를 반환한다.

        Returns:
            캐시 상태 딕셔너리::

                {
                    "cache_dir": str,     # 캐시 디렉토리 경로
                    "ttl_days": int,       # TTL (일)
                    "files": [             # 캐시 파일 목록
                        {
                            "name": str,
                            "service": str,
                            "region": str,
                            "cached_at": str,   # ISO 8601 타임스탬프
                            "age_days": int,
                            "expired": bool,
                            "item_count": int,
                        },
                        ...
                    ],
                }
        """
        files: list[dict[str, Any]] = []
        info: dict[str, Any] = {
            "cache_dir": str(self.cache_dir),
            "ttl_days": self.ttl_days,
            "files": files,
        }

        if self.cache_dir.exists():
            for f in self.cache_dir.glob("*.json"):
                try:
                    with open(f, encoding="utf-8") as fp:
                        data = json.load(fp)
                    cached_at = datetime.fromisoformat(data.get("cached_at", ""))
                    age_days = (datetime.now() - cached_at).days
                    files.append(
                        {
                            "name": f.name,
                            "service": data.get("service"),
                            "region": data.get("region"),
                            "cached_at": data.get("cached_at"),
                            "age_days": age_days,
                            "expired": age_days > self.ttl_days,
                            "item_count": len(data.get("prices", {})),
                        }
                    )
                except Exception as e:
                    logger.debug("Failed to parse cache file %s: %s", f.name, e)
                    files.append({"name": f.name, "error": True})

        return info


# 모듈 레벨 캐시 인스턴스
_cache = PriceCache()


def clear_cache(service: str | None = None, region: str | None = None) -> int:
    """캐시 파일을 삭제한다.

    서비스와 리전을 지정하면 해당 캐시만, 둘 다 ``None`` 이면 전체 캐시를 삭제한다.

    Args:
        service: AWS 서비스 코드 (``None`` 이면 전체 서비스)
        region: AWS 리전 코드 (``None`` 이면 전체 리전)

    Returns:
        삭제된 캐시 파일 수
    """
    count = 0

    if service and region:
        if _cache.invalidate(service, region):
            count = 1
    else:
        pattern = "*.json"
        if service:
            pattern = f"{service}_*.json"
        elif region:
            pattern = f"*_{region}.json"

        for f in _cache.cache_dir.glob(pattern):
            f.unlink()
            count += 1

    return count


def get_cache_info() -> dict[str, Any]:
    """모듈 레벨 캐시 인스턴스의 상태 정보를 조회한다.

    Returns:
        ``PriceCache.get_info()`` 와 동일한 형식의 딕셔너리
    """
    return _cache.get_info()
