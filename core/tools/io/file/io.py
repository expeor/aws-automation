"""
pkg/io/file/io.py - 파일 I/O 유틸리티
"""

import json
from pathlib import Path
from typing import Any


def ensure_dir(path: str | Path) -> Path:
    """디렉토리 존재 확인 및 생성

    Args:
        path: 디렉토리 경로

    Returns:
        생성된 경로 객체
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_file(
    filepath: str | Path,
    encoding: str = "utf-8",
) -> str | None:
    """파일 읽기

    Args:
        filepath: 파일 경로
        encoding: 인코딩 (기본값: utf-8)

    Returns:
        파일 내용 (실패시 None)
    """
    try:
        filepath = Path(filepath)
        return filepath.read_text(encoding=encoding)
    except Exception:
        return None


def write_file(
    filepath: str | Path,
    content: str,
    encoding: str = "utf-8",
) -> bool:
    """파일 쓰기

    Args:
        filepath: 파일 경로
        content: 작성할 내용
        encoding: 인코딩 (기본값: utf-8)

    Returns:
        True if 성공
    """
    try:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding=encoding)
        return True
    except Exception:
        return False


def read_json(filepath: str | Path) -> Any | None:
    """JSON 파일 읽기

    Args:
        filepath: 파일 경로

    Returns:
        파싱된 JSON 데이터 (실패시 None)
    """
    try:
        content = read_file(filepath)
        if content:
            return json.loads(content)
        return None
    except Exception:
        return None


def write_json(
    filepath: str | Path,
    data: Any,
    indent: int = 2,
) -> bool:
    """JSON 파일 쓰기

    Args:
        filepath: 파일 경로
        data: 저장할 데이터
        indent: 들여쓰기 (기본값: 2)

    Returns:
        True if 성공
    """
    try:
        content = json.dumps(data, ensure_ascii=False, indent=indent)
        return write_file(filepath, content)
    except Exception:
        return False
