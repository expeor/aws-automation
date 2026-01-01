"""
core/exceptions.py - 통합 예외 계층 구조

애플리케이션 전체에서 사용되는 예외 클래스들을 정의합니다.
일관된 예외 처리와 에러 메시지를 제공합니다.

예외 계층 구조:
    AAError (베이스)
    ├── AuthError (인증 관련) - core.auth.types에서 재정의
    │   ├── NotAuthenticatedError
    │   ├── TokenExpiredError
    │   ├── AccountNotFoundError
    │   ├── ConfigurationError
    │   └── ProviderError
    ├── DiscoveryError (플러그인 발견)
    │   ├── PluginLoadError
    │   └── MetadataValidationError
    ├── ToolExecutionError (도구 실행)
    │   ├── SessionError
    │   └── APICallError
    ├── FlowError (UI 플로우)
    │   ├── StepError
    │   └── UserCancelError
    └── ConfigError (설정 관련)

Usage:
    from core.exceptions import ToolExecutionError, APICallError

    try:
        result = ec2.describe_instances()
    except ClientError as e:
        raise APICallError(
            service="ec2",
            operation="describe_instances",
            cause=e
        )
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

# =============================================================================
# 베이스 예외
# =============================================================================


class AAError(Exception):
    """AWS Automation 기본 예외 클래스

    모든 커스텀 예외의 베이스 클래스입니다.

    Attributes:
        message: 에러 메시지
        cause: 원인 예외 (체이닝용)
        details: 추가 상세 정보
    """

    def __init__(
        self,
        message: str,
        cause: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.details = details or {}

    def __str__(self) -> str:
        if self.cause:
            return f"{self.message}: {self.cause}"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """예외 정보를 딕셔너리로 반환"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "cause": str(self.cause) if self.cause else None,
            "details": self.details,
        }


# =============================================================================
# 플러그인 발견 관련 예외
# =============================================================================


class DiscoveryError(AAError):
    """플러그인 발견 관련 예외"""

    def __init__(
        self,
        message: str,
        plugin_path: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, cause)
        self.plugin_path = plugin_path
        if plugin_path:
            self.details["plugin_path"] = plugin_path


class PluginLoadError(DiscoveryError):
    """플러그인 로드 실패 예외"""

    def __init__(
        self,
        plugin_name: str,
        reason: str,
        cause: Optional[Exception] = None,
    ):
        message = f"플러그인 로드 실패 [{plugin_name}]: {reason}"
        super().__init__(message, plugin_path=plugin_name, cause=cause)
        self.plugin_name = plugin_name
        self.reason = reason


class MetadataValidationError(DiscoveryError):
    """플러그인 메타데이터 검증 실패 예외"""

    def __init__(
        self,
        plugin_name: str,
        errors: List[str],
        cause: Optional[Exception] = None,
    ):
        message = f"메타데이터 검증 실패 [{plugin_name}]: {', '.join(errors)}"
        super().__init__(message, plugin_path=plugin_name, cause=cause)
        self.plugin_name = plugin_name
        self.validation_errors = errors
        self.details["validation_errors"] = errors


# =============================================================================
# 도구 실행 관련 예외
# =============================================================================


class ToolExecutionError(AAError):
    """도구 실행 관련 예외"""

    def __init__(
        self,
        tool_name: str,
        message: str,
        cause: Optional[Exception] = None,
    ):
        full_message = f"도구 실행 오류 [{tool_name}]: {message}"
        super().__init__(full_message, cause)
        self.tool_name = tool_name
        self.details["tool_name"] = tool_name


class SessionError(ToolExecutionError):
    """세션 생성/관리 관련 예외"""

    def __init__(
        self,
        identifier: str,  # account_id or profile_name
        region: str,
        message: str,
        cause: Optional[Exception] = None,
    ):
        full_message = f"세션 오류 [{identifier}/{region}]: {message}"
        super().__init__(tool_name="session", message=full_message, cause=cause)
        self.identifier = identifier
        self.region = region
        self.details["identifier"] = identifier
        self.details["region"] = region


class APICallError(ToolExecutionError):
    """AWS API 호출 관련 예외

    boto3/botocore의 ClientError를 래핑하여 일관된 예외 처리를 제공합니다.
    """

    def __init__(
        self,
        service: str,
        operation: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        message = f"{service}.{operation}"
        if error_code:
            message = f"{message} 실패 ({error_code})"
        if error_message:
            message = f"{message}: {error_message}"

        super().__init__(tool_name=service, message=message, cause=cause)
        self.service = service
        self.operation = operation
        self.error_code = error_code
        self.error_message = error_message
        self.details.update(
            {
                "service": service,
                "operation": operation,
                "error_code": error_code,
            }
        )

    @classmethod
    def from_client_error(
        cls,
        service: str,
        operation: str,
        client_error: Exception,
    ) -> "APICallError":
        """botocore.exceptions.ClientError로부터 생성

        Args:
            service: AWS 서비스 이름
            operation: API 작업 이름
            client_error: ClientError 예외

        Returns:
            APICallError 인스턴스
        """
        error_code = None
        error_message = None

        # ClientError 형식 파싱
        if hasattr(client_error, "response"):
            error_info = client_error.response.get("Error", {})
            error_code = error_info.get("Code")
            error_message = error_info.get("Message")

        return cls(
            service=service,
            operation=operation,
            error_code=error_code,
            error_message=error_message,
            cause=client_error,
        )


# =============================================================================
# UI 플로우 관련 예외
# =============================================================================


class FlowError(AAError):
    """UI 플로우 관련 예외"""

    def __init__(
        self,
        step_name: str,
        message: str,
        cause: Optional[Exception] = None,
    ):
        full_message = f"플로우 오류 [{step_name}]: {message}"
        super().__init__(full_message, cause)
        self.step_name = step_name
        self.details["step_name"] = step_name


class StepError(FlowError):
    """플로우 단계 실행 오류"""

    pass


class UserCancelError(FlowError):
    """사용자가 작업을 취소한 경우"""

    def __init__(self, step_name: str = "unknown"):
        super().__init__(step_name, "사용자가 취소했습니다")


class BackToMenuError(FlowError):
    """이전 메뉴로 돌아가기 요청

    예외를 통한 플로우 제어용.
    FlowRunner에서 이 예외를 캐치하여 이전 단계로 이동합니다.
    """

    def __init__(self, step_name: str = "unknown"):
        super().__init__(step_name, "이전 메뉴로 돌아가기")


# =============================================================================
# 설정 관련 예외
# =============================================================================


class ConfigError(AAError):
    """설정 관련 예외"""

    def __init__(
        self,
        key: str,
        message: str,
        cause: Optional[Exception] = None,
    ):
        full_message = f"설정 오류 [{key}]: {message}"
        super().__init__(full_message, cause)
        self.config_key = key
        self.details["config_key"] = key


class ValidationError(AAError):
    """입력 검증 오류"""

    def __init__(
        self,
        field: str,
        value: Any,
        expected: str,
        cause: Optional[Exception] = None,
    ):
        message = f"검증 오류 [{field}]: 예상값 '{expected}', 실제값 '{value}'"
        super().__init__(message, cause)
        self.field = field
        self.value = value
        self.expected = expected
        self.details.update(
            {
                "field": field,
                "value": str(value),
                "expected": expected,
            }
        )


# =============================================================================
# 예외 유틸리티 함수
# =============================================================================


def is_access_denied(error: Exception) -> bool:
    """액세스 거부 오류인지 확인

    Args:
        error: 확인할 예외

    Returns:
        액세스 거부 오류이면 True
    """
    if isinstance(error, APICallError):
        return error.error_code in (
            "AccessDenied",
            "AccessDeniedException",
            "UnauthorizedAccess",
        )

    # botocore ClientError 직접 확인
    if hasattr(error, "response"):
        error_code = error.response.get("Error", {}).get("Code", "")
        return error_code in (
            "AccessDenied",
            "AccessDeniedException",
            "UnauthorizedAccess",
        )

    return False


def is_throttling(error: Exception) -> bool:
    """스로틀링 오류인지 확인

    Args:
        error: 확인할 예외

    Returns:
        스로틀링 오류이면 True
    """
    throttling_codes = {
        "Throttling",
        "ThrottlingException",
        "RequestLimitExceeded",
        "TooManyRequestsException",
        "RateExceeded",
    }

    if isinstance(error, APICallError):
        return error.error_code in throttling_codes

    if hasattr(error, "response"):
        error_code = error.response.get("Error", {}).get("Code", "")
        return error_code in throttling_codes

    return False


def is_not_found(error: Exception) -> bool:
    """리소스를 찾을 수 없는 오류인지 확인

    Args:
        error: 확인할 예외

    Returns:
        리소스 없음 오류이면 True
    """
    not_found_codes = {
        "ResourceNotFoundException",
        "NotFoundException",
        "NoSuchEntity",
        "NoSuchBucket",
        "InvalidInstanceID.NotFound",
    }

    if isinstance(error, APICallError):
        return error.error_code in not_found_codes

    if hasattr(error, "response"):
        error_code = error.response.get("Error", {}).get("Code", "")
        return error_code in not_found_codes

    return False
