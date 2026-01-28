"""
reports/log_analyzer - ALB 로그 분석 핵심 모듈

모듈:
    alb_log_analyzer.py     - DuckDB 기반 분석기
    alb_log_downloader.py   - S3 로그 다운로드
    alb_excel_reporter.py   - Excel 보고서 생성
    ip_intelligence.py      - IP 인텔리전스 (국가 매핑 + 악성 IP)
"""

CATEGORY = {
    "name": "log_analyzer",
    "display_name": "Log Analyzer",
    "description": "ALB/NLB 로그 분석",
    "description_en": "ALB/NLB Log Analysis",
    "aliases": ["log", "alb_log", "access_log"],
}

TOOLS: list[dict] = [
    # ALB 로그 분석 도구는 analyzers/elb/alb_log.py에서 정의됨
    # reports/__init__.py에서 ref로 참조하므로 중복 제거
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
