"""functions/reports/log_analyzer/__init__.py - ALB 로그 분석 패키지.

S3에 저장된 ALB 액세스 로그를 DuckDB 기반으로 초고속 분석하고
종합 Excel 보고서를 생성합니다.

모듈:
    - alb_log_analyzer.py: DuckDB 기반 SQL 분석기 (로그 파싱, 통계 산출).
    - alb_log_downloader.py: S3 로그 다운로드 (병렬 다운로드, 압축 해제).
    - alb_excel_reporter.py: Excel 보고서 생성 (요약, 상태코드, 응답시간 등).
    - ip_intelligence.py: IP 인텔리전스 (GeoIP 국가 매핑 + AbuseIPDB 악성 IP 탐지).
    - reporter/: 시트별 Excel Writer 모듈 (summary, status_code, abuse, tps 등).
"""

CATEGORY = {
    "name": "log_analyzer",
    "display_name": "Log Analyzer",
    "description": "ALB/NLB 로그 분석",
    "description_en": "ALB/NLB Log Analysis",
    "aliases": ["log", "alb_log", "access_log"],
}

TOOLS: list[dict] = [
    {
        "name": "ALB 로그 분석",
        "name_en": "ALB Log Analysis",
        "description": "S3에 저장된 ALB 액세스 로그 분석",
        "description_en": "Analyze ALB access logs stored in S3",
        "permission": "read",
        "ref": "elb/alb_log",
        "area": "log",
        "single_region_only": True,
    },
]

from .alb_excel_reporter import ALBExcelReporter
from .alb_log_analyzer import ALBLogAnalyzer
from .alb_log_downloader import ALBLogDownloader
from .ip_intelligence import AbuseIPDBProvider, IPDenyProvider, IPIntelligence

__all__: list[str] = [
    # Discovery 메타데이터
    "CATEGORY",
    "TOOLS",
    # 분석기
    "ALBLogAnalyzer",
    "ALBExcelReporter",
    "ALBLogDownloader",
    # IP Intelligence
    "IPIntelligence",
    "IPDenyProvider",
    "AbuseIPDBProvider",
]
