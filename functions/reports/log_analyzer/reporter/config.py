"""functions/reports/log_analyzer/reporter/config.py - ALB Excel Reporter 설정 상수.

시트별 설정(SheetConfig), 시트 이름(SheetNames), 헤더 정의(Headers),
컬럼 스타일/너비 매핑, 상태 코드 타입 등의 상수를 정의합니다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SheetConfig:
    """시트 레벨 설정 상수.

    Attributes:
        EXCEL_MAX_ROWS: Excel 2007+ 최대 행 수 (1,048,576).
        EXCEL_MAX_COLS: Excel 2007+ 최대 열 수 (16,384).
        ZOOM_SCALE: 기본 확대/축소 비율 (85%).
        HEADER_ROW_HEIGHT: 헤더 행 높이 (픽셀).
        DATA_ROW_HEIGHT: 데이터 행 높이 (픽셀).
        DEFAULT_COLUMN_WIDTH: 기본 컬럼 너비.
        MAX_ROWS_PER_SHEET: 시트당 최대 데이터 행 수.
        BATCH_SIZE: 배치 처리 단위 행 수.
        TOP_URL_LIMIT: URL Top N 제한.
        TOP_COUNTRY_LIMIT: 국가별 Top N 제한.
        TOP_RESPONSE_TIME_LIMIT: 응답 시간 Top N 제한.
        TOP_BYTES_LIMIT: 데이터 전송량 Top N 제한.
        TOP_CLIENT_LIMIT: 클라이언트 Top N 제한.
        SUMMARY_TOP_ITEMS: 요약 시트 Top N 항목 수.
        SECURITY_EVENTS_LIMIT: 보안 이벤트 최대 행 수.
    """

    # Excel 2007+ (.xlsx) limits: 1,048,576 rows, 16,384 columns
    # Excel 97-2003 (.xls) limits: 65,536 rows, 256 columns
    EXCEL_MAX_ROWS: int = 1_048_576
    EXCEL_MAX_COLS: int = 16_384

    ZOOM_SCALE: int = 85
    HEADER_ROW_HEIGHT: int = 40
    DATA_ROW_HEIGHT: int = 20
    DEFAULT_COLUMN_WIDTH: int = 15

    # Max data rows per sheet (Excel max - 1 for header row)
    MAX_ROWS_PER_SHEET: int = EXCEL_MAX_ROWS - 1  # 1,048,575

    BATCH_SIZE: int = 10_000
    TOP_URL_LIMIT: int = 100
    TOP_COUNTRY_LIMIT: int = 50
    TOP_RESPONSE_TIME_LIMIT: int = 100
    TOP_BYTES_LIMIT: int = 100
    TOP_CLIENT_LIMIT: int = 100
    SUMMARY_TOP_ITEMS: int = 5

    # Security events limit (no artificial limit, but respect Excel max)
    SECURITY_EVENTS_LIMIT: int = MAX_ROWS_PER_SHEET


# Column style types
STYLE_NUMBER = "number"
STYLE_DECIMAL = "decimal"
STYLE_DECIMAL3 = "decimal3"
STYLE_STATUS = "status"
STYLE_CENTER = "center"
STYLE_DATA = "data"

COLUMN_STYLE_MAP: dict[str, str] = {
    "Count": STYLE_NUMBER,
    "Unique IPs": STYLE_NUMBER,
    "IP Count": STYLE_NUMBER,
    "Percentage": STYLE_DECIMAL,
    "Avg Response Time": STYLE_DECIMAL3,
    "Error Rate (%)": STYLE_DECIMAL,
    "Top Status": STYLE_STATUS,
    "ELB Status Code": STYLE_STATUS,
    "Backend Status Code": STYLE_STATUS,
    "Client": STYLE_CENTER,
    "Country": STYLE_CENTER,
    "Abuse": STYLE_CENTER,
    "Method": STYLE_CENTER,
    "Target": STYLE_CENTER,
    "Target group name": STYLE_CENTER,
    "Timestamp": STYLE_CENTER,
    "Error Reason": STYLE_CENTER,
    "Request": STYLE_DATA,
    "Redirect URL": STYLE_DATA,
    "User Agent": STYLE_DATA,
    "Request Processing": STYLE_DECIMAL3,
    "Target Processing": STYLE_DECIMAL3,
    "Response Processing": STYLE_DECIMAL3,
    "Classification": STYLE_CENTER,
    "Reason": STYLE_CENTER,
}

COLUMN_WIDTH_MAP: dict[str, int] = {
    "Count": 11,
    "Client": 20,
    "Country": 10,
    "Abuse": 10,
    "Method": 9,
    "Request": 80,
    "Redirect URL": 60,
    "User Agent": 80,
    "Target": 20,
    "Target group name": 20,
    "Timestamp": 22,
    "ELB Status Code": 12,
    "Backend Status Code": 12,
    "Unique IPs": 12,
    "Avg Response Time": 15,
    "Top Status": 12,
    "Error Rate (%)": 12,
    "IP Count": 15,
    "Percentage": 15,
    "ASN": 15,
    "ISP": 40,
    "IP": 20,
    "Error Reason": 40,
    "Response time": 15,
    "Request Processing": 18,
    "Target Processing": 18,
    "Response Processing": 18,
    "Classification": 16,
    "Reason": 45,
    "수신 데이터 (Bytes)": 20,
    "송신 데이터 (Bytes)": 20,
    "총 데이터 (Bytes)": 20,
    "총 데이터 (변환)": 25,
}

WRAP_TEXT_COLUMNS: dict[str, str] = {
    "Request": "left",
    "Redirect URL": "left",
    "User Agent": "left",
    "Client": "center",
    "Target": "center",
    "Target group name": "center",
    "Country": "center",
}


@dataclass(frozen=True)
class SheetNames:
    """Excel 보고서 시트 이름 상수.

    Attributes:
        SUMMARY: 분석 요약 시트 이름.
        COUNTRY_STATS: 국가별 통계 시트 이름.
        URL_TOP100: 요청 URL Top 100 시트 이름.
        CLIENT_STATUS: Client 상태코드 통계 시트 이름.
        TARGET_STATUS: Target 상태코드 통계 시트 이름.
        RESPONSE_TIME: 응답 시간 Top 100 시트 이름.
        BYTES_ANALYSIS: 데이터 전송량 Top 100 시트 이름.
        ABUSE_IP_LIST: 악성 IP 목록 시트 이름.
        ABUSE_REQUESTS: 보안 이벤트 시트 이름.
    """

    SUMMARY: str = "분석 요약"
    COUNTRY_STATS: str = "국가별 통계"
    URL_TOP100: str = "요청 URL Top 100"
    CLIENT_STATUS: str = "Client 상태코드 통계 Top 100"
    TARGET_STATUS: str = "Target 상태코드 통계"
    RESPONSE_TIME: str = "응답 시간 Top 100"
    BYTES_ANALYSIS: str = "데이터 전송량 Top 100"
    ABUSE_IP_LIST: str = "악성 IP 목록"
    ABUSE_REQUESTS: str = "보안 이벤트"
    ELB_2XX: str = "ELB 2xx Top 100"
    ELB_3XX: str = "ELB 3xx Top 100"
    ELB_4XX_COUNT: str = "ELB 4xx Count"
    ELB_5XX_COUNT: str = "ELB 5xx Count"
    BACKEND_4XX_COUNT: str = "Backend 4xx Count"
    BACKEND_5XX_COUNT: str = "Backend 5xx Count"
    ELB_4XX_TS: str = "ELB 4xx Timestamp"
    ELB_5XX_TS: str = "ELB 5xx Timestamp"
    BACKEND_4XX_TS: str = "Backend 4xx Timestamp"
    BACKEND_5XX_TS: str = "Backend 5xx Timestamp"


SHEET_NAMES = SheetNames()


@dataclass(frozen=True)
class Headers:
    """시트별 헤더 컬럼 정의.

    Attributes:
        ABUSE_IP: 악성 IP 목록 시트 헤더.
        ABUSE_REQUESTS: 보안 이벤트 시트 헤더.
        RESPONSE_TIME: 응답 시간 시트 헤더.
        BYTES_ANALYSIS: 데이터 전송량 시트 헤더.
        STATUS_COUNT_BASE: 상태코드 Count 시트 기본 헤더.
        STATUS_COUNT_3XX: 3xx 상태코드 시트 헤더 (Redirect URL 포함).
        STATUS_TIMESTAMP: 상태코드 Timestamp 시트 헤더.
        COUNTRY_STATS: 국가별 통계 시트 헤더.
        URL_DETAILED: URL 상세 분석 시트 헤더.
        URL_SIMPLE: URL 간략 시트 헤더.
    """

    ABUSE_IP: tuple[str, ...] = ("Count", "IP", "Country", "ASN", "ISP")

    ABUSE_REQUESTS: tuple[str, ...] = (
        "Timestamp",
        "Client",
        "Country",
        "Classification",
        "Reason",
        "Target",
        "Target group name",
        "Method",
        "Request",
        "User Agent",
        "ELB Status Code",
        "Backend Status Code",
    )

    RESPONSE_TIME: tuple[str, ...] = (
        "Response time",
        "Request Processing",
        "Target Processing",
        "Response Processing",
        "Timestamp",
        "Client",
        "Country",
        "Target",
        "Target group name",
        "Method",
        "Request",
        "User Agent",
        "ELB Status Code",
        "Backend Status Code",
    )

    BYTES_ANALYSIS: tuple[str, ...] = (
        "Request",
        "수신 데이터 (Bytes)",
        "송신 데이터 (Bytes)",
        "총 데이터 (Bytes)",
        "총 데이터 (변환)",
    )

    STATUS_COUNT_BASE: tuple[str, ...] = (
        "Count",
        "Client",
        "Country",
        "Target",
        "Target group name",
        "Method",
        "Request",
        "ELB Status Code",
        "Backend Status Code",
    )

    STATUS_COUNT_3XX: tuple[str, ...] = (
        "Count",
        "Client",
        "Country",
        "Target",
        "Target group name",
        "Method",
        "Request",
        "Redirect URL",
        "ELB Status Code",
        "Backend Status Code",
    )

    STATUS_TIMESTAMP: tuple[str, ...] = (
        "Timestamp",
        "Client",
        "Country",
        "Target",
        "Target group name",
        "Method",
        "Request",
        "User Agent",
        "ELB Status Code",
        "Backend Status Code",
        "Error Reason",
    )

    COUNTRY_STATS: tuple[str, ...] = ("Count", "Country", "IP Count", "Percentage")

    URL_DETAILED: tuple[str, ...] = (
        "Count",
        "Client",
        "Country",
        "Method",
        "Request",
        "Unique IPs",
        "Avg Response Time",
        "Top Status",
        "Error Rate (%)",
    )

    URL_SIMPLE: tuple[str, ...] = ("Count", "Request")


HEADERS = Headers()

STATUS_CODE_TYPES: tuple[str, ...] = (
    "ELB 2xx Count",
    "ELB 3xx Count",
    "ELB 4xx Count",
    "ELB 5xx Count",
    "Backend 4xx Count",
    "Backend 5xx Count",
)

SPECIAL_COUNTRY_CODES: frozenset[str] = frozenset({"UNKNOWN", "PRIVATE", "LOOPBACK", "LINK_LOCAL", "MULTICAST"})
