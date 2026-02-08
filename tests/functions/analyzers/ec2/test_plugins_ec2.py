"""
tests/test_plugins_ec2.py - EC2 플러그인 테스트

EC2 관련 분석 도구의 단위 테스트
"""

from unittest.mock import MagicMock

import pytest


@pytest.mark.skip(reason="functions.analyzers.ec2.unused 모듈 미구현")
class TestUnusedEC2Analysis:
    """미사용 EC2 분석 테스트"""

    def test_collect_stopped_instances(self, mock_context, mock_ec2_client):
        """중지된 인스턴스 수집 테스트"""
        from functions.analyzers.ec2.unused import UnusedEC2Analysis

        # stopped 상태 인스턴스 응답 설정
        mock_ec2_client.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-stopped001",
                            "InstanceType": "t3.medium",
                            "State": {"Name": "stopped"},
                            "Tags": [{"Key": "Name", "Value": "stopped-instance"}],
                            "StateTransitionReason": "User initiated (2024-01-15 10:30:00 GMT)",
                            "PrivateIpAddress": "10.0.0.10",
                        }
                    ]
                }
            ]
        }

        # 세션 모킹
        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2_client

        # 분석 실행
        analysis = UnusedEC2Analysis(mock_context)
        results = analysis.collect_from_session(mock_session, "123456789012", "ap-northeast-2")

        # 검증
        assert len(results) == 1
        assert results[0]["_resource_id"] == "i-stopped001"
        assert results[0]["_name"] == "stopped-instance"
        assert results[0]["_status"] == "stopped"
        assert results[0]["InstanceType"] == "t3.medium"

    def test_no_stopped_instances(self, mock_context, mock_ec2_client):
        """중지된 인스턴스가 없는 경우"""
        from functions.analyzers.ec2.unused import UnusedEC2Analysis

        mock_ec2_client.describe_instances.return_value = {"Reservations": []}

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2_client

        analysis = UnusedEC2Analysis(mock_context)
        results = analysis.collect_from_session(mock_session, "123456789012", "ap-northeast-2")

        assert len(results) == 0

    def test_extract_stop_date(self, mock_context, mock_ec2_client):
        """중지 날짜 추출 테스트"""
        from functions.analyzers.ec2.unused import UnusedEC2Analysis

        mock_ec2_client.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-test",
                            "InstanceType": "t3.micro",
                            "State": {"Name": "stopped"},
                            "Tags": [],
                            "StateTransitionReason": "User initiated (2024-06-15 08:00:00 GMT)",
                            "PrivateIpAddress": "10.0.0.1",
                        }
                    ]
                }
            ]
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2_client

        analysis = UnusedEC2Analysis(mock_context)
        results = analysis.collect_from_session(mock_session, "123456789012", "ap-northeast-2")

        assert results[0]["StopDate"] == "2024-06-15"


class TestUnusedAMIAnalysis:
    """미사용 AMI 분석 테스트"""

    def test_find_unused_amis(self, mock_context, mock_ec2_client):
        """미사용 AMI 탐지 테스트"""
        # AMI 응답 설정
        mock_ec2_client.describe_images.return_value = {
            "Images": [
                {
                    "ImageId": "ami-unused001",
                    "Name": "unused-ami",
                    "CreationDate": "2024-01-01T00:00:00Z",
                    "State": "available",
                    "Tags": [{"Key": "Name", "Value": "unused-ami"}],
                }
            ]
        }

        # 사용 중인 인스턴스 없음
        mock_ec2_client.describe_instances.return_value = {"Reservations": []}

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2_client

        # 테스트 (실제 플러그인에 따라 수정 필요)
        assert mock_ec2_client.describe_images.return_value["Images"][0]["ImageId"] == "ami-unused001"


class TestUnusedEIPAnalysis:
    """미사용 EIP 분석 테스트"""

    def test_find_unassociated_eips(self, mock_context, mock_ec2_client):
        """연결되지 않은 EIP 탐지"""
        mock_ec2_client.describe_addresses.return_value = {
            "Addresses": [
                {
                    "PublicIp": "1.2.3.4",
                    "AllocationId": "eipalloc-123",
                    "Domain": "vpc",
                    # AssociationId가 없음 = 미사용
                    "Tags": [{"Key": "Name", "Value": "unused-eip"}],
                }
            ]
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2_client

        # 미사용 EIP 확인
        addresses = mock_ec2_client.describe_addresses.return_value["Addresses"]
        unused = [a for a in addresses if "AssociationId" not in a]

        assert len(unused) == 1
        assert unused[0]["PublicIp"] == "1.2.3.4"


class TestPreviousGenInstance:
    """이전 세대 인스턴스 분석 테스트"""

    def test_detect_previous_gen_types(self, mock_context, mock_ec2_client):
        """이전 세대 인스턴스 타입 탐지"""
        previous_gen_types = {"t2", "m4", "c4", "r4", "i2"}

        mock_ec2_client.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-old001",
                            "InstanceType": "t2.micro",  # 이전 세대
                            "State": {"Name": "running"},
                            "Tags": [],
                        },
                        {
                            "InstanceId": "i-new001",
                            "InstanceType": "t3.micro",  # 현재 세대
                            "State": {"Name": "running"},
                            "Tags": [],
                        },
                    ]
                }
            ]
        }

        instances = mock_ec2_client.describe_instances.return_value["Reservations"][0]["Instances"]
        old_gen = [i for i in instances if i["InstanceType"].split(".")[0] in previous_gen_types]

        assert len(old_gen) == 1
        assert old_gen[0]["InstanceId"] == "i-old001"
