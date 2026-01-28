"""
tests/shared/io/file/test_io.py - 파일 I/O 유틸리티 테스트
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from shared.io.file.io import ensure_dir, read_file, read_json, write_file, write_json


class TestEnsureDir:
    """디렉토리 생성 테스트"""

    def test_create_new_directory(self):
        """새 디렉토리 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "test_dir"

            result = ensure_dir(new_dir)

            assert result.exists()
            assert result.is_dir()
            assert result == new_dir

    def test_create_nested_directories(self):
        """중첩 디렉토리 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "level1" / "level2" / "level3"

            result = ensure_dir(nested_dir)

            assert result.exists()
            assert result.is_dir()
            assert (Path(tmpdir) / "level1").exists()
            assert (Path(tmpdir) / "level1" / "level2").exists()

    def test_directory_already_exists(self):
        """이미 존재하는 디렉토리"""
        with tempfile.TemporaryDirectory() as tmpdir:
            existing_dir = Path(tmpdir)

            result = ensure_dir(existing_dir)

            assert result.exists()
            assert result.is_dir()

    def test_with_string_path(self):
        """문자열 경로"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = str(Path(tmpdir) / "string_dir")

            result = ensure_dir(new_dir)

            assert result.exists()
            assert result.is_dir()
            assert isinstance(result, Path)

    def test_with_path_object(self):
        """Path 객체"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "path_dir"

            result = ensure_dir(new_dir)

            assert result.exists()
            assert result.is_dir()

    def test_parent_directories_created(self):
        """부모 디렉토리 자동 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            deep_dir = Path(tmpdir) / "a" / "b" / "c" / "d"

            result = ensure_dir(deep_dir)

            assert (Path(tmpdir) / "a").exists()
            assert (Path(tmpdir) / "a" / "b").exists()
            assert (Path(tmpdir) / "a" / "b" / "c").exists()
            assert result.exists()


class TestReadFile:
    """파일 읽기 테스트"""

    def test_read_simple_file(self):
        """간단한 텍스트 파일 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write("Hello, World!\n")
            f.write("This is a test.\n")
            temp_path = f.name

        try:
            content = read_file(temp_path)

            assert content is not None
            assert "Hello, World!" in content
            assert "This is a test." in content
        finally:
            Path(temp_path).unlink()

    def test_read_empty_file(self):
        """빈 파일 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            temp_path = f.name

        try:
            content = read_file(temp_path)

            assert content == ""
        finally:
            Path(temp_path).unlink()

    def test_read_unicode_content(self):
        """유니코드 내용 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write("안녕하세요\n")
            f.write("こんにちは\n")
            f.write("你好\n")
            temp_path = f.name

        try:
            content = read_file(temp_path)

            assert content is not None
            assert "안녕하세요" in content
            assert "こんにちは" in content
            assert "你好" in content
        finally:
            Path(temp_path).unlink()

    def test_read_with_custom_encoding(self):
        """커스텀 인코딩으로 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="latin-1", delete=False) as f:
            f.write("Test content")
            temp_path = f.name

        try:
            content = read_file(temp_path, encoding="latin-1")

            assert content is not None
            assert "Test content" in content
        finally:
            Path(temp_path).unlink()

    def test_read_nonexistent_file(self):
        """존재하지 않는 파일 읽기"""
        content = read_file("/nonexistent/file.txt")

        assert content is None

    def test_read_with_string_path(self):
        """문자열 경로로 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write("String path test")
            temp_path = f.name

        try:
            content = read_file(temp_path)

            assert content is not None
            assert "String path test" in content
        finally:
            Path(temp_path).unlink()

    def test_read_with_path_object(self):
        """Path 객체로 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write("Path object test")
            temp_path = Path(f.name)

        try:
            content = read_file(temp_path)

            assert content is not None
            assert "Path object test" in content
        finally:
            temp_path.unlink()

    def test_read_large_file(self):
        """큰 파일 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            for i in range(1000):
                f.write(f"Line {i}\n")
            temp_path = f.name

        try:
            content = read_file(temp_path)

            assert content is not None
            assert "Line 0" in content
            assert "Line 999" in content
        finally:
            Path(temp_path).unlink()

    def test_read_file_with_special_characters(self):
        """특수 문자 포함 파일 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write("Special: !@#$%^&*()\n")
            f.write("Emoji: 😀🎉🔥\n")
            temp_path = f.name

        try:
            content = read_file(temp_path)

            assert content is not None
            assert "!@#$%^&*()" in content
        finally:
            Path(temp_path).unlink()


class TestWriteFile:
    """파일 쓰기 테스트"""

    def test_write_simple_content(self):
        """간단한 내용 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.txt"

            result = write_file(filepath, "Hello, World!")

            assert result is True
            assert filepath.exists()
            assert filepath.read_text() == "Hello, World!"

    def test_write_empty_content(self):
        """빈 내용 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "empty.txt"

            result = write_file(filepath, "")

            assert result is True
            assert filepath.exists()
            assert filepath.read_text() == ""

    def test_write_unicode_content(self):
        """유니코드 내용 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "unicode.txt"
            content = "안녕하세요\nこんにちは\n你好"

            result = write_file(filepath, content)

            assert result is True
            assert filepath.read_text(encoding="utf-8") == content

    def test_write_creates_parent_directories(self):
        """부모 디렉토리 자동 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "level1" / "level2" / "test.txt"

            result = write_file(filepath, "Nested file")

            assert result is True
            assert filepath.exists()
            assert filepath.read_text() == "Nested file"

    def test_write_overwrites_existing_file(self):
        """기존 파일 덮어쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "overwrite.txt"
            filepath.write_text("Original content")

            result = write_file(filepath, "New content")

            assert result is True
            assert filepath.read_text() == "New content"

    def test_write_with_custom_encoding(self):
        """커스텀 인코딩으로 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "custom_encoding.txt"

            result = write_file(filepath, "Test content", encoding="latin-1")

            assert result is True
            assert filepath.exists()

    def test_write_with_string_path(self):
        """문자열 경로로 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = str(Path(tmpdir) / "string_path.txt")

            result = write_file(filepath, "String path")

            assert result is True
            assert Path(filepath).exists()

    def test_write_multiline_content(self):
        """여러 줄 내용 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "multiline.txt"
            content = "Line 1\nLine 2\nLine 3\n"

            result = write_file(filepath, content)

            assert result is True
            assert filepath.read_text() == content

    def test_write_large_content(self):
        """큰 내용 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "large.txt"
            content = "\n".join([f"Line {i}" for i in range(10000)])

            result = write_file(filepath, content)

            assert result is True
            assert filepath.exists()
            assert "Line 0" in filepath.read_text()
            assert "Line 9999" in filepath.read_text()

    def test_write_failure_returns_false(self):
        """쓰기 실패 시 False 반환"""
        with patch("pathlib.Path.write_text", side_effect=IOError("Write error")):
            result = write_file("/tmp/test.txt", "content")

            assert result is False


class TestReadJson:
    """JSON 파일 읽기 테스트"""

    def test_read_simple_json(self):
        """간단한 JSON 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump({"name": "John", "age": 30}, f)
            temp_path = f.name

        try:
            data = read_json(temp_path)

            assert data is not None
            assert data["name"] == "John"
            assert data["age"] == 30
        finally:
            Path(temp_path).unlink()

    def test_read_json_array(self):
        """JSON 배열 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump([1, 2, 3, 4, 5], f)
            temp_path = f.name

        try:
            data = read_json(temp_path)

            assert data is not None
            assert isinstance(data, list)
            assert len(data) == 5
            assert data[0] == 1
        finally:
            Path(temp_path).unlink()

    def test_read_nested_json(self):
        """중첩된 JSON 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump({"user": {"name": "John", "address": {"city": "Seoul"}}}, f)
            temp_path = f.name

        try:
            data = read_json(temp_path)

            assert data is not None
            assert data["user"]["name"] == "John"
            assert data["user"]["address"]["city"] == "Seoul"
        finally:
            Path(temp_path).unlink()

    def test_read_json_with_unicode(self):
        """유니코드 JSON 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump({"message": "안녕하세요"}, f, ensure_ascii=False)
            temp_path = f.name

        try:
            data = read_json(temp_path)

            assert data is not None
            assert data["message"] == "안녕하세요"
        finally:
            Path(temp_path).unlink()

    def test_read_empty_json_object(self):
        """빈 JSON 객체 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump({}, f)
            temp_path = f.name

        try:
            data = read_json(temp_path)

            assert data is not None
            assert data == {}
        finally:
            Path(temp_path).unlink()

    def test_read_nonexistent_json_file(self):
        """존재하지 않는 JSON 파일"""
        data = read_json("/nonexistent/file.json")

        assert data is None

    def test_read_invalid_json(self):
        """잘못된 JSON 형식"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as f:
            f.write("not a valid json")
            temp_path = f.name

        try:
            data = read_json(temp_path)

            assert data is None
        finally:
            Path(temp_path).unlink()

    def test_read_json_with_special_types(self):
        """특수 타입 포함 JSON 읽기"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump({"null": None, "bool": True, "number": 3.14}, f)
            temp_path = f.name

        try:
            data = read_json(temp_path)

            assert data is not None
            assert data["null"] is None
            assert data["bool"] is True
            assert data["number"] == 3.14
        finally:
            Path(temp_path).unlink()


class TestWriteJson:
    """JSON 파일 쓰기 테스트"""

    def test_write_simple_json(self):
        """간단한 JSON 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            data = {"name": "John", "age": 30}

            result = write_json(filepath, data)

            assert result is True
            assert filepath.exists()
            loaded = json.loads(filepath.read_text())
            assert loaded == data

    def test_write_json_array(self):
        """JSON 배열 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "array.json"
            data = [1, 2, 3, 4, 5]

            result = write_json(filepath, data)

            assert result is True
            loaded = json.loads(filepath.read_text())
            assert loaded == data

    def test_write_nested_json(self):
        """중첩된 JSON 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "nested.json"
            data = {"user": {"name": "John", "address": {"city": "Seoul"}}}

            result = write_json(filepath, data)

            assert result is True
            loaded = json.loads(filepath.read_text())
            assert loaded == data

    def test_write_json_with_unicode(self):
        """유니코드 JSON 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "unicode.json"
            data = {"message": "안녕하세요", "greeting": "こんにちは"}

            result = write_json(filepath, data)

            assert result is True
            content = filepath.read_text(encoding="utf-8")
            assert "안녕하세요" in content
            assert "こんにちは" in content

    def test_write_json_with_custom_indent(self):
        """커스텀 들여쓰기로 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "indent.json"
            data = {"key": "value"}

            result = write_json(filepath, data, indent=4)

            assert result is True
            content = filepath.read_text()
            assert "    " in content  # 4칸 들여쓰기

    def test_write_json_creates_parent_directories(self):
        """부모 디렉토리 자동 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "level1" / "level2" / "test.json"
            data = {"nested": "directory"}

            result = write_json(filepath, data)

            assert result is True
            assert filepath.exists()

    def test_write_empty_json_object(self):
        """빈 JSON 객체 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "empty.json"

            result = write_json(filepath, {})

            assert result is True
            loaded = json.loads(filepath.read_text())
            assert loaded == {}

    def test_write_json_with_special_types(self):
        """특수 타입 포함 JSON 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "special.json"
            data = {"null": None, "bool": True, "number": 3.14, "string": "text"}

            result = write_json(filepath, data)

            assert result is True
            loaded = json.loads(filepath.read_text())
            assert loaded == data

    def test_write_json_overwrites_existing(self):
        """기존 JSON 파일 덮어쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "overwrite.json"
            write_json(filepath, {"old": "data"})

            result = write_json(filepath, {"new": "data"})

            assert result is True
            loaded = json.loads(filepath.read_text())
            assert loaded == {"new": "data"}

    def test_write_json_failure_returns_false(self):
        """쓰기 실패 시 False 반환"""
        with patch("shared.io.file.io.write_file", return_value=False):
            result = write_json("/tmp/test.json", {"key": "value"})

            assert result is False


class TestIntegration:
    """통합 테스트"""

    def test_read_write_cycle(self):
        """읽기-쓰기 사이클"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "cycle.txt"
            original_content = "Test content for read-write cycle"

            # 쓰기
            write_result = write_file(filepath, original_content)
            assert write_result is True

            # 읽기
            read_content = read_file(filepath)
            assert read_content == original_content

    def test_json_read_write_cycle(self):
        """JSON 읽기-쓰기 사이클"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "cycle.json"
            original_data = {"name": "Test", "value": 123, "nested": {"key": "value"}}

            # 쓰기
            write_result = write_json(filepath, original_data)
            assert write_result is True

            # 읽기
            read_data = read_json(filepath)
            assert read_data == original_data

    def test_ensure_dir_and_write(self):
        """디렉토리 생성 후 파일 쓰기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "test_dir"
            ensure_dir(new_dir)

            filepath = new_dir / "test.txt"
            result = write_file(filepath, "Content in new dir")

            assert result is True
            assert filepath.exists()
            assert read_file(filepath) == "Content in new dir"
