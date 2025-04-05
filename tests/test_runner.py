"""
Tests for the runner module.

This module contains tests for the run_server and _run_server_async functions
in the automcp.runner module.
"""

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from automcp.config import load_config
from automcp.exceptions import ConfigFormatError, ConfigNotFoundError
from automcp.runner import _run_server_async, run_server
from automcp.server import AutoMCPServer
from automcp.types import GroupConfig


# Fixtures
@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary valid config file for testing."""
    config_path = tmp_path / "test_config.json"
    config_data = {
        "name": "test-group",
        "description": "Test group for runner tests",
        "config": {},
    }
    with open(config_path, "w") as f:
        json.dump(config_data, f)
    return config_path


@pytest.fixture
def invalid_config_file(tmp_path):
    """Create a temporary invalid config file for testing."""
    config_path = tmp_path / "invalid_config.json"
    with open(config_path, "w") as f:
        f.write("{invalid json")
    return config_path


# Unit Tests for run_server
@patch("automcp.runner.asyncio.run")
def test_run_server_calls_async_implementation(
    mock_asyncio_run, temp_config_file
):
    """Test that run_server calls the async implementation with asyncio.run."""
    # Call the function
    run_server(temp_config_file)

    # Check that asyncio.run was called with _run_server_async
    mock_asyncio_run.assert_called_once()
    args, _ = mock_asyncio_run.call_args
    assert asyncio.iscoroutine(args[0])  # Check that it's a coroutine


@patch("automcp.runner.asyncio.run")
def test_run_server_handles_keyboard_interrupt(
    mock_asyncio_run, temp_config_file, capsys
):
    """Test that run_server handles KeyboardInterrupt gracefully."""
    # Make asyncio.run raise KeyboardInterrupt
    mock_asyncio_run.side_effect = KeyboardInterrupt()

    # Call the function
    run_server(temp_config_file)

    # Check that the function handled the interrupt gracefully
    captured = capsys.readouterr()
    assert "Server stopped by user" in captured.out


@patch("automcp.runner.asyncio.run")
def test_run_server_propagates_other_exceptions(
    mock_asyncio_run, temp_config_file
):
    """Test that run_server re-raises non-KeyboardInterrupt exceptions."""
    # Make asyncio.run raise a ValueError
    mock_asyncio_run.side_effect = ValueError("Test error")

    # Call the function and check that it raises an AutoMCPError
    with pytest.raises(Exception) as excinfo:
        run_server(temp_config_file)

    # Check that the original exception is included
    assert "Test error" in str(excinfo.value)


# Unit Tests for _run_server_async
@pytest.mark.asyncio
@patch("automcp.runner.load_config")
@patch("automcp.runner.AutoMCPServer")
async def test_run_server_async_loads_config(
    mock_server_cls, mock_load_config, temp_config_file
):
    """Test that _run_server_async loads the configuration correctly."""
    # Setup mocks
    mock_config = GroupConfig(name="test-group", config={})
    mock_load_config.return_value = mock_config

    mock_server = AsyncMock()
    mock_server_cls.return_value = mock_server

    # Make the server.start() method return immediately
    mock_server.start = AsyncMock()

    # Make the while True loop exit after one iteration
    with patch("automcp.runner.asyncio.sleep", side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            await _run_server_async(temp_config_file)

    # Check that load_config was called with the correct path
    mock_load_config.assert_called_once_with(temp_config_file)

    # Check that AutoMCPServer was created with the correct parameters
    mock_server_cls.assert_called_once_with(
        "test-group", mock_config, timeout=30.0
    )


@pytest.mark.asyncio
@patch("automcp.runner.load_config")
@patch("automcp.runner.AutoMCPServer")
async def test_run_server_async_starts_server(
    mock_server_cls, mock_load_config, temp_config_file
):
    """Test that _run_server_async starts the server correctly."""
    # Setup mocks
    mock_config = GroupConfig(name="test-group", config={})
    mock_load_config.return_value = mock_config

    mock_server = AsyncMock()
    mock_server_cls.return_value = mock_server

    # Make the while True loop exit after one iteration
    with patch("automcp.runner.asyncio.sleep", side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            await _run_server_async(temp_config_file)

    # Check that server.start was called
    mock_server.start.assert_called_once()


@pytest.mark.asyncio
@patch("automcp.runner.load_config")
@patch("automcp.runner.AutoMCPServer")
async def test_run_server_async_stops_server_on_exit(
    mock_server_cls, mock_load_config, temp_config_file
):
    """Test that _run_server_async stops the server when exiting."""
    # Setup mocks
    mock_config = GroupConfig(name="test-group", config={})
    mock_load_config.return_value = mock_config

    mock_server = AsyncMock()
    mock_server_cls.return_value = mock_server

    # Make the while True loop exit after one iteration
    with patch("automcp.runner.asyncio.sleep", side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            await _run_server_async(temp_config_file)

    # Check that server.stop was called
    mock_server.stop.assert_called_once()


@pytest.mark.asyncio
@patch("automcp.runner.load_config")
@patch("automcp.runner.AutoMCPServer")
async def test_run_server_async_handles_server_exception(
    mock_server_cls, mock_load_config, temp_config_file
):
    """Test that _run_server_async handles exceptions from the server."""
    # Setup mocks
    mock_config = GroupConfig(name="test-group", config={})
    mock_load_config.return_value = mock_config

    mock_server = AsyncMock()
    mock_server_cls.return_value = mock_server

    # Make server.start raise an exception
    mock_server.start.side_effect = RuntimeError("Server error")

    # Call the function and check that it raises the exception
    with pytest.raises(RuntimeError) as excinfo:
        await _run_server_async(temp_config_file)

    # Check that the original exception is included
    assert "Server error" in str(excinfo.value)

    # Check that server.stop was still called (cleanup)
    mock_server.stop.assert_called_once()


# Integration Tests
def test_run_server_with_config_not_found():
    """Test that run_server raises ConfigNotFoundError for non-existent config."""
    with pytest.raises(ConfigNotFoundError):
        run_server(Path("non_existent_config.json"))


def test_run_server_with_invalid_config(invalid_config_file):
    """Test that run_server raises ConfigFormatError for invalid config."""
    with pytest.raises(ConfigFormatError):
        run_server(invalid_config_file)


# Skip the integration test for now
@pytest.mark.skip(reason="Integration test requires more complex setup")
def test_integration_with_memory_transport(temp_config_file):
    """
    Integration test using in-memory transport.

    This test would create a real AutoMCPServer instance and connect it to a client
    using the in-memory transport, but it's skipped for now as it requires more
    complex setup.
    """
    pass
