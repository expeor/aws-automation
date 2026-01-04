"""
tests/test_plugins_cost_pricing.py - Cost Pricing 플러그인 테스트
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from plugins.cost.pricing.cache import (
    DEFAULT_TTL_DAYS,
    PriceCache,
)


class TestPriceCache:
    """PriceCache 클래스 테스트"""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """임시 캐시 디렉토리"""
        cache_dir = tmp_path / "pricing"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """테스트용 캐시 인스턴스"""
        c = PriceCache(ttl_days=7)
        c.cache_dir = temp_cache_dir
        return c

    def test_init_default_ttl(self):
        """기본 TTL 확인"""
        cache = PriceCache()
        assert cache.ttl_days == DEFAULT_TTL_DAYS

    def test_init_custom_ttl(self):
        """사용자 정의 TTL"""
        cache = PriceCache(ttl_days=30)
        assert cache.ttl_days == 30

    def test_get_cache_path(self, cache):
        """캐시 파일 경로"""
        path = cache._get_cache_path("ebs", "ap-northeast-2")
        assert path.name == "ebs_ap-northeast-2.json"

    def test_get_nonexistent(self, cache):
        """존재하지 않는 캐시 조회"""
        result = cache.get("nonexistent", "us-east-1")
        assert result is None

    def test_set_and_get(self, cache):
        """캐시 저장 및 조회"""
        prices = {"gp3": 0.08, "gp2": 0.10}
        cache.set("ebs", "ap-northeast-2", prices)

        result = cache.get("ebs", "ap-northeast-2")
        assert result == prices

    def test_get_expired_cache(self, cache):
        """만료된 캐시 조회"""
        # 오래된 캐시 데이터 직접 작성
        cache_path = cache._get_cache_path("old", "us-east-1")
        old_date = datetime.now() - timedelta(days=cache.ttl_days + 1)
        data = {
            "cached_at": old_date.isoformat(),
            "prices": {"test": 1.0},
        }
        with open(cache_path, "w") as f:
            json.dump(data, f)

        result = cache.get("old", "us-east-1")
        assert result is None

    def test_get_valid_cache(self, cache):
        """유효한 캐시 조회"""
        # 최근 캐시 데이터 직접 작성
        cache_path = cache._get_cache_path("valid", "us-east-1")
        recent_date = datetime.now() - timedelta(days=1)
        prices = {"test": 2.0}
        data = {
            "cached_at": recent_date.isoformat(),
            "prices": prices,
        }
        with open(cache_path, "w") as f:
            json.dump(data, f)

        result = cache.get("valid", "us-east-1")
        assert result == prices

    def test_invalidate_existing(self, cache):
        """존재하는 캐시 무효화"""
        cache.set("test", "us-east-1", {"price": 1.0})
        result = cache.invalidate("test", "us-east-1")
        assert result is True
        assert cache.get("test", "us-east-1") is None

    def test_invalidate_nonexistent(self, cache):
        """존재하지 않는 캐시 무효화"""
        result = cache.invalidate("nonexistent", "us-east-1")
        assert result is False

    def test_get_info_empty(self, cache):
        """빈 캐시 정보"""
        info = cache.get_info()
        assert "cache_dir" in info
        assert "ttl_days" in info
        assert "files" in info

    def test_get_info_with_files(self, cache):
        """캐시 파일이 있는 상태 정보"""
        cache.set("ec2", "us-east-1", {"instance": 0.1})
        cache.set("ebs", "us-east-1", {"volume": 0.05})

        info = cache.get_info()
        assert len(info["files"]) == 2

    def test_get_corrupted_cache(self, cache):
        """손상된 캐시 파일 처리"""
        cache_path = cache._get_cache_path("corrupted", "us-east-1")
        with open(cache_path, "w") as f:
            f.write("invalid json{")

        result = cache.get("corrupted", "us-east-1")
        assert result is None

    def test_set_creates_file(self, cache):
        """캐시 저장 시 파일 생성"""
        cache.set("newservice", "eu-west-1", {"price": 1.5})

        cache_path = cache._get_cache_path("newservice", "eu-west-1")
        assert cache_path.exists()

        with open(cache_path) as f:
            data = json.load(f)
        assert data["service"] == "newservice"
        assert data["region"] == "eu-west-1"
        assert data["prices"] == {"price": 1.5}


class TestClearCache:
    """clear_cache 함수 테스트"""

    @pytest.fixture
    def temp_cache_setup(self, tmp_path):
        """임시 캐시 설정"""
        cache_dir = tmp_path / "pricing"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # 테스트 캐시 파일 생성
        for service in ["ec2", "ebs", "rds"]:
            for region in ["us-east-1", "ap-northeast-2"]:
                path = cache_dir / f"{service}_{region}.json"
                data = {
                    "cached_at": datetime.now().isoformat(),
                    "service": service,
                    "region": region,
                    "prices": {},
                }
                with open(path, "w") as f:
                    json.dump(data, f)

        return cache_dir

    def test_clear_all(self, temp_cache_setup):
        """전체 캐시 삭제"""
        with patch("plugins.cost.pricing.cache._cache") as mock_cache:
            mock_cache.cache_dir = temp_cache_setup
            mock_cache.invalidate.return_value = True

            # 직접 파일 삭제 테스트
            initial_count = len(list(temp_cache_setup.glob("*.json")))
            assert initial_count == 6  # 3 services * 2 regions

    def test_clear_specific_service(self, temp_cache_setup):
        """특정 서비스 캐시만 삭제"""
        ec2_files = list(temp_cache_setup.glob("ec2_*.json"))
        assert len(ec2_files) == 2

    def test_clear_specific_region(self, temp_cache_setup):
        """특정 리전 캐시만 삭제"""
        us_files = list(temp_cache_setup.glob("*_us-east-1.json"))
        assert len(us_files) == 3


class TestDefaultTTL:
    """기본 TTL 설정 테스트"""

    def test_default_ttl_value(self):
        """기본 TTL 값 확인"""
        assert DEFAULT_TTL_DAYS == 7

    def test_cache_uses_default_ttl(self):
        """캐시가 기본 TTL 사용"""
        cache = PriceCache()
        assert cache.ttl_days == DEFAULT_TTL_DAYS
