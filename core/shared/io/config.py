"""출력 설정 모듈

리포트 출력 형식 및 옵션 설정

Usage:
    from core.shared.io.config import OutputConfig, OutputFormat

    config = OutputConfig(
        formats=OutputFormat.ALL,  # Excel + HTML
        auto_open=True,
        lang="ko",
    )

    if OutputFormat.EXCEL in config.formats:
        # Excel 출력
        pass

    if OutputFormat.HTML in config.formats:
        # HTML 출력
        pass
"""

from dataclasses import dataclass, field
from enum import Flag, auto


class OutputFormat(Flag):
    """출력 형식 플래그

    Flag 타입으로 여러 형식을 조합하여 사용 가능

    Usage:
        # 단일 형식
        fmt = OutputFormat.EXCEL

        # 복수 형식
        fmt = OutputFormat.EXCEL | OutputFormat.HTML

        # 형식 포함 여부 확인
        if OutputFormat.EXCEL in fmt:
            ...

        # 모든 형식 (Excel + HTML)
        fmt = OutputFormat.ALL
    """

    NONE = 0
    EXCEL = auto()
    HTML = auto()
    CONSOLE = auto()
    JSON = auto()
    CSV = auto()
    ALL = EXCEL | HTML  # 기본값: Excel + HTML


@dataclass
class OutputConfig:
    """출력 설정

    Attributes:
        formats: 출력 형식 플래그 (OutputFormat.ALL = Excel + HTML)
        output_dir: 출력 디렉토리 (None이면 자동 생성)
        auto_open: 저장 후 자동 열기 (Explorer/Browser)
        lang: 언어 설정 ("ko" 또는 "en")
    """

    formats: OutputFormat = field(default=OutputFormat.ALL)
    output_dir: str | None = None
    auto_open: bool = True
    lang: str = "ko"

    def should_output_excel(self) -> bool:
        """Excel 출력 여부"""
        return OutputFormat.EXCEL in self.formats

    def should_output_html(self) -> bool:
        """HTML 출력 여부"""
        return OutputFormat.HTML in self.formats

    def should_output_console(self) -> bool:
        """Console 출력 여부"""
        return OutputFormat.CONSOLE in self.formats

    def should_output_json(self) -> bool:
        """JSON 출력 여부"""
        return OutputFormat.JSON in self.formats

    def should_output_csv(self) -> bool:
        """CSV 출력 여부"""
        return OutputFormat.CSV in self.formats

    @classmethod
    def from_string(cls, format_str: str) -> "OutputConfig":
        """문자열에서 OutputConfig 생성

        Args:
            format_str: 형식 문자열 ("excel", "html", "both", "console", "json", "csv")

        Returns:
            OutputConfig 인스턴스
        """
        format_map = {
            "excel": OutputFormat.EXCEL,
            "html": OutputFormat.HTML,
            "both": OutputFormat.ALL,
            "console": OutputFormat.CONSOLE,
            "json": OutputFormat.JSON,
            "csv": OutputFormat.CSV,
        }

        formats = format_map.get(format_str.lower(), OutputFormat.ALL)
        return cls(formats=formats)
