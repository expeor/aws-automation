"""
pkg/io/csv/handler.py - 크로스 플랫폼 CSV 파일 처리 유틸리티

Windows, macOS, Linux에서 다양한 인코딩으로 저장된 CSV 파일을
안전하게 읽을 수 있는 견고한 함수들을 제공합니다.
"""

import csv
import logging
import platform
from pathlib import Path
from typing import Any

try:
    import chardet

    CHARDET_AVAILABLE = True
except ImportError:
    chardet = None  # type: ignore[assignment]  # Optional dependency
    CHARDET_AVAILABLE = False

logger = logging.getLogger(__name__)

# 플랫폼별 인코딩 우선순위 정의
ENCODING_PRIORITIES = [
    "utf-8-sig",  # Windows Excel BOM 포함 UTF-8
    "utf-8",  # macOS/Linux 기본, Windows 최신
    "cp949",  # 한국어 Windows (EUC-KR 확장)
    "euc-kr",  # 한국어 구형 시스템
    "latin-1",  # ISO-8859-1, fallback (거의 모든 바이트 읽기 가능)
]


def detect_csv_encoding(file_path: str) -> tuple[str | None, str | None]:
    """CSV 파일의 인코딩을 자동 감지합니다.

    chardet 라이브러리를 우선 사용하고, 실패시 폴백 방식으로 순차 시도합니다.

    Args:
        file_path: CSV 파일 경로

    Returns:
        Tuple[Optional[str], Optional[str]]: (감지된_인코딩, 오류_메시지)
        성공시 (인코딩, None), 실패시 (None, 오류_메시지)
    """
    path = Path(file_path)

    if not path.exists():
        return None, f"파일을 찾을 수 없습니다: {file_path}"

    if not path.is_file():
        return None, f"경로가 파일이 아닙니다: {file_path}"

    # 1단계: chardet을 사용한 인코딩 자동 감지 (권장 방법)
    if CHARDET_AVAILABLE:
        try:
            # 파일의 충분한 부분을 읽어서 정확한 감지
            with open(file_path, "rb") as f:
                raw_data = f.read(10240)  # 10KB 읽기 (더 정확한 감지를 위해)

            if raw_data:
                detected = chardet.detect(raw_data)
                if detected and detected.get("confidence", 0) > 0.7:
                    detected_encoding = detected["encoding"]

                    # 감지된 인코딩으로 CSV 파싱 테스트
                    try:
                        with open(file_path, encoding=detected_encoding) as f:
                            sample = f.read(1024)
                            if sample:
                                csv.Sniffer().sniff(sample)
                                logger.info(
                                    f"chardet으로 CSV 인코딩 감지 성공: "
                                    f"{detected_encoding} "
                                    f"(신뢰도: {detected['confidence']:.2f}) "
                                    f"for {file_path}"
                                )
                                return detected_encoding, None
                    except Exception as e:
                        logger.debug(f"chardet 감지된 인코딩 {detected_encoding} 검증 실패: {str(e)}")

        except Exception as e:
            logger.debug(f"chardet 인코딩 감지 실패: {str(e)}")

    # 2단계: 폴백 - 순차적 인코딩 시도
    logger.debug(f"chardet 감지 실패 또는 불가능, 폴백 방식 사용: {file_path}")

    for encoding in ENCODING_PRIORITIES:
        try:
            with open(file_path, encoding=encoding) as f:
                # 파일 시작 부분을 읽어서 올바른 CSV인지 확인
                sample = f.read(1024)
                if sample:
                    # CSV로 파싱 시도
                    csv.Sniffer().sniff(sample)
                    logger.info(f"폴백 방식으로 CSV 인코딩 감지: {encoding} for {file_path}")
                    return encoding, None
        except (UnicodeDecodeError, UnicodeError):
            logger.debug(f"인코딩 실패: {encoding} for {file_path}")
            continue
        except csv.Error:
            logger.debug(f"CSV 형식 오류: {encoding} for {file_path}")
            continue
        except Exception as e:
            logger.debug(f"예상치 못한 오류: {encoding} for {file_path}: {str(e)}")
            continue

    return None, f"지원하는 인코딩으로 파일을 읽을 수 없습니다: {file_path}"


def read_csv_robust(
    file_path: str,
    encoding: str | None = None,
) -> tuple[list[dict[str, Any]] | None, str | None, str | None]:
    """CSV 파일 읽기 함수.

    여러 인코딩을 시도하여 크로스 플랫폼 호환성을 보장합니다.

    Args:
        file_path: CSV 파일 경로
        encoding: 특정 인코딩 지정 (None이면 자동 감지)

    Returns:
        Tuple[Optional[List[Dict]], Optional[str], Optional[str]]:
        (데이터, 사용된_인코딩, 오류_메시지)
        성공시 (데이터, 인코딩, None), 실패시 (None, None, 오류_메시지)
    """

    # 특정 인코딩이 지정된 경우 해당 인코딩만 사용
    if encoding:
        encodings_to_try = [encoding]
    else:
        # 자동 감지 시도
        detected_encoding, error = detect_csv_encoding(file_path)
        # 감지 성공 시 해당 인코딩만 사용, 실패 시 모든 인코딩 시도
        encodings_to_try = [detected_encoding] if detected_encoding else ENCODING_PRIORITIES

    last_error = None

    for enc in encodings_to_try:
        try:
            data = []
            with open(file_path, encoding=enc) as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames

                if not headers:
                    last_error = f"CSV 헤더를 찾을 수 없습니다 (인코딩: {enc})"
                    continue

                for row_num, row in enumerate(reader, start=1):
                    try:
                        # 빈 문자열을 None으로 변환하고 공백 제거
                        cleaned_row = {k: v.strip() if v and v.strip() else None for k, v in row.items()}
                        data.append(cleaned_row)
                    except Exception as row_error:
                        logger.warning(f"행 {row_num} 처리 중 오류 (인코딩: {enc}): {str(row_error)}")
                        continue

                logger.info(f"CSV 파일 읽기 성공: {file_path} (인코딩: {enc}, {len(data)}행)")
                return data, enc, None

        except (UnicodeDecodeError, UnicodeError) as e:
            last_error = f"인코딩 오류 ({enc}): {str(e)}"
            logger.debug(last_error)
            continue
        except csv.Error as e:
            last_error = f"CSV 형식 오류 ({enc}): {str(e)}"
            logger.debug(last_error)
            continue
        except FileNotFoundError:
            return None, None, f"파일을 찾을 수 없습니다: {file_path}"
        except PermissionError:
            return None, None, f"파일 접근 권한이 없습니다: {file_path}"
        except Exception as e:
            last_error = f"예상치 못한 오류 ({enc}): {str(e)}"
            logger.debug(last_error)
            continue

    return None, None, f"모든 인코딩 시도 실패: {last_error}"


def validate_csv_headers(
    file_path: str,
    required_headers: list[str],
    encoding: str | None = None,
) -> tuple[bool, str, str | None]:
    """CSV 파일의 헤더가 요구사항을 만족하는지 검증합니다.

    Args:
        file_path: CSV 파일 경로
        required_headers: 필수 헤더 목록
        encoding: 특정 인코딩 지정 (None이면 자동 감지)

    Returns:
        Tuple[bool, str, Optional[str]]: (성공여부, 메시지, 사용된_인코딩)
    """

    data, used_encoding, error = read_csv_robust(file_path, encoding)

    if error:
        return False, f"CSV 파일 읽기 실패: {error}", None

    if not data:
        return False, "CSV 파일이 비어있습니다", used_encoding

    # 첫 번째 행에서 헤더 추출
    actual_headers = list(data[0].keys()) if data else []

    missing_headers = [h for h in required_headers if h not in actual_headers]

    if missing_headers:
        return (
            False,
            f"필수 컬럼이 누락되었습니다: {', '.join(missing_headers)}",
            used_encoding,
        )

    return True, f"CSV 검증 성공 (인코딩: {used_encoding})", used_encoding


def get_platform_recommended_encoding() -> str:
    """현재 플랫폼에서 권장하는 기본 인코딩을 반환합니다."""
    system = platform.system().lower()

    if system == "windows":
        return "utf-8-sig"  # Windows Excel 호환성
    elif system in ["darwin", "linux"]:
        return "utf-8"  # Unix 계열 기본
    else:
        return "utf-8-sig"  # 기본값
