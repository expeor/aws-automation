"""
tests/shared/aws/metrics/test_batch_metrics_cache.py - batch_get_metrics 캐싱 테스트

batch_get_metrics 함수의 캐싱 동작을 테스트합니다.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from core.shared.aws.metrics import MetricQuery, MetricSessionCache, batch_get_metrics


class TestBatchGetMetricsWithCache:
    """batch_get_metrics 캐싱 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.start_time = datetime(2024, 1, 1)
        self.end_time = datetime(2024, 1, 2)

        # 기본 쿼리
        self.queries = [
            MetricQuery(
                id="q1",
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                dimensions={"InstanceId": "i-123"},
                stat="Average",
            ),
            MetricQuery(
                id="q2",
                namespace="AWS/EC2",
                metric_name="NetworkIn",
                dimensions={"InstanceId": "i-123"},
                stat="Sum",
            ),
        ]

    def _create_mock_client(self, responses: list[dict]):
        """CloudWatch 클라이언트 모킹"""
        mock_client = MagicMock()
        mock_client.get_metric_data.side_effect = responses
        return mock_client

    def test_without_cache(self):
        """캐시 없이 기본 동작"""
        mock_client = self._create_mock_client(
            [
                {
                    "MetricDataResults": [
                        {"Id": "q1", "Values": [50.0]},
                        {"Id": "q2", "Values": [1000.0]},
                    ]
                }
            ]
        )

        result = batch_get_metrics(
            mock_client,
            self.queries,
            self.start_time,
            self.end_time,
            cache=None,
        )

        assert result == {"q1": 50.0, "q2": 1000.0}
        assert mock_client.get_metric_data.call_count == 1

    def test_cache_miss_then_hit(self):
        """캐시 미스 → 히트 테스트"""
        mock_client = self._create_mock_client(
            [
                {
                    "MetricDataResults": [
                        {"Id": "q1", "Values": [50.0]},
                        {"Id": "q2", "Values": [1000.0]},
                    ]
                }
            ]
        )

        with MetricSessionCache() as cache:
            # 첫 호출: 캐시 미스, API 호출
            result1 = batch_get_metrics(
                mock_client,
                self.queries,
                self.start_time,
                self.end_time,
                cache=cache,
            )
            assert result1 == {"q1": 50.0, "q2": 1000.0}
            assert mock_client.get_metric_data.call_count == 1

            # 두 번째 호출: 캐시 히트, API 호출 없음
            result2 = batch_get_metrics(
                mock_client,
                self.queries,
                self.start_time,
                self.end_time,
                cache=cache,
            )
            assert result2 == {"q1": 50.0, "q2": 1000.0}
            assert mock_client.get_metric_data.call_count == 1  # 증가하지 않음

    def test_partial_cache_hit(self):
        """부분 캐시 히트"""
        # 첫 호출에서 q1만 조회
        query1 = [self.queries[0]]
        mock_client = self._create_mock_client(
            [
                {"MetricDataResults": [{"Id": "q1", "Values": [50.0]}]},
                {"MetricDataResults": [{"Id": "q2", "Values": [1000.0]}]},
            ]
        )

        with MetricSessionCache() as cache:
            # 첫 호출: q1만
            result1 = batch_get_metrics(
                mock_client,
                query1,
                self.start_time,
                self.end_time,
                cache=cache,
            )
            assert result1 == {"q1": 50.0}
            assert mock_client.get_metric_data.call_count == 1

            # 두 번째 호출: q1, q2 모두
            result2 = batch_get_metrics(
                mock_client,
                self.queries,
                self.start_time,
                self.end_time,
                cache=cache,
            )
            # q1은 캐시에서, q2는 API 호출
            assert result2 == {"q1": 50.0, "q2": 1000.0}
            assert mock_client.get_metric_data.call_count == 2

    def test_different_time_range_no_cache_hit(self):
        """다른 시간 범위는 캐시 미스"""
        mock_client = self._create_mock_client(
            [
                {"MetricDataResults": [{"Id": "q1", "Values": [50.0]}]},
                {"MetricDataResults": [{"Id": "q1", "Values": [75.0]}]},
            ]
        )

        with MetricSessionCache() as cache:
            # 첫 호출
            result1 = batch_get_metrics(
                mock_client,
                [self.queries[0]],
                self.start_time,
                self.end_time,
                cache=cache,
            )
            assert result1 == {"q1": 50.0}

            # 다른 시간 범위
            new_start = self.start_time + timedelta(days=1)
            new_end = self.end_time + timedelta(days=1)
            result2 = batch_get_metrics(
                mock_client,
                [self.queries[0]],
                new_start,
                new_end,
                cache=cache,
            )
            assert result2 == {"q1": 75.0}
            assert mock_client.get_metric_data.call_count == 2

    def test_different_stat_no_cache_hit(self):
        """다른 stat은 캐시 미스"""
        query_avg = MetricQuery(
            id="q1_avg",
            namespace="AWS/EC2",
            metric_name="CPUUtilization",
            dimensions={"InstanceId": "i-123"},
            stat="Average",
        )
        query_max = MetricQuery(
            id="q1_max",
            namespace="AWS/EC2",
            metric_name="CPUUtilization",
            dimensions={"InstanceId": "i-123"},
            stat="Maximum",
        )

        mock_client = self._create_mock_client(
            [
                {"MetricDataResults": [{"Id": "q1_avg", "Values": [50.0]}]},
                {"MetricDataResults": [{"Id": "q1_max", "Values": [100.0]}]},
            ]
        )

        with MetricSessionCache() as cache:
            result1 = batch_get_metrics(
                mock_client,
                [query_avg],
                self.start_time,
                self.end_time,
                cache=cache,
            )
            assert result1 == {"q1_avg": 50.0}

            result2 = batch_get_metrics(
                mock_client,
                [query_max],
                self.start_time,
                self.end_time,
                cache=cache,
            )
            assert result2 == {"q1_max": 100.0}
            assert mock_client.get_metric_data.call_count == 2

    def test_empty_queries(self):
        """빈 쿼리 목록"""
        mock_client = MagicMock()

        with MetricSessionCache() as cache:
            result = batch_get_metrics(
                mock_client,
                [],
                self.start_time,
                self.end_time,
                cache=cache,
            )
            assert result == {}
            mock_client.get_metric_data.assert_not_called()

    def test_zero_value_cached(self):
        """0 값도 캐시됨"""
        mock_client = self._create_mock_client(
            [
                {"MetricDataResults": [{"Id": "q1", "Values": [0.0]}]},
            ]
        )

        with MetricSessionCache() as cache:
            result1 = batch_get_metrics(
                mock_client,
                [self.queries[0]],
                self.start_time,
                self.end_time,
                cache=cache,
            )
            assert result1 == {"q1": 0.0}

            # 두 번째 호출: 캐시 히트
            result2 = batch_get_metrics(
                mock_client,
                [self.queries[0]],
                self.start_time,
                self.end_time,
                cache=cache,
            )
            assert result2 == {"q1": 0.0}
            assert mock_client.get_metric_data.call_count == 1

    def test_cache_key_includes_dimensions(self):
        """캐시 키에 dimensions 포함"""
        query_inst1 = MetricQuery(
            id="q_inst1",
            namespace="AWS/EC2",
            metric_name="CPUUtilization",
            dimensions={"InstanceId": "i-111"},
            stat="Average",
        )
        query_inst2 = MetricQuery(
            id="q_inst2",
            namespace="AWS/EC2",
            metric_name="CPUUtilization",
            dimensions={"InstanceId": "i-222"},
            stat="Average",
        )

        mock_client = self._create_mock_client(
            [
                {"MetricDataResults": [{"Id": "q_inst1", "Values": [50.0]}]},
                {"MetricDataResults": [{"Id": "q_inst2", "Values": [75.0]}]},
            ]
        )

        with MetricSessionCache() as cache:
            result1 = batch_get_metrics(
                mock_client,
                [query_inst1],
                self.start_time,
                self.end_time,
                cache=cache,
            )
            assert result1 == {"q_inst1": 50.0}

            # 다른 인스턴스는 캐시 미스
            result2 = batch_get_metrics(
                mock_client,
                [query_inst2],
                self.start_time,
                self.end_time,
                cache=cache,
            )
            assert result2 == {"q_inst2": 75.0}
            assert mock_client.get_metric_data.call_count == 2


class TestBatchGetMetricsCacheEdgeCases:
    """캐싱 엣지 케이스"""

    def setup_method(self):
        self.start_time = datetime(2024, 1, 1)
        self.end_time = datetime(2024, 1, 2)

    def test_cache_not_active(self):
        """캐시 비활성 상태에서 정상 동작"""
        query = MetricQuery(
            id="q1",
            namespace="AWS/EC2",
            metric_name="CPUUtilization",
            dimensions={"InstanceId": "i-123"},
            stat="Average",
        )

        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {"MetricDataResults": [{"Id": "q1", "Values": [50.0]}]}

        # MetricSessionCache 인스턴스 생성하지만 context manager 외부
        cache = MetricSessionCache()
        result = batch_get_metrics(
            mock_client,
            [query],
            self.start_time,
            self.end_time,
            cache=cache,
        )

        # 캐시가 비활성이므로 정상 API 호출
        assert result == {"q1": 50.0}
        mock_client.get_metric_data.assert_called_once()

    def test_multiple_dimensions_sorted(self):
        """다중 dimension은 정렬되어 캐시 키 생성"""
        query1 = MetricQuery(
            id="q1",
            namespace="AWS/EC2",
            metric_name="CPUUtilization",
            dimensions={"InstanceId": "i-123", "AutoScalingGroupName": "asg-1"},
            stat="Average",
        )
        # 동일한 쿼리, dimensions 순서만 다름
        query2 = MetricQuery(
            id="q2",
            namespace="AWS/EC2",
            metric_name="CPUUtilization",
            dimensions={"AutoScalingGroupName": "asg-1", "InstanceId": "i-123"},
            stat="Average",
        )

        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {"MetricDataResults": [{"Id": "q1", "Values": [50.0]}]}

        with MetricSessionCache() as cache:
            result1 = batch_get_metrics(
                mock_client,
                [query1],
                self.start_time,
                self.end_time,
                cache=cache,
            )
            assert result1 == {"q1": 50.0}

            # 같은 캐시 키로 히트되어야 함
            result2 = batch_get_metrics(
                mock_client,
                [query2],
                self.start_time,
                self.end_time,
                cache=cache,
            )
            # 캐시 히트 시 저장된 값(50.0) 반환
            assert result2 == {"q2": 50.0}
            # API 호출 1회만
            assert mock_client.get_metric_data.call_count == 1
