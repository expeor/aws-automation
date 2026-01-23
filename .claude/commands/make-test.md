# /make-test - 플러그인 테스트 스캐폴딩

플러그인 모듈에 대한 테스트 파일을 자동 생성합니다.

## 사용법

```
/make-test <service>/<module>
```

예시:
```
/make-test efs/unused
/make-test ec2/security
/make-test vpc/sg_audit
```

## 실행 순서

### 1. 대상 모듈 확인

사용자 입력 `$ARGUMENTS`에서 서비스와 모듈명 추출:
- 형식: `{service}/{module}` (예: `efs/unused`)
- 대상 파일: `plugins/{service}/{module}.py`

파일이 존재하지 않으면 오류 메시지 출력 후 종료.

### 2. 모듈 분석

대상 플러그인 파일에서 다음 정보 추출:
- **run() 함수**: 존재 여부 확인 (필수)
- **collect_* 함수**: 수집 함수 목록
- **analyze_* 함수**: 분석 함수 목록
- **dataclass**: 데이터 클래스 목록
- **AWS 서비스**: `get_client(session, "서비스명")` 패턴에서 추출
- **사용 모듈**: import 문 분석

### 3. 테스트 파일 생성

생성 경로: `tests/plugins/{service}/test_{module}.py`

#### 템플릿 구조

```python
"""
tests/plugins/{service}/test_{module}.py - {도구명} 테스트
"""
import pytest
from unittest.mock import MagicMock, patch

# moto 사용 가능 여부 확인
try:
    import moto
    HAS_MOTO = True
except ImportError:
    HAS_MOTO = False


class TestCollect{Resource}:
    """collect_{resources}() 함수 테스트"""

    def test_collect_normal(self, mock_context, mock_boto3_session):
        """정상 수집 케이스"""
        # Arrange
        from plugins.{service}.{module} import collect_{resource}

        mock_client = MagicMock()
        mock_boto3_session.client.return_value = mock_client
        mock_client.{api_method}.return_value = {{
            # 샘플 응답 구조
        }}

        # Act
        result = collect_{resource}(
            mock_boto3_session,
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2"
        )

        # Assert
        assert isinstance(result, list)

    def test_collect_empty(self, mock_context, mock_boto3_session):
        """빈 결과 케이스"""
        from plugins.{service}.{module} import collect_{resource}

        mock_client = MagicMock()
        mock_boto3_session.client.return_value = mock_client
        mock_client.{api_method}.return_value = {{}}

        result = collect_{resource}(
            mock_boto3_session,
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2"
        )

        assert result == []

    def test_collect_access_denied(self, mock_context, mock_boto3_session):
        """권한 없음 에러 케이스"""
        from botocore.exceptions import ClientError
        from plugins.{service}.{module} import collect_{resource}

        mock_client = MagicMock()
        mock_boto3_session.client.return_value = mock_client
        mock_client.{api_method}.side_effect = ClientError(
            {{"Error": {{"Code": "AccessDenied", "Message": "Access Denied"}}}},
            "{api_method}"
        )

        result = collect_{resource}(
            mock_boto3_session,
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2"
        )

        assert result == []


class TestAnalyze{Resource}:
    """analyze_{resources}() 함수 테스트"""

    def test_analyze_normal(self):
        """정상 분석 케이스"""
        from plugins.{service}.{module} import analyze_{resource}

        # Arrange
        test_data = [
            # 테스트 데이터
        ]

        # Act
        result = analyze_{resource}(
            test_data,
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2"
        )

        # Assert
        assert result is not None

    def test_analyze_empty_input(self):
        """빈 입력 케이스"""
        from plugins.{service}.{module} import analyze_{resource}

        result = analyze_{resource}(
            [],
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2"
        )

        # 빈 결과 또는 기본값 반환 확인
        assert result is not None


class TestRun:
    """run() 통합 테스트"""

    @patch("plugins.{service}.{module}.parallel_collect")
    @patch("plugins.{service}.{module}.generate_reports")
    def test_run_success(self, mock_reports, mock_parallel, mock_context):
        """정상 실행"""
        from plugins.{service}.{module} import run

        # Arrange
        mock_result = MagicMock()
        mock_result.get_data.return_value = [MagicMock()]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result
        mock_reports.return_value = {
            "excel": "/tmp/test_report.xlsx",
            "html": "/tmp/test_report.html",
        }

        # Act
        run(mock_context)

        # Assert
        mock_parallel.assert_called_once()
        mock_reports.assert_called_once()

    @patch("plugins.{service}.{module}.parallel_collect")
    def test_run_no_results(self, mock_parallel, mock_context):
        """결과 없음"""
        from plugins.{service}.{module} import run

        mock_result = MagicMock()
        mock_result.get_data.return_value = []
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        # Should complete without error
        run(mock_context)

    @patch("plugins.{service}.{module}.parallel_collect")
    def test_run_with_errors(self, mock_parallel, mock_context):
        """부분 실패"""
        from plugins.{service}.{module} import run

        mock_result = MagicMock()
        mock_result.get_data.return_value = [MagicMock()]
        mock_result.error_count = 2
        mock_parallel.return_value = mock_result

        # Should complete even with some errors
        run(mock_context)


# =============================================================================
# moto 기반 통합 테스트 (선택적)
# =============================================================================

@pytest.mark.skipif(not HAS_MOTO, reason="moto not installed")
class TestWithMoto:
    """moto를 사용한 AWS 모킹 테스트"""

    def test_collect_with_moto(self, moto_{aws_service}):
        """실제 AWS API 모킹 테스트"""
        # moto로 실제 리소스 생성 후 테스트
        pass
```

### 4. fixture 확인

테스트에서 사용하는 fixture 확인 (`tests/conftest.py`):
- `mock_context`: ExecutionContext 모킹
- `mock_provider`: Provider 모킹
- `mock_boto3_session`: boto3.Session 모킹
- `mock_ec2_client`: EC2 클라이언트 모킹
- `moto_ec2`: moto 기반 EC2 모킹
- `moto_s3`: moto 기반 S3 모킹
- `moto_iam`: moto 기반 IAM 모킹

필요한 fixture가 conftest.py에 없으면 추가 안내.

### 5. 디렉토리 생성

`tests/plugins/{service}/` 디렉토리가 없으면 생성.
`__init__.py` 파일이 없으면 빈 파일 생성.

### 6. 파일 작성 및 검증

생성된 테스트 파일이 문법적으로 올바른지 확인:
```bash
python -m py_compile tests/plugins/{service}/test_{module}.py
```

## 출력 예시

```
/make-test efs/unused 실행 중...

[분석] plugins/efs/unused.py
  - run() 함수: 있음
  - collect 함수: collect_efs_filesystems
  - analyze 함수: analyze_filesystems
  - AWS 서비스: efs, cloudwatch
  - 데이터클래스: EFSInfo, EFSFinding, EFSAnalysisResult

[생성] tests/plugins/efs/test_unused.py
  - TestCollectEfsFilesystems (3개 테스트)
  - TestAnalyzeFilesystems (2개 테스트)
  - TestRun (3개 테스트)
  - TestWithMoto (1개 테스트)

[검증] 문법 검사 통과

완료! 생성된 테스트 파일:
  tests/plugins/efs/test_unused.py

실행 방법:
  pytest tests/plugins/efs/test_unused.py -v
```

## 참조 파일

- `tests/conftest.py` - 공통 fixture 정의
- `.claude/skills/tdd-workflow.md` - TDD 가이드
- `.claude/skills/python-best-practices.md` - 코딩 스타일

## 주의사항

1. **기존 파일 덮어쓰기 금지**: 테스트 파일이 이미 존재하면 확인 요청
2. **import 경로 확인**: 프로젝트 루트 기준 import 사용
3. **moto 호환성**: moto가 지원하지 않는 서비스는 MagicMock 사용
4. **fixture 활용**: conftest.py의 fixture 최대한 활용
