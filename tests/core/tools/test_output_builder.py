# tests/test_output_builder.py
"""
pkg/output/builder.py 단위 테스트

출력 경로 빌더 기능을 테스트합니다.
"""

import os
import sys
from datetime import datetime
from unittest.mock import patch

from core.tools.output.builder import (
    DatePattern,
    OutputPath,
    OutputResult,
    create_report_directory,
    open_file,
    open_in_explorer,
)

# =============================================================================
# DatePattern Enum 테스트
# =============================================================================


class TestDatePattern:
    """DatePattern Enum 테스트"""

    def test_all_patterns_defined(self):
        """모든 패턴 정의 확인"""
        assert DatePattern.DAILY.value == "daily"
        assert DatePattern.MONTHLY.value == "monthly"
        assert DatePattern.YEARLY.value == "yearly"
        assert DatePattern.WEEKLY.value == "weekly"

    def test_patterns_count(self):
        """패턴 개수 확인"""
        assert len(DatePattern) == 4

    def test_string_conversion(self):
        """문자열 변환 가능 확인"""
        assert DatePattern("daily") == DatePattern.DAILY
        assert DatePattern("monthly") == DatePattern.MONTHLY


# =============================================================================
# OutputResult 테스트
# =============================================================================


class TestOutputResult:
    """OutputResult NamedTuple 테스트"""

    def test_creation(self):
        """기본 생성 확인"""
        result = OutputResult(
            path="/path/to/file.xlsx",
            directory="/path/to",
            filename="file.xlsx",
        )
        assert result.path == "/path/to/file.xlsx"
        assert result.directory == "/path/to"
        assert result.filename == "file.xlsx"

    def test_namedtuple_unpacking(self):
        """NamedTuple 언패킹 확인"""
        result = OutputResult(
            path="/path/to/file.xlsx",
            directory="/path/to",
            filename="file.xlsx",
        )
        path, directory, filename = result
        assert path == "/path/to/file.xlsx"
        assert directory == "/path/to"
        assert filename == "file.xlsx"


# =============================================================================
# OutputPath._sanitize 테스트
# =============================================================================


class TestOutputPathSanitize:
    """_sanitize 정적 메서드 테스트"""

    def test_spaces_replaced(self):
        """공백 치환 확인"""
        assert OutputPath._sanitize("my profile") == "my_profile"

    def test_forward_slash_replaced(self):
        """포워드 슬래시 치환 확인"""
        assert OutputPath._sanitize("dev/prod") == "dev_prod"

    def test_backslash_replaced(self):
        """백슬래시 치환 확인"""
        assert OutputPath._sanitize("dev\\prod") == "dev_prod"

    def test_combined(self):
        """복합 치환 확인"""
        assert OutputPath._sanitize("my profile/test\\name") == "my_profile_test_name"

    def test_clean_string_unchanged(self):
        """안전한 문자열은 변경 없음"""
        assert OutputPath._sanitize("clean_profile") == "clean_profile"


# =============================================================================
# OutputPath._get_date_parts 테스트
# =============================================================================


class TestOutputPathGetDateParts:
    """_get_date_parts 정적 메서드 테스트"""

    def test_yearly_pattern(self):
        """YEARLY 패턴 테스트"""
        parts = OutputPath._get_date_parts(DatePattern.YEARLY)
        # 현재 연도 포함
        assert len(parts) == 1
        assert parts[0].isdigit()
        assert len(parts[0]) == 4

    def test_monthly_pattern(self):
        """MONTHLY 패턴 테스트"""
        parts = OutputPath._get_date_parts(DatePattern.MONTHLY)
        # [연도, 월] 형태
        assert len(parts) == 2
        assert parts[0].isdigit()  # 연도
        assert parts[1].isdigit()  # 월 (01-12)
        assert len(parts[1]) == 2  # 패딩됨

    def test_daily_pattern(self):
        """DAILY 패턴 테스트"""
        parts = OutputPath._get_date_parts(DatePattern.DAILY)
        # [YYYY-MM-DD] 형태
        assert len(parts) == 1
        assert "-" in parts[0]
        assert len(parts[0]) == 10  # YYYY-MM-DD

    def test_weekly_pattern(self):
        """WEEKLY 패턴 테스트"""
        parts = OutputPath._get_date_parts(DatePattern.WEEKLY)
        # [연도, 월, 주차] 형태
        assert len(parts) == 3
        assert parts[0].isdigit()  # 연도
        assert parts[1].isdigit()  # 월
        assert "월" in parts[2]  # X월Y주차
        assert "주차" in parts[2]


# =============================================================================
# OutputPath.build 테스트
# =============================================================================


class TestOutputPathBuild:
    """build 메서드 테스트"""

    def test_basic_build(self, tmp_path):
        """기본 빌드 테스트"""
        with patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)):
            path = OutputPath("test-profile").build()

            assert os.path.exists(path)
            assert "output" in path
            assert "test-profile" in path

    def test_build_with_sub(self, tmp_path):
        """sub 경로 추가 테스트"""
        with patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)):
            path = OutputPath("test-profile").sub("tools", "ebs").build()

            assert os.path.exists(path)
            assert "tools" in path
            assert "ebs" in path

    def test_build_with_date_string(self, tmp_path):
        """문자열 날짜 패턴 테스트"""
        with (
            patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)),
            patch("core.tools.output.builder.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = datetime(2025, 12, 10)
            path = OutputPath("test-profile").with_date("monthly").build()

            assert "2025" in path
            assert "12" in path

    def test_build_with_date_enum(self, tmp_path):
        """Enum 날짜 패턴 테스트"""
        with (
            patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)),
            patch("core.tools.output.builder.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = datetime(2025, 12, 10)
            path = OutputPath("test-profile").with_date(DatePattern.YEARLY).build()

            assert "2025" in path

    def test_build_creates_directory(self, tmp_path):
        """디렉토리 자동 생성 확인"""
        with patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)):
            path = OutputPath("new-profile").sub("deeply", "nested", "path").build()

            assert os.path.isdir(path)


# =============================================================================
# OutputPath.save_file 테스트
# =============================================================================


class TestOutputPathSaveFile:
    """save_file 메서드 테스트"""

    def test_save_file_returns_output_result(self, tmp_path):
        """OutputResult 반환 테스트"""
        with patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)):
            result = OutputPath("test-profile").save_file("test.txt")

            assert isinstance(result, OutputResult)
            assert result.filename == "test.txt"
            # content 없으면 파일 생성 안됨 (경로만 반환)
            assert "test.txt" in result.path

    def test_save_file_with_content(self, tmp_path):
        """내용 있는 파일 저장 테스트"""
        with patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)):
            content = "Hello, World!"
            result = OutputPath("test-profile").save_file("test.txt", content)

            assert os.path.exists(result.path)
            with open(result.path, encoding="utf-8") as f:
                assert f.read() == content


# =============================================================================
# OutputPath.sub 체이닝 테스트
# =============================================================================


class TestOutputPathChaining:
    """메서드 체이닝 테스트"""

    def test_sub_returns_self(self):
        """sub()이 self 반환"""
        builder = OutputPath("test")
        result = builder.sub("path1")
        assert result is builder

    def test_with_date_returns_self(self):
        """with_date()가 self 반환"""
        builder = OutputPath("test")
        result = builder.with_date("daily")
        assert result is builder

    def test_full_chain(self, tmp_path):
        """전체 체이닝 테스트"""
        with (
            patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)),
            patch("core.tools.output.builder.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = datetime(2025, 12, 10)

            path = OutputPath("test-profile").sub("AWS_EBS_Reports").with_date("monthly").build()

            assert "test-profile" in path
            assert "AWS_EBS_Reports" in path
            assert "2025" in path
            assert "12" in path


# =============================================================================
# open_in_explorer 테스트
# =============================================================================


class TestOpenInExplorer:
    """open_in_explorer 함수 테스트"""

    def test_creates_directory_if_not_exists(self, tmp_path):
        """디렉토리 없으면 생성"""
        new_dir = tmp_path / "new_folder"
        assert not new_dir.exists()

        with (
            patch.object(sys, "platform", "win32"),
            patch("os.startfile", create=True),
        ):
            open_in_explorer(str(new_dir))

        assert new_dir.exists()

    @patch("os.startfile", create=True)
    def test_windows_uses_startfile(self, mock_startfile, tmp_path):
        """Windows에서 os.startfile 사용"""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch.object(sys, "platform", "win32"):
            result = open_in_explorer(str(test_dir))

        mock_startfile.assert_called_once_with(str(test_dir))
        assert result is True

    @patch("subprocess.run")
    def test_macos_uses_open(self, mock_run, tmp_path):
        """macOS에서 open 명령어 사용"""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch.object(sys, "platform", "darwin"):
            result = open_in_explorer(str(test_dir))

        mock_run.assert_called_once_with(["open", str(test_dir)], check=False)
        assert result is True

    @patch("subprocess.run")
    def test_linux_uses_xdg_open(self, mock_run, tmp_path):
        """Linux에서 xdg-open 명령어 사용"""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch.object(sys, "platform", "linux"):
            result = open_in_explorer(str(test_dir))

        mock_run.assert_called_once_with(["xdg-open", str(test_dir)], check=False)
        assert result is True

    @patch("os.startfile", create=True, side_effect=Exception("error"))
    def test_returns_false_on_error(self, mock_startfile, tmp_path):
        """에러 발생 시 False 반환"""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch.object(sys, "platform", "win32"):
            result = open_in_explorer(str(test_dir))

        assert result is False


# =============================================================================
# open_file 테스트
# =============================================================================


class TestOpenFile:
    """open_file 함수 테스트"""

    def test_returns_false_if_not_exists(self):
        """파일 없으면 False 반환"""
        result = open_file("/nonexistent/file.txt")
        assert result is False

    @patch("os.startfile", create=True)
    def test_windows_uses_startfile(self, mock_startfile, tmp_path):
        """Windows에서 os.startfile 사용"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        with patch.object(sys, "platform", "win32"):
            result = open_file(str(test_file))

        mock_startfile.assert_called_once_with(str(test_file))
        assert result is True

    @patch("subprocess.run")
    def test_macos_uses_open(self, mock_run, tmp_path):
        """macOS에서 open 명령어 사용"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        with patch.object(sys, "platform", "darwin"):
            result = open_file(str(test_file))

        mock_run.assert_called_once_with(["open", str(test_file)], check=False)
        assert result is True


# =============================================================================
# create_report_directory 테스트
# =============================================================================


class TestCreateReportDirectory:
    """create_report_directory 함수 테스트"""

    def test_creates_tools_subdirectory(self, tmp_path):
        """tools 하위 디렉토리 생성"""
        with (
            patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)),
            patch("core.tools.output.builder.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = datetime(2025, 12, 10)

            path = create_report_directory("ebs", "my-profile")

            assert os.path.isdir(path)
            assert "tools" in path
            assert "ebs" in path
            assert "my-profile" in path

    def test_uses_default_identifier(self, tmp_path):
        """기본 identifier 사용"""
        with (
            patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)),
            patch("core.tools.output.builder.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = datetime(2025, 12, 10)

            path = create_report_directory("ebs")

            assert "default" in path

    def test_respects_date_pattern(self, tmp_path):
        """날짜 패턴 적용"""
        with (
            patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)),
            patch("core.tools.output.builder.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = datetime(2025, 12, 10)

            path = create_report_directory("ebs", "test", "daily")

            assert "2025-12-10" in path


# =============================================================================
# OutputPath._get_project_root Tests
# =============================================================================


class TestGetProjectRoot:
    """_get_project_root 메서드 테스트"""

    def test_uses_env_variable_if_set(self, tmp_path):
        """환경 변수 AA_OUTPUT_ROOT 우선 사용"""
        test_root = tmp_path / "custom_root"
        test_root.mkdir()

        with patch.dict(os.environ, {"AA_OUTPUT_ROOT": str(test_root)}):
            root = OutputPath._get_project_root()
            assert str(test_root) in root

    def test_finds_pyproject_toml(self, tmp_path):
        """pyproject.toml이 있는 디렉토리 찾기"""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "pyproject.toml").touch()

        nested = project_root / "core" / "tools"
        nested.mkdir(parents=True)

        original_cwd = os.getcwd()
        try:
            os.chdir(nested)
            root = OutputPath._get_project_root()
            # Should find project_root
            assert "project" in root or os.path.exists(os.path.join(root, "pyproject.toml"))
        finally:
            os.chdir(original_cwd)

    def test_finds_git_directory(self, tmp_path):
        """.git이 있는 디렉토리 찾기"""
        project_root = tmp_path / "git_project"
        project_root.mkdir()
        (project_root / ".git").mkdir()

        nested = project_root / "subdir"
        nested.mkdir()

        original_cwd = os.getcwd()
        try:
            os.chdir(nested)
            root = OutputPath._get_project_root()
            assert "git_project" in root or os.path.exists(os.path.join(root, ".git"))
        finally:
            os.chdir(original_cwd)

    def test_fallback_to_cwd(self, tmp_path):
        """마커 파일 없으면 현재 디렉토리 반환"""
        temp_dir = tmp_path / "no_markers"
        temp_dir.mkdir()

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            root = OutputPath._get_project_root()
            # Should return cwd
            assert os.path.exists(root)
        finally:
            os.chdir(original_cwd)


# =============================================================================
# Weekly Date Pattern Tests
# =============================================================================


class TestWeeklyDatePattern:
    """주차 계산 테스트"""

    def test_first_week_of_month(self):
        """월 첫째 주 테스트"""
        with patch("core.tools.output.builder.datetime") as mock_dt:
            # 2025년 12월 1일 (월요일)
            mock_dt.now.return_value = datetime(2025, 12, 1)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            parts = OutputPath._get_date_parts(DatePattern.WEEKLY)

            assert len(parts) == 3
            assert parts[0] == "2025"
            assert parts[1] == "12"
            assert "1주차" in parts[2]

    def test_second_week_of_month(self):
        """월 둘째 주 테스트"""
        with patch("core.tools.output.builder.datetime") as mock_dt:
            # 2025년 12월 10일
            mock_dt.now.return_value = datetime(2025, 12, 10)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            parts = OutputPath._get_date_parts(DatePattern.WEEKLY)

            assert "2주차" in parts[2]

    def test_last_week_of_month(self):
        """월 마지막 주 테스트"""
        with patch("core.tools.output.builder.datetime") as mock_dt:
            # 2025년 12월 31일
            mock_dt.now.return_value = datetime(2025, 12, 31)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            parts = OutputPath._get_date_parts(DatePattern.WEEKLY)

            # Should be 4th or 5th week
            assert "주차" in parts[2]


# =============================================================================
# print_report_complete Tests
# =============================================================================


class TestPrintReportComplete:
    """print_report_complete 함수 테스트"""

    def test_single_path_output(self, capsys):
        """단일 경로 출력"""
        from core.tools.output.builder import print_report_complete

        print_report_complete("/path/to/report.xlsx")

        captured = capsys.readouterr()
        assert "보고서 생성 완료" in captured.out
        assert "/path/to/report.xlsx" in captured.out

    def test_multiple_paths_output(self, capsys):
        """여러 경로 출력"""
        from core.tools.output.builder import print_report_complete

        paths = {
            "excel": "/path/to/report.xlsx",
            "html": "/path/to/report.html",
        }
        print_report_complete(paths)

        captured = capsys.readouterr()
        assert "EXCEL" in captured.out
        assert "HTML" in captured.out

    def test_custom_message(self, capsys):
        """커스텀 메시지 출력"""
        from core.tools.output.builder import print_report_complete

        print_report_complete("/path/to/report.xlsx", message="분석 완료!")

        captured = capsys.readouterr()
        assert "분석 완료" in captured.out

    def test_empty_path_in_dict(self, capsys):
        """딕셔너리에 빈 경로 포함"""
        from core.tools.output.builder import print_report_complete

        paths = {
            "excel": "/path/to/report.xlsx",
            "html": "",  # Empty path
            "csv": None,  # None path
        }
        print_report_complete(paths)

        captured = capsys.readouterr()
        assert "EXCEL" in captured.out
        # Empty/None paths should be skipped


# =============================================================================
# single_report_directory Tests
# =============================================================================


class TestSingleReportDirectory:
    """single_report_directory 함수 테스트"""

    def test_creates_reports_subdirectory(self, tmp_path):
        """reports 하위 디렉토리 생성"""
        from core.tools.output.builder import single_report_directory

        with (
            patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)),
            patch("core.tools.output.builder.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = datetime(2025, 12, 31)

            path = single_report_directory("my-sso-session")

            assert os.path.isdir(path)
            assert "my-sso-session" in path
            assert "reports" in path
            assert "2025-12-31" in path

    def test_uses_daily_pattern(self, tmp_path):
        """DAILY 패턴 사용 확인"""
        from core.tools.output.builder import single_report_directory

        with (
            patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)),
            patch("core.tools.output.builder.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = datetime(2025, 1, 15)

            path = single_report_directory("test-session")

            assert "2025-01-15" in path


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """통합 테스트"""

    def test_full_workflow_with_file_save(self, tmp_path):
        """파일 저장 전체 워크플로우"""
        with (
            patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)),
            patch("core.tools.output.builder.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = datetime(2025, 12, 25)

            # Build path with chaining
            builder = OutputPath("christmas-profile").sub("AWS_Reports").with_date("monthly")

            # Save file
            content = "Test report content"
            result = builder.save_file("report.txt", content)

            # Verify
            assert os.path.exists(result.path)
            assert "christmas-profile" in result.path
            assert "AWS_Reports" in result.path
            assert "2025" in result.path
            assert "12" in result.path

            with open(result.path, encoding="utf-8") as f:
                assert f.read() == content

    def test_multiple_files_same_directory(self, tmp_path):
        """같은 디렉토리에 여러 파일 저장"""
        with patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)):
            builder = OutputPath("test-profile").sub("reports")

            result1 = builder.save_file("file1.txt", "Content 1")
            result2 = builder.save_file("file2.txt", "Content 2")

            # Same directory
            assert result1.directory == result2.directory

            # Both files exist
            assert os.path.exists(result1.path)
            assert os.path.exists(result2.path)

    def test_sanitization_in_full_workflow(self, tmp_path):
        """전체 워크플로우에서 sanitization 확인"""
        with patch.object(OutputPath, "_get_project_root", return_value=str(tmp_path)):
            # Identifier with special characters
            path = OutputPath("my profile/test\\name").build()

            assert "my_profile_test_name" in path
            assert " " not in path
            assert "/" not in os.path.basename(path)
            assert "\\" not in os.path.basename(path)
