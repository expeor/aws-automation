"""
plugins/cost/pricing/cache.py - 가격 정보 로컬 캐시

가격 데이터를 로컬에 캐싱하여 API 호출을 최소화합니다.
기본 만료: 7일 (가격 변동이 자주 없음)

캐시 경로: {project_root}/temp/pricing/

동시성 보호:
- 파일 락(filelock)으로 멀티 프로세스 환경에서 안전한 캐시 쓰기
- 읽기는 락 없이 수행 (성능 최적화)
"""

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
    """가격 정보 캐시 관리자

    멀티 프로세스 환경에서 안전한 파일 기반 캐시입니다.
    filelock 라이브러리를 사용하여 동시 쓰기를 방지합니다.
    """

    def __init__(self, ttl_days: int = DEFAULT_TTL_DAYS):
        """
        Args:
            ttl_days: 캐시 만료 일수
        """
        self.ttl_days = ttl_days
        self.cache_dir = _get_pricing_cache_dir()

    def _get_cache_path(self, service: str, region: str) -> Path:
        """캐시 파일 경로 반환"""
        return self.cache_dir / f"{service}_{region}.json"

    def _get_lock_path(self, service: str, region: str) -> Path:
        """락 파일 경로 반환"""
        return self.cache_dir / f"{service}_{region}.json.lock"

    def get(self, service: str, region: str) -> dict[str, Any] | None:
        """캐시된 가격 데이터 조회 (락 없이 읽기)

        Args:
            service: 서비스 코드 (ec2, ebs, rds 등)
            region: AWS 리전

        Returns:
            캐시된 데이터 또는 None (만료/없음)
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
        """가격 데이터 캐싱 (파일 락으로 동시 쓰기 방지)

        Args:
            service: 서비스 코드
            region: AWS 리전
            prices: 가격 데이터 딕셔너리
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
        """특정 캐시 무효화

        Args:
            service: 서비스 코드
            region: AWS 리전

        Returns:
            삭제 성공 여부
        """
        cache_path = self._get_cache_path(service, region)

        if cache_path.exists():
            cache_path.unlink()
            return True
        return False

    def get_info(self) -> dict[str, Any]:
        """캐시 상태 정보

        Returns:
            캐시 파일 목록 및 상태
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
                except Exception:
                    files.append({"name": f.name, "error": True})

        return info


# 모듈 레벨 캐시 인스턴스
_cache = PriceCache()


def clear_cache(service: str | None = None, region: str | None = None) -> int:
    """캐시 삭제

    Args:
        service: 서비스 코드 (None이면 전체)
        region: AWS 리전 (None이면 전체)

    Returns:
        삭제된 파일 수
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
    """캐시 상태 정보 조회"""
    return _cache.get_info()
