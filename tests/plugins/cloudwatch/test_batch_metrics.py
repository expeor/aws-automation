"""
tests/plugins/cloudwatch/test_batch_metrics.py - batch_metrics.py 테스트

CloudWatch Batch Metrics Utility 테스트
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from plugins.cloudwatch.common.batch_metrics import (
    MetricQuery,
    _chunks,
    batch_get_metrics,
    build_ec2_metric_queries,
    build_elasticache_metric_queries,
    build_lambda_metric_queries,
    build_nat_metric_queries,
    build_rds_metric_queries,
    build_sagemaker_endpoint_metric_queries,
    sanitize_metric_id,
)


class TestSanitizeMetricId:
    """sanitize_metric_id 함수 테스트"""

    def test_simple_name(self):
        """단순한 이름은 그대로 유지"""
        assert sanitize_metric_id("my_function") == "my_function"

    def test_hyphen_to_underscore(self):
        """하이픈을 언더스코어로 변환"""
        assert sanitize_metric_id("my-lambda-func") == "my_lambda_func"

    def test_dot_to_underscore(self):
        """점을 언더스코어로 변환"""
        assert sanitize_metric_id("my.lambda.func") == "my_lambda_func"

    def test_mixed_special_chars(self):
        """혼합 특수문자 처리"""
        assert sanitize_metric_id("my-lambda.func_test") == "my_lambda_func_test"

    def test_number_prefix(self):
        """숫자로 시작하면 prefix 추가"""
        assert sanitize_metric_id("123-func") == "m_123_func"

    def test_consecutive_special_chars(self):
        """연속된 특수문자는 하나로 압축"""
        result = sanitize_metric_id("my--func..test")
        assert "__" not in result
        assert ".." not in result

    def test_empty_string(self):
        """빈 문자열 처리"""
        assert sanitize_metric_id("") == "metric"

    def test_max_length(self):
        """최대 길이 제한 (200자)"""
        long_name = "a" * 300
        result = sanitize_metric_id(long_name)
        assert len(result) <= 200

    def test_unicode_chars(self):
        """유니코드 문자 처리"""
        result = sanitize_metric_id("한글-func")
        # 유니코드는 _로 변환
        assert "한글" not in result


class TestMetricQuery:
    """MetricQuery 데이터클래스 테스트"""

    def test_default_stat(self):
        """기본 stat 값은 Sum"""
        query = MetricQuery(
            id="test_query",
            namespace="AWS/Lambda",
            metric_name="Invocations",
            dimensions={"FunctionName": "test-func"},
        )
        assert query.stat == "Sum"

    def test_custom_stat(self):
        """커스텀 stat 값 설정"""
        query = MetricQuery(
            id="test_query",
            namespace="AWS/Lambda",
            metric_name="Duration",
            dimensions={"FunctionName": "test-func"},
            stat="Average",
        )
        assert query.stat == "Average"

    def test_dimensions_dict(self):
        """dimensions는 딕셔너리 형태"""
        query = MetricQuery(
            id="test",
            namespace="AWS/EC2",
            metric_name="CPUUtilization",
            dimensions={"InstanceId": "i-1234567890"},
        )
        assert query.dimensions == {"InstanceId": "i-1234567890"}


class TestChunks:
    """_chunks 헬퍼 함수 테스트"""

    def test_smaller_than_chunk_size(self):
        """청크 크기보다 작은 경우"""
        items = [1, 2, 3]
        chunks = list(_chunks(items, 10))
        assert len(chunks) == 1
        assert chunks[0] == [1, 2, 3]

    def test_exact_chunk_size(self):
        """청크 크기와 정확히 일치"""
        items = [1, 2, 3, 4, 5]
        chunks = list(_chunks(items, 5))
        assert len(chunks) == 1

    def test_multiple_chunks(self):
        """여러 청크로 분할"""
        items = list(range(12))
        chunks = list(_chunks(items, 5))
        assert len(chunks) == 3
        assert chunks[0] == [0, 1, 2, 3, 4]
        assert chunks[1] == [5, 6, 7, 8, 9]
        assert chunks[2] == [10, 11]

    def test_empty_list(self):
        """빈 리스트"""
        chunks = list(_chunks([], 5))
        assert len(chunks) == 0


class TestBatchGetMetrics:
    """batch_get_metrics 함수 테스트"""

    def test_empty_queries(self):
        """빈 쿼리 목록"""
        mock_client = MagicMock()
        result = batch_get_metrics(
            mock_client,
            [],
            datetime.now(timezone.utc) - timedelta(days=7),
            datetime.now(timezone.utc),
        )
        assert result == {}
        mock_client.get_metric_data.assert_not_called()

    def test_single_query(self):
        """단일 쿼리"""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            "MetricDataResults": [
                {"Id": "test_invocations", "Values": [100, 200, 300]}
            ]
        }

        queries = [
            MetricQuery(
                id="test_invocations",
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions={"FunctionName": "test-func"},
                stat="Sum",
            )
        ]

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)

        result = batch_get_metrics(mock_client, queries, start_time, end_time)

        assert result["test_invocations"] == 600  # sum of values
        mock_client.get_metric_data.assert_called_once()

    def test_multiple_queries(self):
        """여러 쿼리"""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            "MetricDataResults": [
                {"Id": "func1_invocations", "Values": [100]},
                {"Id": "func2_invocations", "Values": [200]},
                {"Id": "func1_errors", "Values": [5]},
            ]
        }

        queries = [
            MetricQuery(
                id="func1_invocations",
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions={"FunctionName": "func1"},
            ),
            MetricQuery(
                id="func2_invocations",
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions={"FunctionName": "func2"},
            ),
            MetricQuery(
                id="func1_errors",
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions={"FunctionName": "func1"},
            ),
        ]

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)

        result = batch_get_metrics(mock_client, queries, start_time, end_time)

        assert result["func1_invocations"] == 100
        assert result["func2_invocations"] == 200
        assert result["func1_errors"] == 5

    def test_empty_values(self):
        """빈 값 처리"""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            "MetricDataResults": [
                {"Id": "test_metric", "Values": []}
            ]
        }

        queries = [
            MetricQuery(
                id="test_metric",
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions={"FunctionName": "test"},
            )
        ]

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)

        result = batch_get_metrics(mock_client, queries, start_time, end_time)

        assert result["test_metric"] == 0.0

    def test_pagination(self):
        """페이지네이션 처리"""
        mock_client = MagicMock()
        mock_client.get_metric_data.side_effect = [
            {
                "MetricDataResults": [
                    {"Id": "test_metric", "Values": [100]}
                ],
                "NextToken": "token123",
            },
            {
                "MetricDataResults": [
                    {"Id": "test_metric", "Values": [50]}
                ],
            },
        ]

        queries = [
            MetricQuery(
                id="test_metric",
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions={"FunctionName": "test"},
            )
        ]

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)

        result = batch_get_metrics(mock_client, queries, start_time, end_time)

        # 두 페이지의 값이 합산되어야 함
        assert result["test_metric"] == 150
        assert mock_client.get_metric_data.call_count == 2

    def test_throttling_retry(self):
        """스로틀링 시 재시도"""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        throttle_error = ClientError(
            {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}},
            "GetMetricData",
        )
        mock_client.get_metric_data.side_effect = [
            throttle_error,
            {"MetricDataResults": [{"Id": "test", "Values": [100]}]},
        ]

        queries = [
            MetricQuery(
                id="test",
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions={"FunctionName": "test"},
            )
        ]

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)

        with patch("time.sleep"):  # 대기 시간 스킵
            result = batch_get_metrics(mock_client, queries, start_time, end_time)

        assert result["test"] == 100
        assert mock_client.get_metric_data.call_count == 2

    def test_throttling_max_retries_exceeded(self):
        """스로틀링 최대 재시도 초과"""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        throttle_error = ClientError(
            {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}},
            "GetMetricData",
        )
        mock_client.get_metric_data.side_effect = throttle_error

        queries = [
            MetricQuery(
                id="test",
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions={"FunctionName": "test"},
            )
        ]

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)

        with patch("time.sleep"):
            with pytest.raises(ClientError):
                batch_get_metrics(
                    mock_client, queries, start_time, end_time, max_retries=2
                )

        # 초기 시도 + 2번 재시도 = 3번 호출
        assert mock_client.get_metric_data.call_count == 3


class TestBuildLambdaMetricQueries:
    """build_lambda_metric_queries 함수 테스트"""

    def test_single_function(self):
        """단일 함수에 대한 쿼리 생성"""
        queries = build_lambda_metric_queries(["my-func"])

        # Invocations, Errors, Throttles, Duration(3), ConcurrentExecutions = 7개
        assert len(queries) == 7

        # 각 쿼리 확인
        ids = [q.id for q in queries]
        assert "my_func_invocations_sum" in ids
        assert "my_func_errors_sum" in ids
        assert "my_func_throttles_sum" in ids
        assert "my_func_duration_avg" in ids
        assert "my_func_duration_max" in ids
        assert "my_func_duration_min" in ids
        assert "my_func_concurrentexecutions_max" in ids

    def test_multiple_functions(self):
        """여러 함수에 대한 쿼리 생성"""
        queries = build_lambda_metric_queries(["func1", "func2"])

        # 각 함수당 7개 = 14개
        assert len(queries) == 14

    def test_custom_metrics(self):
        """커스텀 메트릭 지정"""
        queries = build_lambda_metric_queries(
            ["test-func"], metrics=["Invocations", "Errors"]
        )

        # Invocations, Errors 각 1개 = 2개
        assert len(queries) == 2


class TestBuildRdsMetricQueries:
    """build_rds_metric_queries 함수 테스트"""

    def test_single_instance(self):
        """단일 인스턴스에 대한 쿼리 생성"""
        queries = build_rds_metric_queries(["db-instance-1"])

        # DatabaseConnections, CPUUtilization, ReadIOPS, WriteIOPS = 4개
        assert len(queries) == 4

        for q in queries:
            assert q.stat == "Average"
            assert q.namespace == "AWS/RDS"
            assert "DBInstanceIdentifier" in q.dimensions

    def test_custom_metrics(self):
        """커스텀 메트릭 지정"""
        queries = build_rds_metric_queries(
            ["db-1"], metrics=["DatabaseConnections"]
        )
        assert len(queries) == 1


class TestBuildElastiCacheMetricQueries:
    """build_elasticache_metric_queries 함수 테스트"""

    def test_redis_cluster(self):
        """Redis 클러스터 (ReplicationGroupId)"""
        queries = build_elasticache_metric_queries(
            ["my-redis-cluster"], dimension_name="ReplicationGroupId"
        )

        # CurrConnections, CPUUtilization = 2개
        assert len(queries) == 2

        for q in queries:
            assert "ReplicationGroupId" in q.dimensions

    def test_memcached_cluster(self):
        """Memcached 클러스터 (CacheClusterId)"""
        queries = build_elasticache_metric_queries(
            ["my-memcached"], dimension_name="CacheClusterId"
        )

        for q in queries:
            assert "CacheClusterId" in q.dimensions


class TestBuildNatMetricQueries:
    """build_nat_metric_queries 함수 테스트"""

    def test_nat_gateway(self):
        """NAT Gateway 쿼리 생성"""
        queries = build_nat_metric_queries(["nat-12345"])

        # BytesOut, BytesIn, PacketsOut, PacketsIn, ActiveConn, ConnAttempt = 6개
        assert len(queries) == 6

        for q in queries:
            assert q.namespace == "AWS/NATGateway"
            assert q.stat == "Sum"


class TestBuildEc2MetricQueries:
    """build_ec2_metric_queries 함수 테스트"""

    def test_ec2_instance(self):
        """EC2 인스턴스 쿼리 생성"""
        queries = build_ec2_metric_queries(["i-1234567890"])

        # CPUUtilization (avg, max), NetworkIn, NetworkOut = 4개
        assert len(queries) == 4

        cpu_queries = [q for q in queries if "cpu" in q.id.lower()]
        assert len(cpu_queries) == 2  # avg, max


class TestBuildSageMakerEndpointMetricQueries:
    """build_sagemaker_endpoint_metric_queries 함수 테스트"""

    def test_endpoint(self):
        """SageMaker Endpoint 쿼리 생성"""
        queries = build_sagemaker_endpoint_metric_queries(["my-endpoint"])

        # Invocations, InvocationsPerInstance = 2개
        assert len(queries) == 2

        for q in queries:
            assert q.namespace == "AWS/SageMaker"
            assert "EndpointName" in q.dimensions


class TestIntegration:
    """통합 테스트"""

    def test_large_query_batch(self):
        """대량 쿼리 배치 처리 (500개 단위 분할)"""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            "MetricDataResults": []
        }

        # 1000개 쿼리 생성
        queries = [
            MetricQuery(
                id=f"metric_{i}",
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions={"FunctionName": f"func-{i}"},
            )
            for i in range(1000)
        ]

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)

        batch_get_metrics(mock_client, queries, start_time, end_time)

        # 500개씩 분할하므로 2번 호출
        assert mock_client.get_metric_data.call_count == 2
