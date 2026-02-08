"""
tests/plugins/cost/pricing/test_cache.py - 캐시 테스트
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from functions.analyzers.cost.pricing.cache import PriceCache


class TestPriceCache:
    """PriceCache 클래스 테스트"""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """임시 캐시 디렉토리 생성"""
        cache_dir = tmp_path / "pricing"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """테스트용 캐시 인스턴스"""
        with patch("core.shared.aws.pricing.cache._get_pricing_cache_dir", return_value=temp_cache_dir):
            return PriceCache(ttl_days=7)

    def test_set_and_get(self, cache, temp_cache_dir):
        """캐시 저장 및 조회"""
        with patch("core.shared.aws.pricing.cache._get_pricing_cache_dir", return_value=temp_cache_dir):
            test_prices = {"t3.micro": 0.0104, "t3.small": 0.0208}
            cache.set("ec2", "ap-northeast-2", test_prices)

            result = cache.get("ec2", "ap-northeast-2")
            assert result is not None
            assert result["t3.micro"] == 0.0104
            assert result["t3.small"] == 0.0208

    def test_get_nonexistent(self, cache, temp_cache_dir):
        """존재하지 않는 캐시 조회"""
        with patch("core.shared.aws.pricing.cache._get_pricing_cache_dir", return_value=temp_cache_dir):
            result = cache.get("nonexistent", "us-east-1")
            assert result is None

    def test_cache_expiration(self, cache, temp_cache_dir):
        """캐시 만료 테스트"""
        with patch("core.shared.aws.pricing.cache._get_pricing_cache_dir", return_value=temp_cache_dir):
            # 캐시 저장
            test_prices = {"t3.micro": 0.0104}
            cache.set("ec2", "ap-northeast-2", test_prices)

            # 캐시 파일 직접 수정하여 만료 시뮬레이션
            cache_path = temp_cache_dir / "ec2_ap-northeast-2.json"
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

            # 8일 전으로 설정 (TTL 7일 초과)
            expired_time = datetime.now() - timedelta(days=8)
            data["cached_at"] = expired_time.isoformat()

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            # 만료된 캐시 조회 시 None 반환
            result = cache.get("ec2", "ap-northeast-2")
            assert result is None

    def test_invalidate(self, cache, temp_cache_dir):
        """캐시 무효화 테스트"""
        with patch("core.shared.aws.pricing.cache._get_pricing_cache_dir", return_value=temp_cache_dir):
            test_prices = {"t3.micro": 0.0104}
            cache.set("ec2", "ap-northeast-2", test_prices)

            # 캐시 존재 확인
            assert cache.get("ec2", "ap-northeast-2") is not None

            # 캐시 무효화
            result = cache.invalidate("ec2", "ap-northeast-2")
            assert result is True

            # 캐시 삭제 확인
            assert cache.get("ec2", "ap-northeast-2") is None

    def test_invalidate_nonexistent(self, cache, temp_cache_dir):
        """존재하지 않는 캐시 무효화"""
        with patch("core.shared.aws.pricing.cache._get_pricing_cache_dir", return_value=temp_cache_dir):
            result = cache.invalidate("nonexistent", "us-east-1")
            assert result is False

    def test_get_info(self, cache, temp_cache_dir):
        """캐시 정보 조회"""
        with patch("core.shared.aws.pricing.cache._get_pricing_cache_dir", return_value=temp_cache_dir):
            cache.set("ec2", "ap-northeast-2", {"t3.micro": 0.0104})
            cache.set("ebs", "ap-northeast-2", {"gp3": 0.08})

            info = cache.get_info()
            assert "cache_dir" in info
            assert info["ttl_days"] == 7
            assert "files" in info
            assert len(info["files"]) == 2

    def test_empty_prices(self, cache, temp_cache_dir):
        """빈 가격 딕셔너리 저장 및 조회"""
        with patch("core.shared.aws.pricing.cache._get_pricing_cache_dir", return_value=temp_cache_dir):
            cache.set("ec2", "us-west-2", {})
            result = cache.get("ec2", "us-west-2")
            assert result == {}
