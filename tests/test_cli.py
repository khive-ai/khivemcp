"""
Tests for the CLI module.

This module contains tests for the CLI commands in the automcp.cli module,
particularly the 'run' command that uses the run_server function.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from automcp.cli import run
from automcp.exceptions import (
    AutoMCPError,
    ConfigFormatError,
    ConfigNotFoundError,
)
from automcp.types import GroupConfig, ServiceConfig


# Fixtures
@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary valid config file for testing."""
    config_path = tmp_path / "test_config.json"
    config_data = {
        "name": "test-group",
        "description": "Test group for CLI tests",
        "config": {},
    }
    with open(config_path, "w") as f:
        json.dump(config_data, f)
    return config_path


# Basic functionality test
def test_run_function_basic(temp_config_file):
    """Test that the run function calls run_server with the correct parameters."""
    with patch("automcp.cli.run_server") as mock_run_server:
        # Call the run function directly
        run(config=temp_config_file, group=None, timeout=30.0)

        # Check that run_server was called with the correct parameters
        mock_run_server.assert_called_once()
        args, kwargs = mock_run_server.call_args
        assert kwargs["config_path"] == temp_config_file.resolve()
        assert kwargs["timeout"] == 30.0


def test_run_function_with_timeout(temp_config_file):
    """Test that the run function passes the timeout parameter correctly."""
    with patch("automcp.cli.run_server") as mock_run_server:
        # Call the run function directly with a custom timeout
        run(config=temp_config_file, group=None, timeout=60.0)

        # Check that run_server was called with the correct parameters
        mock_run_server.assert_called_once()
        args, kwargs = mock_run_server.call_args
        assert kwargs["config_path"] == temp_config_file.resolve()
        assert kwargs["timeout"] == 60.0


@patch("automcp.cli.load_config")
def test_run_function_with_group(mock_load_config, temp_config_file):
    """Test that the run function handles the group parameter correctly."""
    # Setup mock for load_config to return a ServiceConfig
    service_config = ServiceConfig(
        name="test-service",
        description="Test service",
        groups={
            "group1": GroupConfig(
                name="group1", description="Test group 1", config={}
            ),
            "group2": GroupConfig(
                name="group2", description="Test group 2", config={}
            ),
        },
    )
    mock_load_config.return_value = service_config

    with patch("automcp.cli.run_server") as mock_run_server:
        # Call the run function with a group
        run(config=temp_config_file, group="group1", timeout=30.0)

        # Check that load_config was called
        mock_load_config.assert_called_once_with(temp_config_file.resolve())

        # Check that run_server was called with the correct parameters
        mock_run_server.assert_called_once()
        args, kwargs = mock_run_server.call_args
        assert kwargs["config_path"] == temp_config_file.resolve()
        assert kwargs["timeout"] == 30.0


# Error handling tests
def test_run_function_handles_config_not_found(temp_config_file):
    """Test that the run function handles ConfigNotFoundError correctly."""
    with patch("automcp.cli.run_server") as mock_run_server:
        # Make run_server raise ConfigNotFoundError
        mock_run_server.side_effect = ConfigNotFoundError(
            "Config file not found"
        )

        # Mock typer.echo to check it's called with the correct message
        with patch("automcp.cli.typer.echo") as mock_echo:
            # Mock typer.Exit to prevent it from being raised
            with patch("automcp.cli.typer.Exit", side_effect=SystemExit):
                # Call the run function and expect SystemExit
                with pytest.raises(SystemExit):
                    run(config=temp_config_file, group=None, timeout=30.0)

                # Check that echo was called with the correct error message
                mock_echo.assert_called_with(
                    "Configuration error: Config file not found"
                )


def test_run_function_handles_config_format_error(temp_config_file):
    """Test that the run function handles ConfigFormatError correctly."""
    with patch("automcp.cli.run_server") as mock_run_server:
        # Make run_server raise ConfigFormatError
        mock_run_server.side_effect = ConfigFormatError(
            "Invalid config format"
        )

        # Mock typer.echo to check it's called with the correct message
        with patch("automcp.cli.typer.echo") as mock_echo:
            # Mock typer.Exit to prevent it from being raised
            with patch("automcp.cli.typer.Exit", side_effect=SystemExit):
                # Call the run function and expect SystemExit
                with pytest.raises(SystemExit):
                    run(config=temp_config_file, group=None, timeout=30.0)

                # Check that echo was called with the correct error message
                mock_echo.assert_called_with(
                    "Configuration format error: Invalid config format"
                )


def test_run_function_handles_server_error(temp_config_file):
    """Test that the run function handles AutoMCPError correctly."""
    with patch("automcp.cli.run_server") as mock_run_server:
        # Make run_server raise AutoMCPError
        mock_run_server.side_effect = AutoMCPError("Server error")

        # Mock typer.echo to check it's called with the correct message
        with patch("automcp.cli.typer.echo") as mock_echo:
            # Mock typer.Exit to prevent it from being raised
            with patch("automcp.cli.typer.Exit", side_effect=SystemExit):
                # Call the run function and expect SystemExit
                with pytest.raises(SystemExit):
                    run(config=temp_config_file, group=None, timeout=30.0)

                # Check that echo was called with the correct error message
                mock_echo.assert_called_with("Server error: Server error")


def test_run_function_handles_unexpected_error(temp_config_file):
    """Test that the run function handles unexpected errors correctly."""
    with patch("automcp.cli.run_server") as mock_run_server:
        # Make run_server raise an unexpected error
        mock_run_server.side_effect = ValueError("Unexpected error")

        # Mock typer.echo to check it's called with the correct message
        with patch("automcp.cli.typer.echo") as mock_echo:
            # Mock typer.Exit to prevent it from being raised
            with patch("automcp.cli.typer.Exit", side_effect=SystemExit):
                # Call the run function and expect SystemExit
                with pytest.raises(SystemExit):
                    run(config=temp_config_file, group=None, timeout=30.0)

                # Check that echo was called with the correct error message
                mock_echo.assert_called_with(
                    "Unexpected error: Unexpected error"
                )
