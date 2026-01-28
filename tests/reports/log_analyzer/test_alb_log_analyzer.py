"""
tests/reports/log_analyzer/test_alb_log_analyzer.py - ALB log analyzer tests

Tests for the DuckDB-based ALB log analyzer.
Note: These tests focus on structure and logic; actual DuckDB operations are mocked.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestALBLogAnalyzerStructure:
    """Test ALB log analyzer structure and initialization"""

    @pytest.fixture
    def mock_duckdb(self):
        """Mock DuckDB module"""
        with patch("reports.log_analyzer.alb_log_analyzer.duckdb") as mock:
            mock_conn = MagicMock()
            mock.connect.return_value = mock_conn
            yield mock

    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client"""
        return MagicMock()

    def test_analyzer_import(self):
        """Should be able to import ALBLogAnalyzer"""
        try:
            from reports.log_analyzer.alb_log_analyzer import ALBLogAnalyzer

            assert ALBLogAnalyzer is not None
        except ImportError as e:
            # If duckdb is not installed, this is expected
            if "duckdb" not in str(e):
                raise

    @patch("reports.log_analyzer.alb_log_analyzer.duckdb")
    def test_analyzer_initialization(self, mock_duckdb):
        """Should initialize ALBLogAnalyzer with required parameters"""
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn

        from reports.log_analyzer.alb_log_analyzer import ALBLogAnalyzer

        mock_s3_client = MagicMock()
        start_time = datetime(2024, 1, 1, 0, 0, 0)

        analyzer = ALBLogAnalyzer(
            s3_client=mock_s3_client,
            bucket_name="test-bucket",
            prefix="logs/alb",
            start_datetime=start_time,
        )

        assert analyzer.bucket_name == "test-bucket"
        assert analyzer.prefix == "logs/alb"
        assert analyzer.start_datetime == start_time

    @patch("reports.log_analyzer.alb_log_analyzer.duckdb")
    def test_analyzer_datetime_string_conversion(self, mock_duckdb):
        """Should convert datetime strings to datetime objects"""
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn

        from reports.log_analyzer.alb_log_analyzer import ALBLogAnalyzer

        mock_s3_client = MagicMock()

        analyzer = ALBLogAnalyzer(
            s3_client=mock_s3_client,
            bucket_name="test-bucket",
            prefix="logs/alb",
            start_datetime="2024-01-01 00:00",
            end_datetime="2024-01-02 00:00",
        )

        assert isinstance(analyzer.start_datetime, datetime)
        assert isinstance(analyzer.end_datetime, datetime)
        assert analyzer.start_datetime.year == 2024
        assert analyzer.start_datetime.month == 1
        assert analyzer.start_datetime.day == 1

    @patch("reports.log_analyzer.alb_log_analyzer.duckdb")
    def test_analyzer_invalid_datetime_string(self, mock_duckdb):
        """Should raise ValueError for invalid datetime string"""
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn

        from reports.log_analyzer.alb_log_analyzer import ALBLogAnalyzer

        mock_s3_client = MagicMock()

        with pytest.raises(ValueError):
            ALBLogAnalyzer(
                s3_client=mock_s3_client,
                bucket_name="test-bucket",
                prefix="logs/alb",
                start_datetime="invalid-date",
            )

    @patch("reports.log_analyzer.alb_log_analyzer.duckdb")
    def test_analyzer_timezone_setup(self, mock_duckdb):
        """Should set up timezone correctly"""
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn

        from reports.log_analyzer.alb_log_analyzer import ALBLogAnalyzer

        mock_s3_client = MagicMock()
        start_time = datetime(2024, 1, 1, 0, 0, 0)

        analyzer = ALBLogAnalyzer(
            s3_client=mock_s3_client,
            bucket_name="test-bucket",
            prefix="logs/alb",
            start_datetime=start_time,
            timezone="Asia/Seoul",
        )

        assert analyzer.timezone.zone == "Asia/Seoul"

    @patch("reports.log_analyzer.alb_log_analyzer.duckdb")
    def test_analyzer_invalid_timezone(self, mock_duckdb):
        """Should fall back to UTC for invalid timezone"""
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn

        from reports.log_analyzer.alb_log_analyzer import ALBLogAnalyzer

        mock_s3_client = MagicMock()
        start_time = datetime(2024, 1, 1, 0, 0, 0)

        with patch("reports.log_analyzer.alb_log_analyzer.logger") as mock_logger:
            analyzer = ALBLogAnalyzer(
                s3_client=mock_s3_client,
                bucket_name="test-bucket",
                prefix="logs/alb",
                start_datetime=start_time,
                timezone="Invalid/Timezone",
            )

            # Should log warning
            mock_logger.warning.assert_called()


class TestALBLogAnalyzerMethods:
    """Test ALB log analyzer methods"""

    @patch("reports.log_analyzer.alb_log_analyzer.duckdb")
    def test_get_empty_analysis_results(self, mock_duckdb):
        """Should return empty analysis results structure"""
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn

        from reports.log_analyzer.alb_log_analyzer import ALBLogAnalyzer

        mock_s3_client = MagicMock()
        start_time = datetime(2024, 1, 1, 0, 0, 0)

        analyzer = ALBLogAnalyzer(
            s3_client=mock_s3_client,
            bucket_name="test-bucket",
            prefix="logs/alb",
            start_datetime=start_time,
        )

        results = analyzer._get_empty_analysis_results()

        # Check structure
        assert "start_time" in results
        assert "end_time" in results
        assert "log_lines_count" in results
        assert "client_ip_counts" in results
        assert "request_url_counts" in results
        assert "user_agent_counts" in results
        assert "elb_2xx_count" in results
        assert "elb_4xx_count" in results
        assert "elb_5xx_count" in results

        # Check default values
        assert results["log_lines_count"] == 0
        assert results["elb_2xx_count"] == 0
        assert isinstance(results["client_ip_counts"], dict)
        assert len(results["client_ip_counts"]) == 0


class TestDuckDBCheck:
    """Test DuckDB availability check"""

    def test_check_duckdb_available(self):
        """Should not raise error when DuckDB is available"""
        try:
            from reports.log_analyzer.alb_log_analyzer import _check_duckdb

            # Should not raise if duckdb is installed
            _check_duckdb()
        except ImportError:
            # If duckdb module itself can't be imported, skip this test
            pytest.skip("DuckDB not installed")

    @patch("reports.log_analyzer.alb_log_analyzer.duckdb", None)
    def test_check_duckdb_unavailable(self):
        """Should raise ImportError when DuckDB is not available"""
        from reports.log_analyzer.alb_log_analyzer import _check_duckdb

        with pytest.raises(ImportError) as exc_info:
            _check_duckdb()

        assert "DuckDB" in str(exc_info.value)
        assert "pip install duckdb" in str(exc_info.value)


class TestALBLogAnalyzerCleanup:
    """Test cleanup functionality"""

    @patch("reports.log_analyzer.alb_log_analyzer.duckdb")
    @patch("os.path.exists")
    @patch("shutil.rmtree")
    def test_cleanup_removes_directories(self, mock_rmtree, mock_exists, mock_duckdb):
        """Should clean up temporary directories"""
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn
        mock_exists.return_value = True

        from reports.log_analyzer.alb_log_analyzer import ALBLogAnalyzer

        mock_s3_client = MagicMock()
        start_time = datetime(2024, 1, 1, 0, 0, 0)

        analyzer = ALBLogAnalyzer(
            s3_client=mock_s3_client,
            bucket_name="test-bucket",
            prefix="logs/alb",
            start_datetime=start_time,
        )

        analyzer.clean_up([])

        # Should close connection
        mock_conn.close.assert_called()

    @patch("reports.log_analyzer.alb_log_analyzer.duckdb")
    def test_cleanup_handles_errors_gracefully(self, mock_duckdb):
        """Should handle cleanup errors gracefully"""
        mock_conn = MagicMock()
        mock_conn.close.side_effect = Exception("Connection close error")
        mock_duckdb.connect.return_value = mock_conn

        from reports.log_analyzer.alb_log_analyzer import ALBLogAnalyzer

        mock_s3_client = MagicMock()
        start_time = datetime(2024, 1, 1, 0, 0, 0)

        analyzer = ALBLogAnalyzer(
            s3_client=mock_s3_client,
            bucket_name="test-bucket",
            prefix="logs/alb",
            start_datetime=start_time,
        )

        # Should not raise exception
        analyzer.clean_up([])
