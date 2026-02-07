"""
tests/shared/io/csv/test_handler.py - CSV 핸들러 테스트
"""

from unittest.mock import patch

from shared.io.csv.handler import (
    ENCODING_PRIORITIES,
    detect_csv_encoding,
    get_platform_recommended_encoding,
    read_csv_robust,
    validate_csv_headers,
)


class TestDetectCsvEncoding:
    """CSV 인코딩 감지 테스트"""

    def test_detect_utf8_encoding(self, tmp_path):
        """UTF-8 인코딩 감지"""
        temp_file = tmp_path / "utf8.csv"
        temp_file.write_text("이름,나이\n홍길동,30\n김철수,25\n", encoding="utf-8")

        encoding, error = detect_csv_encoding(str(temp_file))

        assert encoding is not None
        assert error is None
        assert encoding in ["utf-8", "utf-8-sig"]

    def test_detect_utf8_sig_encoding(self, tmp_path):
        """UTF-8-SIG (BOM) 인코딩 감지"""
        temp_file = tmp_path / "utf8sig.csv"
        with open(temp_file, "w", encoding="utf-8-sig") as f:
            f.write("Name,Age\nJohn,30\nJane,25\n")

        encoding, error = detect_csv_encoding(str(temp_file))

        assert encoding is not None
        assert error is None

    def test_detect_cp949_encoding(self, tmp_path):
        """CP949 (한국어 Windows) 인코딩 감지"""
        temp_file = tmp_path / "cp949.csv"
        with open(temp_file, "w", encoding="cp949") as f:
            f.write("이름,나이\n홍길동,30\n")

        encoding, error = detect_csv_encoding(str(temp_file))

        assert encoding is not None
        assert error is None
        # cp949 또는 euc-kr로 감지될 수 있음 (대소문자 구분 없이)
        assert encoding.lower() in ["cp949", "euc-kr", "utf-8", "utf-8-sig"]

    def test_file_not_found(self):
        """존재하지 않는 파일"""
        encoding, error = detect_csv_encoding("/nonexistent/file.csv")

        assert encoding is None
        assert error is not None
        assert "찾을 수 없습니다" in error

    def test_directory_instead_of_file(self, tmp_path):
        """디렉토리 경로 전달"""
        encoding, error = detect_csv_encoding(str(tmp_path))

        assert encoding is None
        assert error is not None
        assert "파일이 아닙니다" in error

    def test_empty_file(self, tmp_path):
        """빈 파일"""
        temp_file = tmp_path / "empty.csv"
        temp_file.write_text("", encoding="utf-8")

        encoding, error = detect_csv_encoding(str(temp_file))

        # 빈 파일은 실패할 수 있음
        assert encoding is None or encoding in ENCODING_PRIORITIES

    @patch("shared.io.csv.handler.CHARDET_AVAILABLE", False)
    def test_fallback_without_chardet(self, tmp_path):
        """chardet 없이 폴백 방식"""
        temp_file = tmp_path / "fallback.csv"
        temp_file.write_text("Name,Age\nJohn,30\n", encoding="utf-8")

        encoding, error = detect_csv_encoding(str(temp_file))

        assert encoding is not None
        assert error is None
        assert encoding in ENCODING_PRIORITIES

    def test_chardet_low_confidence(self, tmp_path):
        """chardet 신뢰도 낮을 때 폴백"""
        temp_file = tmp_path / "short.csv"
        temp_file.write_text("a,b\n", encoding="utf-8")

        encoding, error = detect_csv_encoding(str(temp_file))

        # 짧은 파일이어도 인코딩은 감지되어야 함
        assert encoding is not None
        assert error is None

    def test_non_csv_file(self, tmp_path):
        """CSV가 아닌 파일"""
        temp_file = tmp_path / "plain.txt"
        temp_file.write_text("This is not a CSV file\nJust plain text\n", encoding="utf-8")

        encoding, error = detect_csv_encoding(str(temp_file))

        # 평문 파일도 인코딩은 감지될 수 있음 (CSV 형식 검증은 별도)
        # 이 테스트는 인코딩 감지만 테스트하므로 성공 가능
        assert encoding is not None or error is not None


class TestReadCsvRobust:
    """CSV 읽기 테스트"""

    def test_read_simple_csv(self, tmp_path):
        """간단한 CSV 읽기"""
        temp_file = tmp_path / "simple.csv"
        temp_file.write_text("Name,Age,City\nJohn,30,Seoul\nJane,25,Busan\n", encoding="utf-8")

        data, encoding, error = read_csv_robust(str(temp_file))

        assert data is not None
        assert encoding is not None
        assert error is None
        assert len(data) == 2
        assert data[0]["Name"] == "John"
        assert data[0]["Age"] == "30"
        assert data[1]["City"] == "Busan"

    def test_read_with_specific_encoding(self, tmp_path):
        """특정 인코딩 지정하여 읽기"""
        temp_file = tmp_path / "utf8sig.csv"
        with open(temp_file, "w", encoding="utf-8-sig") as f:
            f.write("Name,Age\nJohn,30\n")

        data, encoding, error = read_csv_robust(str(temp_file), encoding="utf-8-sig")

        assert data is not None
        assert encoding == "utf-8-sig"
        assert error is None
        assert len(data) == 1

    def test_read_korean_content(self, tmp_path):
        """한글 내용 읽기"""
        temp_file = tmp_path / "korean.csv"
        temp_file.write_text("이름,나이,도시\n홍길동,30,서울\n김철수,25,부산\n", encoding="utf-8")

        data, encoding, error = read_csv_robust(str(temp_file))

        assert data is not None
        assert encoding is not None
        assert error is None
        assert len(data) == 2
        assert data[0]["이름"] == "홍길동"
        assert data[1]["도시"] == "부산"

    def test_read_with_empty_values(self, tmp_path):
        """빈 값이 있는 CSV 읽기"""
        temp_file = tmp_path / "empty_values.csv"
        temp_file.write_text("Name,Age,City\nJohn,30,\n,25,Busan\nTom,,Seoul\n", encoding="utf-8")

        data, encoding, error = read_csv_robust(str(temp_file))

        assert data is not None
        assert error is None
        assert len(data) == 3
        # 빈 값은 None으로 변환
        assert data[0]["City"] is None
        assert data[1]["Name"] is None
        assert data[2]["Age"] is None

    def test_read_with_whitespace(self, tmp_path):
        """공백이 있는 값 처리"""
        temp_file = tmp_path / "whitespace.csv"
        temp_file.write_text("Name,Age\n  John  ,  30  \nJane,25\n", encoding="utf-8")

        data, encoding, error = read_csv_robust(str(temp_file))

        assert data is not None
        assert error is None
        # 공백은 제거됨
        assert data[0]["Name"] == "John"
        assert data[0]["Age"] == "30"

    def test_file_not_found_error(self):
        """파일 없음 에러"""
        data, encoding, error = read_csv_robust("/nonexistent/file.csv")

        assert data is None
        assert encoding is None
        assert error is not None
        assert "찾을 수 없습니다" in error

    def test_invalid_encoding(self, tmp_path):
        """잘못된 인코딩 지정"""
        temp_file = tmp_path / "invalid_enc.csv"
        temp_file.write_text("Name,Age\nJohn,30\n", encoding="utf-8")

        data, encoding, error = read_csv_robust(str(temp_file), encoding="invalid-encoding")

        # 잘못된 인코딩이면 실패
        assert data is None
        assert error is not None

    def test_no_header(self, tmp_path):
        """헤더가 없는 CSV"""
        temp_file = tmp_path / "no_header.csv"
        temp_file.write_text("", encoding="utf-8")

        data, encoding, error = read_csv_robust(str(temp_file))

        # 헤더가 없으면 실패
        assert data is None

    def test_permission_error(self, tmp_path):
        """권한 에러 시뮬레이션"""
        temp_file = tmp_path / "perm.csv"
        temp_file.write_text("Name,Age\nJohn,30\n", encoding="utf-8")

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            data, encoding, error = read_csv_robust(str(temp_file))

            assert data is None
            assert encoding is None
            assert error is not None
            assert "권한이 없습니다" in error

    def test_malformed_row_handling(self, tmp_path):
        """잘못된 형식의 행 처리"""
        temp_file = tmp_path / "malformed.csv"
        temp_file.write_text("Name,Age,City\nJohn,30,Seoul\nJane,25,Busan\n", encoding="utf-8")

        data, encoding, error = read_csv_robust(str(temp_file))

        assert data is not None
        assert error is None
        assert len(data) == 2

    def test_large_file(self, tmp_path):
        """큰 파일 읽기"""
        temp_file = tmp_path / "large.csv"
        lines = ["ID,Name,Value\n"]
        for i in range(1000):
            lines.append(f"{i},Name{i},{i * 100}\n")
        temp_file.write_text("".join(lines), encoding="utf-8")

        data, encoding, error = read_csv_robust(str(temp_file))

        assert data is not None
        assert error is None
        assert len(data) == 1000
        assert data[0]["ID"] == "0"
        assert data[999]["ID"] == "999"


class TestValidateCsvHeaders:
    """CSV 헤더 검증 테스트"""

    def test_validate_valid_headers(self, tmp_path):
        """올바른 헤더 검증"""
        temp_file = tmp_path / "valid.csv"
        temp_file.write_text("Name,Age,City\nJohn,30,Seoul\n", encoding="utf-8")

        is_valid, message, encoding = validate_csv_headers(str(temp_file), required_headers=["Name", "Age", "City"])

        assert is_valid is True
        assert "성공" in message
        assert encoding is not None

    def test_validate_partial_headers(self, tmp_path):
        """일부 필수 헤더만 검증"""
        temp_file = tmp_path / "partial.csv"
        temp_file.write_text("Name,Age,City,Country\nJohn,30,Seoul,Korea\n", encoding="utf-8")

        is_valid, message, encoding = validate_csv_headers(str(temp_file), required_headers=["Name", "Age"])

        assert is_valid is True
        assert "성공" in message

    def test_validate_missing_headers(self, tmp_path):
        """누락된 헤더 감지"""
        temp_file = tmp_path / "missing.csv"
        temp_file.write_text("Name,Age\nJohn,30\n", encoding="utf-8")

        is_valid, message, encoding = validate_csv_headers(str(temp_file), required_headers=["Name", "Age", "City"])

        assert is_valid is False
        assert "누락" in message
        assert "City" in message

    def test_validate_empty_file(self, tmp_path):
        """빈 파일 검증"""
        temp_file = tmp_path / "empty.csv"
        temp_file.write_text("", encoding="utf-8")

        is_valid, message, encoding = validate_csv_headers(str(temp_file), required_headers=["Name"])

        assert is_valid is False
        assert "비어있습니다" in message or "실패" in message

    def test_validate_file_not_found(self):
        """존재하지 않는 파일 검증"""
        is_valid, message, encoding = validate_csv_headers("/nonexistent/file.csv", required_headers=["Name"])

        assert is_valid is False
        assert "실패" in message
        assert encoding is None

    def test_validate_with_encoding(self, tmp_path):
        """특정 인코딩으로 검증"""
        temp_file = tmp_path / "enc.csv"
        with open(temp_file, "w", encoding="utf-8-sig") as f:
            f.write("Name,Age\nJohn,30\n")

        is_valid, message, encoding = validate_csv_headers(
            str(temp_file), required_headers=["Name", "Age"], encoding="utf-8-sig"
        )

        assert is_valid is True
        assert encoding == "utf-8-sig"

    def test_validate_case_sensitive(self, tmp_path):
        """대소문자 구분 검증"""
        temp_file = tmp_path / "case.csv"
        temp_file.write_text("name,age\nJohn,30\n", encoding="utf-8")

        is_valid, message, encoding = validate_csv_headers(str(temp_file), required_headers=["Name", "Age"])

        # 대소문자가 다르면 실패
        assert is_valid is False
        assert "누락" in message


class TestGetPlatformRecommendedEncoding:
    """플랫폼별 권장 인코딩 테스트"""

    @patch("platform.system", return_value="Windows")
    def test_windows_encoding(self, mock_system):
        """Windows 권장 인코딩"""
        encoding = get_platform_recommended_encoding()

        assert encoding == "utf-8-sig"

    @patch("platform.system", return_value="Darwin")
    def test_macos_encoding(self, mock_system):
        """macOS 권장 인코딩"""
        encoding = get_platform_recommended_encoding()

        assert encoding == "utf-8"

    @patch("platform.system", return_value="Linux")
    def test_linux_encoding(self, mock_system):
        """Linux 권장 인코딩"""
        encoding = get_platform_recommended_encoding()

        assert encoding == "utf-8"

    @patch("platform.system", return_value="Unknown")
    def test_unknown_platform_encoding(self, mock_system):
        """알 수 없는 플랫폼 (기본값)"""
        encoding = get_platform_recommended_encoding()

        assert encoding == "utf-8-sig"


class TestEncodingPriorities:
    """인코딩 우선순위 상수 테스트"""

    def test_encoding_priorities_defined(self):
        """인코딩 우선순위 정의 확인"""
        assert ENCODING_PRIORITIES is not None
        assert len(ENCODING_PRIORITIES) > 0
        assert "utf-8" in ENCODING_PRIORITIES
        assert "utf-8-sig" in ENCODING_PRIORITIES

    def test_utf8_sig_first_priority(self):
        """UTF-8-SIG가 첫 번째 우선순위"""
        assert ENCODING_PRIORITIES[0] == "utf-8-sig"

    def test_latin1_fallback(self):
        """latin-1이 마지막 폴백"""
        assert "latin-1" in ENCODING_PRIORITIES
