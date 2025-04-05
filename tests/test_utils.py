"""Tests for automcp.utils module."""

import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest
import yaml

from automcp.utils import generate_test_report, load_config, run_tests


class TestLoadConfig:
    """Tests for the load_config function."""

    def test_load_yaml_config(self, tmp_path):
        """Test loading a YAML configuration file."""
        # Create a temporary YAML config file
        config_data = {
            "name": "test-service",
            "description": "Test service",
            "groups": {
                "test_module.TestGroup": {
                    "name": "test-group",
                    "description": "A test group",
                }
            },
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        # Load the config
        config = load_config(config_path)

        # Check the config values
        assert config.name == "test-service"
        assert config.description == "Test service"
        assert len(config.groups) == 1
        assert "test_module.TestGroup" in config.groups
        assert config.groups["test_module.TestGroup"].name == "test-group"
        assert config.groups["test_module.TestGroup"].description == "A test group"

    def test_load_json_config(self, tmp_path):
        """Test loading a JSON configuration file."""
        # Create a temporary JSON config file
        config_data = {
            "name": "test-group",
            "description": "A test group",
            "packages": ["package1", "package2"],
            "config": {"key1": "value1"},
            "env_vars": {"ENV1": "value1"},
        }
        config_path = tmp_path / "config.json"
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Load the config
        config = load_config(config_path)

        # Check the config values
        assert config.name == "test-group"
        assert config.description == "A test group"
        assert config.packages == ["package1", "package2"]
        assert config.config == {"key1": "value1"}
        assert config.env_vars == {"ENV1": "value1"}

    def test_config_not_found(self, tmp_path):
        """Test loading a non-existent configuration file."""
        config_path = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            load_config(config_path)

    def test_invalid_format(self, tmp_path):
        """Test loading a file with an unsupported format."""
        config_path = tmp_path / "config.txt"
        config_path.touch()
        with pytest.raises(ValueError, match="Unsupported file format"):
            load_config(config_path)

    def test_invalid_content(self, tmp_path):
        """Test loading a file with invalid content."""
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(ValueError):
            load_config(config_path)


class TestGenerateTestReport:
    """Tests for the generate_test_report function."""

    def test_generate_report_defaults(self, tmp_path):
        """Test generating a report with default settings."""
        # Set a custom output path in the temporary directory
        output_path = tmp_path / "report.md"

        # Generate the report
        result_path = generate_test_report(0, output_path=output_path)

        # Check the result
        assert result_path == output_path
        assert output_path.exists()

        # Check report content
        content = output_path.read_text()

        # Basic checks
        assert "# AutoMCP Test Report" in content
        assert "✅ All tests passed!" in content
        assert "**Server Loading Tests**" in content
        assert "**Schema Validation Tests**" in content
        assert "**Timeout Handling Tests**" in content
        assert "**Integration Tests**" in content
        assert "## Conclusion" in content

        # Date check - ensure the current date is in the report
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in content

    def test_generate_report_with_failure(self, tmp_path):
        """Test generating a report with test failures."""
        output_path = tmp_path / "report.md"
        result_path = generate_test_report(1, output_path=output_path)

        content = output_path.read_text()
        assert "❌ Some tests failed!" in content

    def test_generate_report_custom_areas(self, tmp_path):
        """Test generating a report with custom test areas."""
        output_path = tmp_path / "report.md"

        # Define custom test areas
        test_areas = [
            {"name": "Custom Area 1", "items": ["Test 1", "Test 2", "Test 3"]},
            {"name": "Custom Area 2", "items": ["Test A", "Test B"]},
        ]

        result_path = generate_test_report(
            0, output_path=output_path, test_areas=test_areas
        )

        content = output_path.read_text()
        assert "**Custom Area 1**" in content
        assert "- Test 1" in content
        assert "**Custom Area 2**" in content
        assert "- Test B" in content
        assert (
            "**Server Loading Tests**" not in content
        )  # Should not include default areas

    def test_generate_report_custom_title(self, tmp_path):
        """Test generating a report with a custom title."""
        output_path = tmp_path / "report.md"
        custom_title = "My Custom Test Report"

        result_path = generate_test_report(
            0, output_path=output_path, title=custom_title
        )

        content = output_path.read_text()
        assert f"# {custom_title}" in content
        assert "# AutoMCP Test Report" not in content

    def test_generate_report_no_coverage_info(self, tmp_path):
        """Test generating a report without coverage information."""
        output_path = tmp_path / "report.md"

        result_path = generate_test_report(
            0, output_path=output_path, include_coverage_info=False
        )

        content = output_path.read_text()
        assert "For coverage information" not in content
        assert "pytest --cov" not in content

    def test_generate_report_no_conclusion(self, tmp_path):
        """Test generating a report without a conclusion."""
        output_path = tmp_path / "report.md"

        result_path = generate_test_report(
            0, output_path=output_path, include_conclusion=False
        )

        content = output_path.read_text()
        assert "## Conclusion" not in content

    def test_generate_report_default_path(self, monkeypatch):
        """Test generating a report with the default output path."""
        # Use a mock to avoid creating an actual file
        mock_open = mock.mock_open()
        mock_file = mock.MagicMock()

        with mock.patch("builtins.open", mock_open):
            with mock.patch("pathlib.Path.cwd", return_value=Path("/mock/cwd")):
                with mock.patch("pathlib.Path.write_text"):
                    with mock.patch(
                        "pathlib.Path.__truediv__",
                        return_value=Path("/mock/cwd/TEST_REPORT.md"),
                    ):
                        result_path = generate_test_report(0)

        assert str(result_path) == "/mock/cwd/TEST_REPORT.md"


class TestRunTests:
    """Tests for the run_tests function."""

    @mock.patch("subprocess.run")
    def test_run_tests_default(self, mock_subprocess_run):
        """Test running tests with default settings."""
        # Mock the subprocess run result
        mock_subprocess_result = mock.MagicMock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stdout = "All tests passed!"
        mock_subprocess_result.stderr = ""
        mock_subprocess_run.return_value = mock_subprocess_result

        # Run the tests
        result = run_tests()

        # Check the subprocess call
        mock_subprocess_run.assert_called_once_with(
            ["pytest", "tests/"], capture_output=True, text=True
        )

        # Check the result
        assert result == 0

    @mock.patch("subprocess.run")
    def test_run_tests_custom_dir(self, mock_subprocess_run):
        """Test running tests with a custom test directory."""
        mock_subprocess_result = mock.MagicMock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stdout = "All tests passed!"
        mock_subprocess_result.stderr = ""
        mock_subprocess_run.return_value = mock_subprocess_result

        result = run_tests(test_dir="custom/tests/")

        mock_subprocess_run.assert_called_once_with(
            ["pytest", "custom/tests/"], capture_output=True, text=True
        )

        assert result == 0

    @mock.patch("subprocess.run")
    def test_run_tests_verbose(self, mock_subprocess_run):
        """Test running tests with verbose output."""
        mock_subprocess_result = mock.MagicMock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stdout = "Verbose output..."
        mock_subprocess_result.stderr = ""
        mock_subprocess_run.return_value = mock_subprocess_result

        result = run_tests(verbose=True)

        mock_subprocess_run.assert_called_once_with(
            ["pytest", "tests/", "-v"], capture_output=True, text=True
        )

        assert result == 0

    @mock.patch("subprocess.run")
    def test_run_tests_coverage(self, mock_subprocess_run):
        """Test running tests with coverage reporting."""
        mock_subprocess_result = mock.MagicMock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stdout = "Coverage report..."
        mock_subprocess_result.stderr = ""
        mock_subprocess_run.return_value = mock_subprocess_result

        result = run_tests(coverage=True)

        mock_subprocess_run.assert_called_once_with(
            ["pytest", "tests/", "--cov=automcp"], capture_output=True, text=True
        )

        assert result == 0

    @mock.patch("subprocess.run")
    def test_run_tests_html_coverage(self, mock_subprocess_run):
        """Test running tests with HTML coverage reporting."""
        mock_subprocess_result = mock.MagicMock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stdout = "HTML coverage report..."
        mock_subprocess_result.stderr = ""
        mock_subprocess_run.return_value = mock_subprocess_result

        result = run_tests(coverage=True, html_report=True)

        mock_subprocess_run.assert_called_once_with(
            ["pytest", "tests/", "--cov=automcp", "--cov-report=html"],
            capture_output=True,
            text=True,
        )

        assert result == 0

    @mock.patch("subprocess.run")
    def test_run_tests_custom_package(self, mock_subprocess_run):
        """Test running tests with a custom package for coverage."""
        mock_subprocess_result = mock.MagicMock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stdout = "Custom package coverage..."
        mock_subprocess_result.stderr = ""
        mock_subprocess_run.return_value = mock_subprocess_result

        result = run_tests(coverage=True, package="custom_package")

        mock_subprocess_run.assert_called_once_with(
            ["pytest", "tests/", "--cov=custom_package"], capture_output=True, text=True
        )

        assert result == 0

    @mock.patch("subprocess.run")
    def test_run_tests_failure(self, mock_subprocess_run):
        """Test running tests that fail."""
        mock_subprocess_result = mock.MagicMock()
        mock_subprocess_result.returncode = 1
        mock_subprocess_result.stdout = "Some tests failed!"
        mock_subprocess_result.stderr = "Error details"
        mock_subprocess_run.return_value = mock_subprocess_result

        result = run_tests()

        assert result == 1

    @mock.patch("subprocess.run")
    @mock.patch("time.time")
    def test_run_tests_timing(self, mock_time, mock_subprocess_run):
        """Test that the timing information is calculated correctly."""
        # Set up time.time to return different values on consecutive calls
        mock_time.side_effect = [100.0, 105.0]  # 5 seconds elapsed

        mock_subprocess_result = mock.MagicMock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stdout = "All tests passed!"
        mock_subprocess_result.stderr = ""
        mock_subprocess_run.return_value = mock_subprocess_result

        with mock.patch("builtins.print") as mock_print:
            result = run_tests()

            # Check if the elapsed time was printed
            elapsed_time_printed = False
            for call_args in mock_print.call_args_list:
                if call_args[0][0] == "\nTests completed in 5.00 seconds":
                    elapsed_time_printed = True
                    break

            assert elapsed_time_printed, "Elapsed time was not printed correctly"

        assert result == 0
