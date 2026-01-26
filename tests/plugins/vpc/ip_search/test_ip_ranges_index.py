"""
tests/plugins/vpc/ip_search/test_ip_ranges_index.py - IP Range Index Tests

Tests for the optimized IP range lookup functionality.
"""

import pytest

from plugins.vpc.ip_search.common.ip_ranges.index import (
    IPPrefixData,
    IPRangeIndex,
    MultiProviderIndex,
)


class TestIPRangeIndex:
    """Tests for IPRangeIndex class"""

    def test_add_prefix_ipv4(self) -> None:
        """Test adding IPv4 prefixes"""
        index = IPRangeIndex()
        index.add_prefix("10.0.0.0/8", "AWS", "EC2", "us-east-1")
        index.build()

        assert index.prefix_count == 1

    def test_add_prefix_ipv6(self) -> None:
        """Test adding IPv6 prefixes"""
        index = IPRangeIndex()
        index.add_prefix("2600::/32", "AWS", "EC2", "us-east-1")
        index.build()

        assert index.prefix_count == 1

    def test_search_ipv4_match(self) -> None:
        """Test IPv4 address matching"""
        index = IPRangeIndex()
        index.add_prefix("10.0.0.0/8", "AWS", "EC2", "us-east-1")
        index.add_prefix("192.168.0.0/16", "GCP", "GCE", "us-central1")
        index.build()

        results = index.search("10.1.2.3")
        assert len(results) == 1
        assert results[0].provider == "AWS"
        assert results[0].service == "EC2"

    def test_search_ipv4_no_match(self) -> None:
        """Test IPv4 address not matching any prefix"""
        index = IPRangeIndex()
        index.add_prefix("10.0.0.0/8", "AWS", "EC2", "us-east-1")
        index.build()

        results = index.search("172.16.0.1")
        assert len(results) == 0

    def test_search_invalid_ip(self) -> None:
        """Test searching with invalid IP address"""
        index = IPRangeIndex()
        index.add_prefix("10.0.0.0/8", "AWS", "EC2", "us-east-1")
        index.build()

        results = index.search("invalid-ip")
        assert len(results) == 0

    def test_search_batch(self) -> None:
        """Test batch IP search"""
        index = IPRangeIndex()
        index.add_prefix("10.0.0.0/8", "AWS", "EC2", "us-east-1")
        index.add_prefix("192.168.0.0/16", "GCP", "GCE", "us-central1")
        index.build()

        results = index.search_batch(["10.1.2.3", "192.168.1.1", "172.16.0.1"])

        assert "10.1.2.3" in results
        assert len(results["10.1.2.3"]) == 1
        assert results["10.1.2.3"][0].provider == "AWS"

        assert "192.168.1.1" in results
        assert len(results["192.168.1.1"]) == 1
        assert results["192.168.1.1"][0].provider == "GCP"

        assert "172.16.0.1" in results
        assert len(results["172.16.0.1"]) == 0

    def test_backend_type(self) -> None:
        """Test backend type detection"""
        index = IPRangeIndex()
        # Should be binary_search unless pytricia is installed
        assert index.backend in ("binary_search", "radix_tree")


class TestMultiProviderIndex:
    """Tests for MultiProviderIndex class"""

    def test_load_aws_provider(self) -> None:
        """Test loading AWS IP ranges"""
        index = MultiProviderIndex()
        aws_data = {
            "prefixes": [
                {"ip_prefix": "52.94.76.0/24", "region": "us-east-1", "service": "AMAZON"},
            ],
            "ipv6_prefixes": [],
        }
        index.load_provider("aws", aws_data)
        index.build()

        assert "aws" in index.loaded_providers
        assert index.prefix_count == 1

        results = index.search("52.94.76.1")
        assert len(results) == 1
        assert results[0].provider == "AWS"

    def test_load_cloudflare_provider(self) -> None:
        """Test loading Cloudflare IP ranges"""
        index = MultiProviderIndex()
        cf_data = {
            "prefixes": [
                {"ip_prefix": "103.21.244.0/22", "service": "Cloudflare CDN"},
            ],
            "ipv6_prefixes": [],
        }
        index.load_provider("cloudflare", cf_data)
        index.build()

        assert "cloudflare" in index.loaded_providers

        results = index.search("103.21.244.1")
        assert len(results) == 1
        assert results[0].provider == "Cloudflare"

    def test_load_fastly_provider(self) -> None:
        """Test loading Fastly IP ranges"""
        index = MultiProviderIndex()
        fastly_data = {
            "prefixes": [
                {"ip_prefix": "23.235.32.0/20", "service": "Fastly CDN"},
            ],
            "ipv6_prefixes": [],
        }
        index.load_provider("fastly", fastly_data)
        index.build()

        assert "fastly" in index.loaded_providers

        results = index.search("23.235.32.1")
        assert len(results) == 1
        assert results[0].provider == "Fastly"

    def test_load_multiple_providers(self) -> None:
        """Test loading multiple providers"""
        index = MultiProviderIndex()

        aws_data = {"prefixes": [{"ip_prefix": "52.94.0.0/16", "region": "us-east-1", "service": "AMAZON"}]}
        gcp_data = {"prefixes": [{"ipv4Prefix": "35.192.0.0/12", "scope": "us-central1", "service": "Google Cloud"}]}

        index.load_provider("aws", aws_data)
        index.load_provider("gcp", gcp_data)
        index.build()

        assert "aws" in index.loaded_providers
        assert "gcp" in index.loaded_providers
        assert index.prefix_count == 2


class TestIPPrefixData:
    """Tests for IPPrefixData dataclass"""

    def test_ipprefix_data_creation(self) -> None:
        """Test IPPrefixData creation"""
        data = IPPrefixData(
            prefix="10.0.0.0/8",
            provider="AWS",
            service="EC2",
            region="us-east-1",
            extra={"network_border_group": "us-east-1"},
        )

        assert data.prefix == "10.0.0.0/8"
        assert data.provider == "AWS"
        assert data.service == "EC2"
        assert data.region == "us-east-1"
        assert data.extra["network_border_group"] == "us-east-1"
