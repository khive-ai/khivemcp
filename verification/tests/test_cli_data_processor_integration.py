"""Integration tests for DataProcessorGroup via the enhanced AutoMCP CLI."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from automcp.server import AutoMCPServer
from automcp.types import GroupConfig
from verification.groups.data_processor_group import DataProcessorGroup
from verification.tests.test_helpers import (
    create_connected_automcp_server_and_client_session,
)


class TestDataProcessorGroupCLIIntegration:
    """Test DataProcessorGroup integration with the enhanced AutoMCP CLI."""

    @pytest.fixture
    def config_path(self):
        """Return the path to the DataProcessorGroup config file."""
        return Path("verification/config/data_processor_group.json")

    @pytest.fixture
    def sample_data(self):
        """Return sample data for testing DataProcessorGroup operations."""
        return {
            "data": [
                {
                    "id": "cli-test-1",
                    "value": "Test Data",
                    "metadata": {"source": "cli-test", "priority": "high"},
                },
                {
                    "id": "cli-test-2",
                    "value": 42,
                    "metadata": {"source": "cli-test", "priority": "medium"},
                },
            ],
            "parameters": {"transform_case": "upper", "aggregate": True},
        }

    @pytest.mark.asyncio
    async def test_server_startup_with_data_processor_group(self, config_path):
        """Test that the server properly loads and registers the DataProcessorGroup."""
        # Load the configuration
        with open(config_path, "r") as f:
            config_data = json.load(f)

        config = GroupConfig(**config_data)
        server = AutoMCPServer("test-server", config)

        # Normally the CLI would do this, we'll simulate that behavior
        data_processor_group = DataProcessorGroup()
        data_processor_group.config = config
        server.groups["data-processor"] = data_processor_group

        # Create a connected server and client session
        async with create_connected_automcp_server_and_client_session(server) as (
            _,
            client,
        ):
            # Get the list of available tools
            tools_result = await client.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]

            # Verify the DataProcessorGroup operations are available
            assert "data-processor.process_data" in tool_names
            assert "data-processor.generate_report" in tool_names
            assert "data-processor.validate_schema" in tool_names

    @pytest.mark.asyncio
    async def test_process_data_operation_via_server(self, config_path, sample_data):
        """Test calling the process_data operation via a server instance."""
        # Load the configuration
        with open(config_path, "r") as f:
            config_data = json.load(f)

        config = GroupConfig(**config_data)
        server = AutoMCPServer("test-server", config)

        # Register the group manually as the CLI would do
        data_processor_group = DataProcessorGroup()
        data_processor_group.config = config
        server.groups["data-processor"] = data_processor_group

        # Create a connected server and client session
        async with create_connected_automcp_server_and_client_session(server) as (
            _,
            client,
        ):
            # Call the process_data operation
            response = await client.call_tool(
                "data-processor.process_data", sample_data
            )
            response_text = response.content[0].text if response.content else ""

            # Verify the response
            assert "TEST DATA" in response_text
            assert "cli-test-1" in response_text
            assert "processed_items" in response_text
            assert "aggregated" in response_text

    @pytest.mark.stdio_mode
    def test_stdio_mode_pipe_communication(self, config_path, sample_data):
        """Test communication with the server in stdio mode using pipes."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as input_file:
            # Prepare an MCP request in JSON-RPC format
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"client_name": "test-client", "client_version": "1.0.0"},
            }
            input_file.write(json.dumps(request) + "\n")

            # Add a request to list tools
            request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "mcp/list_tools",
                "params": {},
            }
            input_file.write(json.dumps(request) + "\n")

            input_file.flush()
            input_file_path = input_file.name

        try:
            # Run the CLI in stdio mode with prepared input
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "automcp.cli",
                    "run",
                    str(config_path),
                    "--mode",
                    "stdio",
                ],
                stdin=open(input_file_path, "r"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = proc.communicate(timeout=5)

            # Check the stdout for JSON-RPC responses
            assert "jsonrpc" in stdout

            # Parse the responses
            responses = []
            for line in stdout.strip().split("\n"):
                if line.strip():
                    try:
                        responses.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

            # Verify initialize response
            assert any(resp.get("id") == 1 for resp in responses)

            # Verify list_tools response
            tools_response = next(
                (resp for resp in responses if resp.get("id") == 2), None
            )
            assert tools_response is not None

            # Check tools in response
            tools = tools_response.get("result", {}).get("tools", [])
            tool_names = [tool.get("name") for tool in tools]
            assert "data-processor.process_data" in tool_names
            assert "data-processor.generate_report" in tool_names
            assert "data-processor.validate_schema" in tool_names

            # Check stderr for the debug output
            assert "Available DataProcessorGroup operations" in stderr

        finally:
            # Clean up
            os.unlink(input_file_path)

    def test_environment_variable_configuration(self, config_path):
        """Test server configuration via environment variables."""
        env = os.environ.copy()
        env["AUTOMCP_SERVER_MODE"] = "normal"
        env["AUTOMCP_CONFIG_PATH"] = str(config_path)
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

            # Verify environment variable usage
            assert f"Using config file: {config_path.resolve()}" in combined_output
            assert "Available DataProcessorGroup operations" in combined_output
            assert "data-processor.process_data" in combined_output
            assert "data-processor.generate_report" in combined_output
            assert "data-processor.validate_schema" in combined_output

        except subprocess.TimeoutExpired:
            # Expected since server keeps running
            proc.kill()
            stdout, stderr = proc.communicate()
            combined_output = stdout + stderr

            # Verify environment variable usage
            assert f"Using config file: {config_path.resolve()}" in combined_output
            assert "Available DataProcessorGroup operations" in combined_output

    def test_verbose_flag_detailed_output(self, config_path):
        """Test that verbose flag provides detailed output."""
        proc = subprocess.Popen(
            [sys.executable, "-m", "automcp.cli", "run", str(config_path), "--verbose"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, stderr = proc.communicate(timeout=2)
            combined_output = stdout + stderr

            # Check for detailed DEBUG level logs
            assert "DEBUG" in combined_output
            assert "Available DataProcessorGroup operations" in combined_output
            # Each operation should be listed in verbose mode
            assert "data-processor.process_data" in combined_output
            assert "data-processor.generate_report" in combined_output
            assert "data-processor.validate_schema" in combined_output

        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            combined_output = stdout + stderr

            # Same checks
            assert "DEBUG" in combined_output
            assert "Available DataProcessorGroup operations" in combined_output

    def test_config_file_validation_error(self):
        """Test proper error handling for invalid configurations."""
        # Create a temporary invalid config file
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w+") as f:
            f.write('{"name": "invalid-config", "invalid_field": true}')
            f.flush()

            proc = subprocess.run(
                [sys.executable, "-m", "automcp.cli", "run", f.name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Check for proper error message
            assert proc.returncode != 0
            assert "Failed to load config" in proc.stdout + proc.stderr

    def test_exit_code_for_file_not_found(self):
        """Test that proper exit code is returned when config file is not found."""
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "automcp.cli",
                "run",
                "nonexistent_config_file.json",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Check exit code and error message
        assert proc.returncode != 0
        assert "Config file not found" in proc.stdout + proc.stderr
