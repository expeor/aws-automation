"""
tests/plugins/vpc/ip_search/test_ip_ranges_providers.py - IP Range Providers Tests

Tests for cloud provider IP range functionality.
"""

from unittest.mock import Mock, patch

import pytest

from plugins.vpc.ip_search.common.ip_ranges.providers import (
    IPRangeLoadResult,
    PublicIPResult,
    get_search_backend,
    load_ip_ranges_parallel,
    load_ip_ranges_parallel_with_errors,
    search_in_aws,
    search_in_cloudflare,
    search_in_fastly,
    search_in_gcp,
)


class TestPublicIPResult:
    """Tests for PublicIPResult dataclass"""

    def test_public_ip_result_creation(self) -> None:
        """Test PublicIPResult creation"""
        result = PublicIPResult(
            ip_address="52.94.76.1",
            provider="AWS",
            service="AMAZON",
            ip_prefix="52.94.76.0/24",
            region="us-east-1",
        )

        assert result.ip_address == "52.94.76.1"
        assert result.provider == "AWS"
        assert result.service == "AMAZON"
        assert result.ip_prefix == "52.94.76.0/24"
        assert result.region == "us-east-1"


class TestSearchFunctions:
    """Tests for search functions"""

    def test_search_in_aws_match(self) -> None:
        """Test AWS IP search with match"""
        data = {
            "prefixes": [
                {"ip_prefix": "52.94.76.0/24", "region": "us-east-1", "service": "AMAZON"},
            ],
            "ipv6_prefixes": [],
        }

        results = search_in_aws("52.94.76.1", data)

        assert len(results) == 1
        assert results[0].provider == "AWS"
        assert results[0].service == "AMAZON"
        assert results[0].region == "us-east-1"

    def test_search_in_aws_no_match(self) -> None:
        """Test AWS IP search with no match"""
        data = {
            "prefixes": [
                {"ip_prefix": "52.94.76.0/24", "region": "us-east-1", "service": "AMAZON"},
            ],
            "ipv6_prefixes": [],
        }

        results = search_in_aws("10.0.0.1", data)
        assert len(results) == 0

    def test_search_in_aws_invalid_ip(self) -> None:
        """Test AWS IP search with invalid IP"""
        data = {"prefixes": [], "ipv6_prefixes": []}
        results = search_in_aws("invalid", data)
        assert len(results) == 0

    def test_search_in_gcp_match(self) -> None:
        """Test GCP IP search with match"""
        data = {
            "prefixes": [
                {"ipv4Prefix": "35.192.0.0/12", "scope": "us-central1", "service": "Google Cloud"},
            ]
        }

        results = search_in_gcp("35.200.0.1", data)

        assert len(results) == 1
        assert results[0].provider == "GCP"
        assert results[0].service == "Google Cloud"

    def test_search_in_cloudflare_match(self) -> None:
        """Test Cloudflare IP search with match"""
        data = {
            "prefixes": [
                {"ip_prefix": "103.21.244.0/22", "service": "Cloudflare CDN"},
            ],
            "ipv6_prefixes": [],
        }

        results = search_in_cloudflare("103.21.244.1", data)

        assert len(results) == 1
        assert results[0].provider == "Cloudflare"
        assert results[0].service == "Cloudflare CDN"
        assert results[0].region == "Global"

    def test_search_in_fastly_match(self) -> None:
        """Test Fastly IP search with match"""
        data = {
            "prefixes": [
                {"ip_prefix": "23.235.32.0/20", "service": "Fastly CDN"},
            ],
            "ipv6_prefixes": [],
        }

        results = search_in_fastly("23.235.32.1", data)

        assert len(results) == 1
        assert results[0].provider == "Fastly"
        assert results[0].service == "Fastly CDN"
        assert results[0].region == "Global"


class TestLoadIPRangesParallel:
    """Tests for parallel IP range loading"""

    @patch("plugins.vpc.ip_search.common.ip_ranges.providers.get_aws_ip_ranges")
    @patch("plugins.vpc.ip_search.common.ip_ranges.providers.get_gcp_ip_ranges")
    def test_load_ip_ranges_parallel(
        self, mock_gcp: Mock, mock_aws: Mock
    ) -> None:
        """Test parallel loading of IP ranges"""
        mock_aws.return_value = {"prefixes": [{"ip_prefix": "52.0.0.0/8"}]}
        mock_gcp.return_value = {"prefixes": [{"ipv4Prefix": "35.0.0.0/8"}]}

        result = load_ip_ranges_parallel({"aws", "gcp"})

        assert "aws" in result
        assert "gcp" in result
        mock_aws.assert_called_once()
        mock_gcp.assert_called_once()

    @patch("plugins.vpc.ip_search.common.ip_ranges.providers.get_aws_ip_ranges")
    def test_load_ip_ranges_parallel_with_error(self, mock_aws: Mock) -> None:
        """Test parallel loading with error"""
        mock_aws.side_effect = Exception("Network error")

        result = load_ip_ranges_parallel({"aws"})

        assert "aws" in result
        assert result["aws"] == {}  # Empty on error

    @patch("plugins.vpc.ip_search.common.ip_ranges.providers.get_cloudflare_ip_ranges")
    @patch("plugins.vpc.ip_search.common.ip_ranges.providers.get_fastly_ip_ranges")
    def test_load_cdn_providers(
        self, mock_fastly: Mock, mock_cloudflare: Mock
    ) -> None:
        """Test loading CDN providers (Cloudflare, Fastly)"""
        mock_cloudflare.return_value = {"prefixes": [{"ip_prefix": "103.0.0.0/8"}]}
        mock_fastly.return_value = {"prefixes": [{"ip_prefix": "23.0.0.0/8"}]}

        result = load_ip_ranges_parallel({"cloudflare", "fastly"})

        assert "cloudflare" in result
        assert "fastly" in result


class TestLoadIPRangesWithErrors:
    """Tests for parallel IP range loading with error collection"""

    @patch("plugins.vpc.ip_search.common.ip_ranges.providers.get_aws_ip_ranges")
    def test_load_with_errors_success(self, mock_aws: Mock) -> None:
        """Test loading with error collection - success case"""
        mock_aws.return_value = {"prefixes": [{"ip_prefix": "52.0.0.0/8"}]}

        result = load_ip_ranges_parallel_with_errors({"aws"})

        assert isinstance(result, IPRangeLoadResult)
        assert "aws" in result.data
        assert not result.errors.has_errors

    @patch("plugins.vpc.ip_search.common.ip_ranges.providers.get_aws_ip_ranges")
    def test_load_with_errors_failure(self, mock_aws: Mock) -> None:
        """Test loading with error collection - failure case"""
        mock_aws.side_effect = Exception("Network error")

        result = load_ip_ranges_parallel_with_errors({"aws"})

        assert isinstance(result, IPRangeLoadResult)
        assert result.data["aws"] == {}
        assert result.errors.has_errors


class TestSearchBackend:
    """Tests for search backend detection"""

    def test_get_search_backend(self) -> None:
        """Test getting search backend type"""
        backend = get_search_backend()
        assert backend in ("radix_tree", "binary_search")
