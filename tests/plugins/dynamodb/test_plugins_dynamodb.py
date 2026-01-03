"""
tests/test_plugins_dynamodb.py - DynamoDB 플러그인 테스트
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from plugins.dynamodb.unused import (
    DynamoDBAnalysisResult,
    TableFinding,
    TableInfo,
    TableStatus,
    analyze_tables,
)
from plugins.dynamodb.capacity_mode import (
    CapacityAnalysisResult,
    CapacityRecommendation,
    TableCapacityFinding,
    TableCapacityInfo,
    analyze_capacity,
)


class TestTableInfo:
    """TableInfo 데이터클래스 테스트"""

    def test_size_mb(self):
        """크기 MB 변환"""
        table = TableInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            table_name="test-table",
            table_status="ACTIVE",
            billing_mode="PROVISIONED",
            item_count=1000,
            size_bytes=1024 * 1024 * 100,  # 100MB
        )
        assert table.size_mb == 100.0

    @patch("plugins.dynamodb.unused.get_dynamodb_monthly_cost")
    def test_estimated_monthly_cost_provisioned(self, mock_cost):
        """Provisioned 테이블 월간 비용"""
        mock_cost.return_value = 10.0
        table = TableInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            table_name="test-table",
            table_status="ACTIVE",
            billing_mode="PROVISIONED",
            item_count=1000,
            size_bytes=1024**3,  # 1GB
            provisioned_read=10,
            provisioned_write=5,
        )
        assert table.estimated_monthly_cost == 10.0
        mock_cost.assert_called_once()
        # Verify PROVISIONED mode was used
        call_kwargs = mock_cost.call_args[1]
        assert call_kwargs["billing_mode"] == "PROVISIONED"
        assert call_kwargs["rcu"] == 10
        assert call_kwargs["wcu"] == 5

    @patch("plugins.dynamodb.unused.get_dynamodb_monthly_cost")
    def test_estimated_monthly_cost_ondemand(self, mock_cost):
        """On-Demand 테이블 월간 비용"""
        mock_cost.return_value = 5.0
        table = TableInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            table_name="test-table",
            table_status="ACTIVE",
            billing_mode="PAY_PER_REQUEST",
            item_count=1000,
            size_bytes=1024**3,
            consumed_read=10.0,
            consumed_write=5.0,
        )
        assert table.estimated_monthly_cost == 5.0
        # Verify PAY_PER_REQUEST mode was used
        call_kwargs = mock_cost.call_args[1]
        assert call_kwargs["billing_mode"] == "PAY_PER_REQUEST"


class TestTableStatus:
    """TableStatus Enum 테스트"""

    def test_status_values(self):
        """상태 값 확인"""
        assert TableStatus.NORMAL.value == "normal"
        assert TableStatus.UNUSED.value == "unused"
        assert TableStatus.LOW_USAGE.value == "low_usage"


class TestAnalyzeTables:
    """analyze_tables 테스트"""

    @patch("plugins.dynamodb.unused.get_dynamodb_monthly_cost")
    def test_unused_table(self, mock_cost):
        """미사용 테이블 (읽기/쓰기 0)"""
        mock_cost.return_value = 15.0
        tables = [
            TableInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                table_name="unused-table",
                table_status="ACTIVE",
                billing_mode="PROVISIONED",
                item_count=0,
                size_bytes=0,
                provisioned_read=5,
                provisioned_write=5,
                consumed_read=0.0,
                consumed_write=0.0,
            )
        ]

        result = analyze_tables(tables, "123456789012", "test", "ap-northeast-2")

        assert result.unused_tables == 1
        assert result.low_usage_tables == 0
        assert result.unused_monthly_cost == 15.0
        assert result.findings[0].status == TableStatus.UNUSED

    @patch("plugins.dynamodb.unused.get_dynamodb_monthly_cost")
    def test_low_usage_table(self, mock_cost):
        """저사용 Provisioned 테이블"""
        mock_cost.return_value = 10.0
        tables = [
            TableInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                table_name="low-usage-table",
                table_status="ACTIVE",
                billing_mode="PROVISIONED",
                item_count=1000,
                size_bytes=1024 * 1024,
                provisioned_read=100,
                provisioned_write=100,
                # 5% 사용률 (10% 미만)
                consumed_read=5.0,
                consumed_write=5.0,
            )
        ]

        result = analyze_tables(tables, "123456789012", "test", "ap-northeast-2")

        assert result.low_usage_tables == 1
        assert result.unused_tables == 0
        assert result.findings[0].status == TableStatus.LOW_USAGE

    @patch("plugins.dynamodb.unused.get_dynamodb_monthly_cost")
    def test_normal_table(self, mock_cost):
        """정상 사용 테이블"""
        mock_cost.return_value = 20.0
        tables = [
            TableInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                table_name="normal-table",
                table_status="ACTIVE",
                billing_mode="PROVISIONED",
                item_count=10000,
                size_bytes=1024 * 1024 * 500,
                provisioned_read=100,
                provisioned_write=100,
                # 50% 사용률 (10% 이상)
                consumed_read=50.0,
                consumed_write=50.0,
            )
        ]

        result = analyze_tables(tables, "123456789012", "test", "ap-northeast-2")

        assert result.normal_tables == 1
        assert result.unused_tables == 0
        assert result.low_usage_tables == 0
        assert result.findings[0].status == TableStatus.NORMAL

    @patch("plugins.dynamodb.unused.get_dynamodb_monthly_cost")
    def test_ondemand_with_usage(self, mock_cost):
        """On-Demand 테이블 (사용량 있음 = 정상)"""
        mock_cost.return_value = 5.0
        tables = [
            TableInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                table_name="ondemand-table",
                table_status="ACTIVE",
                billing_mode="PAY_PER_REQUEST",
                item_count=5000,
                size_bytes=1024 * 1024 * 100,
                consumed_read=100.0,
                consumed_write=50.0,
            )
        ]

        result = analyze_tables(tables, "123456789012", "test", "ap-northeast-2")

        # On-Demand는 저사용 판정 없음 (Provisioned가 아니므로)
        assert result.normal_tables == 1
        assert result.findings[0].status == TableStatus.NORMAL

    @patch("plugins.dynamodb.unused.get_dynamodb_monthly_cost")
    def test_mixed_tables(self, mock_cost):
        """혼합 테이블 분석"""
        mock_cost.return_value = 10.0
        tables = [
            TableInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                table_name="unused-table",
                table_status="ACTIVE",
                billing_mode="PROVISIONED",
                item_count=0,
                size_bytes=0,
                provisioned_read=5,
                provisioned_write=5,
                consumed_read=0.0,
                consumed_write=0.0,
            ),
            TableInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                table_name="low-usage-table",
                table_status="ACTIVE",
                billing_mode="PROVISIONED",
                item_count=100,
                size_bytes=1024,
                provisioned_read=100,
                provisioned_write=100,
                consumed_read=5.0,
                consumed_write=5.0,
            ),
            TableInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                table_name="normal-table",
                table_status="ACTIVE",
                billing_mode="PROVISIONED",
                item_count=10000,
                size_bytes=1024 * 1024,
                provisioned_read=100,
                provisioned_write=100,
                consumed_read=50.0,
                consumed_write=50.0,
            ),
        ]

        result = analyze_tables(tables, "123456789012", "test", "ap-northeast-2")

        assert result.total_tables == 3
        assert result.unused_tables == 1
        assert result.low_usage_tables == 1
        assert result.normal_tables == 1


class TestDynamoDBAnalysisResult:
    """DynamoDBAnalysisResult 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        result = DynamoDBAnalysisResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert result.total_tables == 0
        assert result.unused_tables == 0
        assert result.low_usage_tables == 0
        assert result.normal_tables == 0
        assert result.unused_monthly_cost == 0.0
        assert result.low_usage_monthly_cost == 0.0
        assert result.findings == []


# ============================================
# capacity_mode.py 테스트
# ============================================


class TestTableCapacityInfo:
    """TableCapacityInfo 데이터클래스 테스트"""

    def test_read_utilization(self):
        """읽기 사용률 계산"""
        table = TableCapacityInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            table_name="test-table",
            table_status="ACTIVE",
            billing_mode="PROVISIONED",
            item_count=1000,
            size_bytes=1024 * 1024,
            provisioned_read=100,
            provisioned_write=100,
            avg_consumed_read=50.0,
            avg_consumed_write=30.0,
        )
        assert table.read_utilization == 50.0
        assert table.write_utilization == 30.0

    def test_utilization_zero_provisioned(self):
        """Provisioned 0일 때 사용률"""
        table = TableCapacityInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            table_name="test-table",
            table_status="ACTIVE",
            billing_mode="PROVISIONED",
            item_count=1000,
            size_bytes=1024 * 1024,
            provisioned_read=0,
            provisioned_write=0,
            avg_consumed_read=10.0,
            avg_consumed_write=5.0,
        )
        assert table.read_utilization == 0
        assert table.write_utilization == 0

    @patch("plugins.dynamodb.capacity_mode.get_dynamodb_monthly_cost")
    def test_estimated_provisioned_cost(self, mock_cost):
        """Provisioned 비용 계산"""
        mock_cost.return_value = 15.0
        table = TableCapacityInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            table_name="test-table",
            table_status="ACTIVE",
            billing_mode="PROVISIONED",
            item_count=1000,
            size_bytes=1024**3,
            provisioned_read=50,
            provisioned_write=25,
        )
        assert table.estimated_provisioned_cost == 15.0
        call_kwargs = mock_cost.call_args[1]
        assert call_kwargs["billing_mode"] == "PROVISIONED"

    @patch("plugins.dynamodb.capacity_mode.estimate_ondemand_cost")
    def test_estimated_ondemand_cost(self, mock_estimate):
        """On-Demand 비용 추정"""
        mock_estimate.return_value = 8.0
        table = TableCapacityInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            table_name="test-table",
            table_status="ACTIVE",
            billing_mode="PAY_PER_REQUEST",
            item_count=1000,
            size_bytes=1024**3,
            avg_consumed_read=10.0,
            avg_consumed_write=5.0,
        )
        assert table.estimated_ondemand_cost == 8.0


class TestCapacityRecommendation:
    """CapacityRecommendation Enum 테스트"""

    def test_recommendation_values(self):
        """권장 사항 값 확인"""
        assert CapacityRecommendation.KEEP_PROVISIONED.value == "keep_provisioned"
        assert CapacityRecommendation.SWITCH_TO_ONDEMAND.value == "switch_to_ondemand"
        assert CapacityRecommendation.SWITCH_TO_PROVISIONED.value == "switch_to_provisioned"
        assert CapacityRecommendation.REDUCE_CAPACITY.value == "reduce_capacity"
        assert CapacityRecommendation.INCREASE_CAPACITY.value == "increase_capacity"
        assert CapacityRecommendation.OPTIMAL.value == "optimal"


class TestAnalyzeCapacity:
    """analyze_capacity 테스트"""

    @patch("plugins.dynamodb.capacity_mode.get_dynamodb_monthly_cost")
    @patch("plugins.dynamodb.capacity_mode.estimate_ondemand_cost")
    def test_provisioned_low_usage_switch_to_ondemand(self, mock_ondemand, mock_provisioned):
        """Provisioned 저사용 → On-Demand 전환 권장"""
        mock_provisioned.return_value = 50.0
        mock_ondemand.return_value = 10.0  # On-Demand가 더 저렴

        tables = [
            TableCapacityInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                table_name="low-usage-table",
                table_status="ACTIVE",
                billing_mode="PROVISIONED",
                item_count=1000,
                size_bytes=1024 * 1024,
                provisioned_read=100,
                provisioned_write=100,
                avg_consumed_read=5.0,  # 5% 사용률
                avg_consumed_write=5.0,
            )
        ]

        result = analyze_capacity(tables, "123456789012", "test", "ap-northeast-2")

        assert result.optimization_candidates == 1
        assert result.potential_savings == 40.0  # 50 - 10
        assert result.findings[0].recommendation == CapacityRecommendation.SWITCH_TO_ONDEMAND

    @patch("plugins.dynamodb.capacity_mode.get_dynamodb_monthly_cost")
    @patch("plugins.dynamodb.capacity_mode.estimate_ondemand_cost")
    def test_provisioned_throttled(self, mock_ondemand, mock_provisioned):
        """Provisioned 쓰로틀링 발생 → 용량 증가 권장"""
        mock_provisioned.return_value = 30.0
        mock_ondemand.return_value = 20.0

        tables = [
            TableCapacityInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                table_name="throttled-table",
                table_status="ACTIVE",
                billing_mode="PROVISIONED",
                item_count=10000,
                size_bytes=1024 * 1024 * 100,
                provisioned_read=50,
                provisioned_write=50,
                avg_consumed_read=45.0,
                avg_consumed_write=48.0,
                throttled_read=100.0,
                throttled_write=50.0,
            )
        ]

        result = analyze_capacity(tables, "123456789012", "test", "ap-northeast-2")

        assert result.findings[0].recommendation == CapacityRecommendation.INCREASE_CAPACITY

    @patch("plugins.dynamodb.capacity_mode.get_dynamodb_monthly_cost")
    @patch("plugins.dynamodb.capacity_mode.estimate_ondemand_cost")
    def test_provisioned_optimal(self, mock_ondemand, mock_provisioned):
        """Provisioned 적정 사용률"""
        mock_provisioned.return_value = 25.0
        mock_ondemand.return_value = 30.0

        tables = [
            TableCapacityInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                table_name="optimal-table",
                table_status="ACTIVE",
                billing_mode="PROVISIONED",
                item_count=5000,
                size_bytes=1024 * 1024 * 50,
                provisioned_read=100,
                provisioned_write=100,
                avg_consumed_read=50.0,  # 50% 사용률
                avg_consumed_write=40.0,  # 40% 사용률
            )
        ]

        result = analyze_capacity(tables, "123456789012", "test", "ap-northeast-2")

        assert result.findings[0].recommendation == CapacityRecommendation.OPTIMAL

    @patch("plugins.dynamodb.capacity_mode.get_dynamodb_monthly_cost")
    @patch("plugins.dynamodb.capacity_mode.estimate_ondemand_cost")
    def test_ondemand_switch_to_provisioned(self, mock_ondemand, mock_provisioned):
        """On-Demand → Provisioned 전환 권장"""
        mock_provisioned.return_value = 20.0
        mock_ondemand.return_value = 50.0  # On-Demand가 더 비쌈

        tables = [
            TableCapacityInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                table_name="ondemand-table",
                table_status="ACTIVE",
                billing_mode="PAY_PER_REQUEST",
                item_count=10000,
                size_bytes=1024 * 1024 * 100,
                avg_consumed_read=100.0,
                avg_consumed_write=50.0,
            )
        ]

        result = analyze_capacity(tables, "123456789012", "test", "ap-northeast-2")

        assert result.ondemand_tables == 1
        assert result.optimization_candidates == 1
        assert result.potential_savings == 30.0  # 50 - 20
        assert result.findings[0].recommendation == CapacityRecommendation.SWITCH_TO_PROVISIONED

    @patch("plugins.dynamodb.capacity_mode.get_dynamodb_monthly_cost")
    @patch("plugins.dynamodb.capacity_mode.estimate_ondemand_cost")
    def test_ondemand_optimal(self, mock_ondemand, mock_provisioned):
        """On-Demand 최적"""
        mock_provisioned.return_value = 40.0
        mock_ondemand.return_value = 30.0  # On-Demand가 더 저렴

        tables = [
            TableCapacityInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                table_name="ondemand-optimal",
                table_status="ACTIVE",
                billing_mode="PAY_PER_REQUEST",
                item_count=5000,
                size_bytes=1024 * 1024 * 50,
                avg_consumed_read=50.0,
                avg_consumed_write=25.0,
            )
        ]

        result = analyze_capacity(tables, "123456789012", "test", "ap-northeast-2")

        assert result.findings[0].recommendation == CapacityRecommendation.OPTIMAL


class TestCapacityAnalysisResult:
    """CapacityAnalysisResult 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        result = CapacityAnalysisResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert result.total_tables == 0
        assert result.provisioned_tables == 0
        assert result.ondemand_tables == 0
        assert result.optimization_candidates == 0
        assert result.potential_savings == 0.0
        assert result.findings == []
