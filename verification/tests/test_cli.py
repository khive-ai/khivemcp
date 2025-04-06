"""Tests for the enhanced AutoMCP CLI."""

import os
import subprocess
import sys
import tempfile
from unittest import mock

import pytest
from typer.testing import CliRunner

from automcp.cli import app


# Helper functions for CLI testing
def run_cli_command(command_args, env=None, check_exit_code=True):
    """Run CLI command as subprocess and return result."""
    if env is None:
        env = {}

    # Create a merged environment
    merged_env = os.environ.copy()
    merged_env.update(env)

    # Construct the full command
    module_path = "automcp.cli"
    full_command = [sys.executable, "-m", module_path] + command_args

    result = subprocess.run(
        full_command,
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if check_exit_code:
        assert (
            result.returncode == 0
        ), f"Command failed with code {result.returncode}\nStdout: {result.stdout}\nStderr: {result.stderr}"

    return result


# Typer-specific test runner
runner = CliRunner()


# Basic functionality tests
def test_run_command_normal_mode():
    """Test running CLI in normal mode."""
    # Use Typer's test runner since we just want to check command structure
    result = runner.invoke(
        app,
        ["run", "verification/config/data_processor_group.json", "--mode", "normal"],
    )
    assert "Starting server" in result.stdout


def test_run_command_with_verbose_flag():
    """Test running CLI with verbose flag."""
    # This will exit quickly since we're not in a proper test environment
    # so we just check that it accepts the verbose flag
    result = runner.invoke(
        app, ["run", "verification/config/data_processor_group.json", "--verbose"]
    )
    assert result.exit_code != 0  # It will exit with an error due to test environment
    assert "Starting server" in result.stdout


def test_environment_variable_config_path():
    """Test using environment variables for configuration path."""
    with mock.patch.dict(
        os.environ,
        {
            "AUTOMCP_CONFIG_PATH": "verification/config/data_processor_group.json",
        },
    ):
        result = runner.invoke(app, ["run"])
        assert "Using config file" in result.stdout


def test_environment_variable_server_mode():
    """Test using environment variables for server mode."""
    with mock.patch.dict(
        os.environ,
        {
            "AUTOMCP_SERVER_MODE": "stdio",
            "AUTOMCP_CONFIG_PATH": "verification/config/data_processor_group.json",
        },
    ):
        result = runner.invoke(app, ["run"])
        assert "in stdio mode" in result.stdout


# Error handling tests
def test_missing_config_file():
    """Test error handling when config file doesn't exist."""
    result = runner.invoke(app, ["run", "nonexistent.yaml"])
    assert result.exit_code != 0
    assert "Config file not found" in result.stdout


def test_invalid_config_file():
    """Test error handling with invalid config file."""
    # Create a temporary invalid config file
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w") as f:
        f.write("{invalid json")
        f.flush()

        result = runner.invoke(app, ["run", f.name])
        assert result.exit_code != 0
        assert "Failed to load config" in result.stdout


def test_invalid_server_mode():
    """Test error handling with invalid server mode."""
    result = runner.invoke(
        app,
        [
            "run",
            "verification/config/data_processor_group.json",
            "--mode",
            "invalid_mode",
        ],
    )
    assert "Unknown server mode" in result.stdout


def test_missing_specified_group():
    """Test error when requesting a group that doesn't exist in service config."""
    # Use multi_group.yaml since it's likely a service config with multiple groups
    result = runner.invoke(
        app,
        ["run", "verification/config/multi_group.yaml", "--group", "nonexistent-group"],
    )
    assert result.exit_code != 0
    assert "not found in service config" in result.stdout


# DataProcessorGroup integration tests
def test_data_processor_group_loading():
    """Test that the DataProcessorGroup is properly loaded and registered."""
    result = runner.invoke(
        app, ["run", "verification/config/data_processor_group.json", "--verbose"]
    )
    assert "DataProcessorGroup operations" in result.stdout


# Integration tests with subprocess
@pytest.mark.integration
def test_cli_subprocess_normal_mode():
    """Test running the CLI as a subprocess in normal mode."""
    # This test will time out after a few seconds since we don't handle the server lifecycle
    # Run with --mode normal to make it exit faster if no input is coming
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "automcp.cli",
            "run",
            "verification/config/data_processor_group.json",
            "--mode",
            "normal",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Give it a moment to start
    try:
        stdout, stderr = proc.communicate(timeout=2)
        # It might exit if stdin is closed
        assert "Starting server" in stdout + stderr
    except subprocess.TimeoutExpired:
        # This is expected since the server will keep running
        proc.kill()
        stdout, stderr = proc.communicate()
        assert "Starting server" in stdout + stderr


@pytest.mark.integration
def test_cli_subprocess_with_environment_variables():
    """Test running the CLI as a subprocess with environment variables."""
    # Set environment variables
    env = os.environ.copy()
    env["AUTOMCP_CONFIG_PATH"] = "verification/config/data_processor_group.json"
    env["AUTOMCP_SERVER_MODE"] = "normal"
    env["AUTOMCP_VERBOSE"] = "1"

    proc = subprocess.Popen(
        [sys.executable, "-m", "automcp.cli", "run"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        stdout, stderr = proc.communicate(timeout=2)
        combined_output = stdout + stderr
        assert "Using config file" in combined_output
        assert "Starting server" in combined_output
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        combined_output = stdout + stderr
        assert "Using config file" in combined_output
        assert "Starting server" in combined_output


# Tests using a mock server implementation to avoid actual server startup
@pytest.mark.unit
def test_auto_loading_of_data_processor_group():
    """Test auto-loading of DataProcessorGroup."""
    # Mock the server startup to check if DataProcessorGroup is registered correctly
    with (
        mock.patch("automcp.server.AutoMCPServer.start"),
        mock.patch("asyncio.run"),
        mock.patch("automcp.cli.run_mcp_server"),
    ):

        result = runner.invoke(
            app, ["run", "verification/config/data_processor_group.json"]
        )

        assert result.exit_code == 0
        # Since we've mocked the server startup, we can't check exact output
        # but we should see it trying to load the config
        assert "Loaded configuration" in result.stdout
