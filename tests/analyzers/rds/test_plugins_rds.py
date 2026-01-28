"""
tests/test_plugins_rds.py - RDS 플러그인 테스트
"""

from datetime import datetime, timezone

from analyzers.rds.unused import (
    InstanceStatus,
    RDSAnalysisResult,
    RDSInstanceInfo,
    analyze_instances,
)


class TestRDSInstanceInfo:
    """RDSInstanceInfo 데이터클래스 테스트"""

    def test_estimated_monthly_cost_single_az(self):
        """단일 AZ 월간 비용 추정"""
        instance = RDSInstanceInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            db_instance_id="test-db",
            db_instance_class="db.t3.medium",
            engine="mysql",
            engine_version="8.0",
            status="available",
            multi_az=False,
            storage_type="gp2",
            allocated_storage=100,  # 100GB
            created_at=datetime.now(timezone.utc),
        )
        # db.t3.medium: $0.068/hr * 730 = $49.64
        # Storage: 100 * $0.115 = $11.50
        # Total: ~$61.14
        cost = instance.estimated_monthly_cost
        assert 60 < cost < 65

    def test_estimated_monthly_cost_multi_az(self):
        """Multi-AZ 월간 비용 추정"""
        instance = RDSInstanceInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            db_instance_id="test-db",
            db_instance_class="db.t3.medium",
            engine="mysql",
            engine_version="8.0",
            status="available",
            multi_az=True,  # Multi-AZ
            storage_type="gp2",
            allocated_storage=100,
            created_at=datetime.now(timezone.utc),
        )
        # db.t3.medium Multi-AZ (ap-northeast-2): $0.073 * 2 * 730 = $106.58
        # Storage Multi-AZ: 100 * $0.115 * 2 = $23.00
        # Total: ~$129.58
        cost = instance.estimated_monthly_cost
        assert 125 < cost < 135

    def test_default_values(self):
        """기본값 확인"""
        instance = RDSInstanceInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            db_instance_id="test-db",
            db_instance_class="db.t3.micro",
            engine="mysql",
            engine_version="8.0",
            status="available",
            multi_az=False,
            storage_type="gp2",
            allocated_storage=20,
            created_at=None,
        )
        assert instance.avg_connections == 0.0
        assert instance.avg_cpu == 0.0
        assert instance.avg_read_iops == 0.0
        assert instance.avg_write_iops == 0.0


class TestInstanceStatus:
    """InstanceStatus Enum 테스트"""

    def test_status_values(self):
        """상태 값 확인"""
        assert InstanceStatus.NORMAL.value == "normal"
        assert InstanceStatus.UNUSED.value == "unused"
        assert InstanceStatus.LOW_USAGE.value == "low_usage"
        assert InstanceStatus.STOPPED.value == "stopped"


class TestAnalyzeInstances:
    """analyze_instances 테스트"""

    def test_stopped_instance(self):
        """정지된 인스턴스"""
        instances = [
            RDSInstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                db_instance_id="stopped-db",
                db_instance_class="db.t3.micro",
                engine="mysql",
                engine_version="8.0",
                status="stopped",
                multi_az=False,
                storage_type="gp2",
                allocated_storage=20,
                created_at=datetime.now(timezone.utc),
            )
        ]

        result = analyze_instances(instances, "123456789012", "test", "ap-northeast-2")

        assert result.stopped_instances == 1
        assert result.findings[0].status == InstanceStatus.STOPPED

    def test_unused_instance(self):
        """미사용 인스턴스 (연결 없음)"""
        instances = [
            RDSInstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                db_instance_id="unused-db",
                db_instance_class="db.t3.medium",
                engine="mysql",
                engine_version="8.0",
                status="available",
                multi_az=False,
                storage_type="gp2",
                allocated_storage=100,
                created_at=datetime.now(timezone.utc),
                avg_connections=0,  # 연결 없음
                avg_cpu=0,
            )
        ]

        result = analyze_instances(instances, "123456789012", "test", "ap-northeast-2")

        assert result.unused_instances == 1
        assert result.unused_monthly_cost > 0
        assert result.findings[0].status == InstanceStatus.UNUSED

    def test_low_usage_instance(self):
        """저사용 인스턴스"""
        instances = [
            RDSInstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                db_instance_id="low-usage-db",
                db_instance_class="db.r5.large",
                engine="mysql",
                engine_version="8.0",
                status="available",
                multi_az=True,
                storage_type="gp2",
                allocated_storage=200,
                created_at=datetime.now(timezone.utc),
                avg_connections=5,  # 연결 있음
                avg_cpu=2.5,  # CPU 5% 미만
            )
        ]

        result = analyze_instances(instances, "123456789012", "test", "ap-northeast-2")

        assert result.low_usage_instances == 1
        assert result.low_usage_monthly_cost > 0
        assert result.findings[0].status == InstanceStatus.LOW_USAGE

    def test_normal_instance(self):
        """정상 인스턴스"""
        instances = [
            RDSInstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                db_instance_id="normal-db",
                db_instance_class="db.t3.medium",
                engine="mysql",
                engine_version="8.0",
                status="available",
                multi_az=False,
                storage_type="gp2",
                allocated_storage=100,
                created_at=datetime.now(timezone.utc),
                avg_connections=50,
                avg_cpu=25.0,  # CPU 5% 이상
            )
        ]

        result = analyze_instances(instances, "123456789012", "test", "ap-northeast-2")

        assert result.normal_instances == 1
        assert result.findings[0].status == InstanceStatus.NORMAL

    def test_mixed_instances(self):
        """혼합 인스턴스 분석"""
        instances = [
            RDSInstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                db_instance_id="stopped-db",
                db_instance_class="db.t3.micro",
                engine="mysql",
                engine_version="8.0",
                status="stopped",
                multi_az=False,
                storage_type="gp2",
                allocated_storage=20,
                created_at=datetime.now(timezone.utc),
            ),
            RDSInstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                db_instance_id="unused-db",
                db_instance_class="db.t3.medium",
                engine="mysql",
                engine_version="8.0",
                status="available",
                multi_az=False,
                storage_type="gp2",
                allocated_storage=100,
                created_at=datetime.now(timezone.utc),
                avg_connections=0,
                avg_cpu=0,
            ),
            RDSInstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                db_instance_id="low-db",
                db_instance_class="db.t3.large",
                engine="mysql",
                engine_version="8.0",
                status="available",
                multi_az=False,
                storage_type="gp2",
                allocated_storage=100,
                created_at=datetime.now(timezone.utc),
                avg_connections=10,
                avg_cpu=3.0,  # Low usage
            ),
            RDSInstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                db_instance_id="normal-db",
                db_instance_class="db.t3.medium",
                engine="mysql",
                engine_version="8.0",
                status="available",
                multi_az=False,
                storage_type="gp2",
                allocated_storage=100,
                created_at=datetime.now(timezone.utc),
                avg_connections=100,
                avg_cpu=50.0,
            ),
        ]

        result = analyze_instances(instances, "123456789012", "test", "ap-northeast-2")

        assert result.total_instances == 4
        assert result.stopped_instances == 1
        assert result.unused_instances == 1
        assert result.low_usage_instances == 1
        assert result.normal_instances == 1


class TestRDSAnalysisResult:
    """RDSAnalysisResult 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        result = RDSAnalysisResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert result.total_instances == 0
        assert result.unused_instances == 0
        assert result.low_usage_instances == 0
        assert result.stopped_instances == 0
        assert result.normal_instances == 0
        assert result.unused_monthly_cost == 0.0
        assert result.low_usage_monthly_cost == 0.0
        assert result.findings == []
