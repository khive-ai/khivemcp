# verify_client.py
import sys

import anyio
import mcp.types as types  # For result type checking if needed
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def run_test(server_cmd: list[str]):
    print("\n--- Starting Test Run ---")
    print(f"Server command: {' '.join(server_cmd)}")

    server_params = StdioServerParameters(command=server_cmd[0], args=server_cmd[1:])

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("Client: Connecting...")
            async with ClientSession(read_stream, write_stream) as session:
                print("Client: Initializing session...")
                init_result = await session.initialize()
                print(
                    f"Client: Initialized. Server: {init_result.serverInfo.name} v{init_result.serverInfo.version}"
                )
                print(
                    f"Client: Server Capabilities: {init_result.capabilities.model_dump_json(indent=2)}"
                )

                # <<< --- Test Steps Go Here --- >>>
                await test_tool_list(session)
                await test_tool_calls_valid(session)
                await test_tool_calls_invalid(session)
                await test_tool_context(session)  # Assuming data-processor uses context
                await test_tool_error_handling(
                    session
                )  # Using our new test_error operation

                # If we got here, all tests passed
                print("Client: All tests passed for this run.")

    except Exception as e:
        print("\n--- CLIENT ERROR ---")
        print(f"An error occurred during the client test run: {type(e).__name__}: {e}")
        # Consider adding traceback print here if needed
        print("--------------------")
        raise  # Re-raise to indicate failure


async def test_tool_list(session: ClientSession):
    print("\nClient: Listing tools...")
    list_result = await session.list_tools()
    tool_names = [t.name for t in list_result.tools]
    print(f"Client: Found tools: {tool_names}")
    # Basic check: Ensure expected tools are present (adapt based on config used)
    assert "data-processor.process_data" in tool_names
    assert "data-processor.generate_report" in tool_names
    assert "data-processor.validate_schema" in tool_names
    assert "data-processor.test_error" in tool_names  # Check our new operation
    print("Client: [PASS] Tool list looks reasonable.")


async def test_tool_calls_valid(session: ClientSession):
    print("\nClient: Testing valid tool calls...")

    # Test process_data
    # For AutoMCP operations, FastMCP expects the first parameter to be ctx (which it handles)
    # We only need to pass the remaining parameters
    data_obj = {"data": [{"id": "t1", "value": "hello"}]}
    process_args = {
        "data": data_obj
    }  # Match the parameter name in the method signature

    print(f"Client: Calling data-processor.process_data with args: {process_args}")
    try:
        process_resp = await session.call_tool(
            "data-processor.process_data", arguments=process_args
        )
        print(f"Client: process_data response: {process_resp.content}")
        assert not process_resp.isError, "Call returned an error"
        assert isinstance(
            process_resp.content[0], types.TextContent
        ), "Expected TextContent response"
        # Add more specific checks on the content if needed, parsing the JSON string
        print("Client: [PASS] data-processor.process_data (valid args)")
    except Exception as e:
        print(
            f"Client: [FAIL] Error calling data-processor.process_data: {type(e).__name__}: {e}"
        )
        raise

    # Example for validate_schema
    # For this operation, we need to pass a request parameter
    request_obj = {
        "data": {"name": "test", "value": 123},
        "schema": {  # Corresponds to schema_def in Pydantic model
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "integer", "minimum": 100},
            },
            "required": ["name", "value"],
        },
    }
    validate_args = {"request": request_obj}

    print(f"Client: Calling data-processor.validate_schema with args: {validate_args}")
    try:
        validate_resp = await session.call_tool(
            "data-processor.validate_schema", arguments=validate_args
        )
        print(f"Client: validate_schema response: {validate_resp.content}")
        assert not validate_resp.isError, "Call returned an error"
        # Check response content for valid=True
        import json

        validate_result_dict = json.loads(validate_resp.content[0].text)
        assert (
            validate_result_dict.get("valid") is True
        ), "Expected validation to be successful"
        print("Client: [PASS] data-processor.validate_schema (valid args)")
    except Exception as e:
        print(
            f"Client: [FAIL] Error calling data-processor.validate_schema: {type(e).__name__}: {e}"
        )
        raise


async def test_tool_calls_invalid(session: ClientSession):
    print("\nClient: Testing invalid tool calls (expecting errors)...")
    # Test process_data with missing required field ('data')
    invalid_args = {"parameters": {}}
    print(
        f"Client: Calling data-processor.process_data with invalid args: {invalid_args}"
    )

    # In FastMCP's implementation, validation errors return isError=False but with an error message
    # containing validation error details, rather than raising McpError exceptions
    resp = await session.call_tool(
        "data-processor.process_data", arguments=invalid_args
    )
    print(f"Client: Response: {resp.content}")

    # Check if the response contains validation error message
    error_text = (
        resp.content[0].text
        if resp.content and isinstance(resp.content[0], types.TextContent)
        else ""
    )
    if "validation error" in error_text and "Field required" in error_text:
        print("Client: [PASS] Received expected validation error in response")
    else:
        print("Client: [FAIL] Expected validation error but got different response")
        assert False, "Expected validation error message in response"


async def test_tool_context(session: ClientSession):
    print("\nClient: Testing tool context usage (check server stderr)...")
    # Call a tool known to use ctx.info/report_progress (e.g., process_data)
    process_args = {"data": {"data": [{"id": "ctx_test", "value": 1}]}}
    print(
        f"Client: Calling data-processor.process_data (for context check) with args: {process_args}"
    )
    await session.call_tool("data-processor.process_data", arguments=process_args)
    print(
        "Client: Call complete. Manually check server's stderr output for '[DataProcessorGroup] Processing...' logs and progress reports."
    )
    # Note: Client doesn't automatically see logs/progress unless handler is setup
    print("Client: [INFO] Context test requires manual verification of server logs.")


async def test_tool_error_handling(session: ClientSession):
    print("\nClient: Testing internal tool error handling...")

    # Test with our new test_error operation
    tool_name_to_test = "data-processor.test_error"
    error_args = {"request": {"error_type": "value_error"}}
    print(f"Client: Calling {tool_name_to_test} with args: {error_args}")

    try:
        resp = await session.call_tool(tool_name_to_test, arguments=error_args)
        print(f"Client: {tool_name_to_test} response content: {resp.content}")

        # In FastMCP, errors from operation methods are returned as text responses
        # Check if the error message is in the response content
        error_text = (
            resp.content[0].text
            if resp.content and isinstance(resp.content[0], types.TextContent)
            else ""
        )

        if "Intentional test error: ValueError" in error_text:
            print("Client: [PASS] Received expected error message in response")
        else:
            print(
                "Client: [FAIL] Expected specific error message but got different response"
            )
            assert False, "Expected 'Intentional test error: ValueError' in response"

    except Exception as e:
        print(
            f"Client: [FAIL] Unexpected exception during error test: {type(e).__name__}: {e}"
        )
        assert False, "Unexpected exception"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_client.py <path_to_config_file>")
        sys.exit(1)

    config_path = sys.argv[1]
    # Construct the server command
    server_command = [sys.executable, "-m", "automcp.cli", config_path]

    try:
        anyio.run(run_test, server_command)
        print("\n--- Verification Client Finished Successfully ---")
    except Exception:
        print("\n--- Verification Client Finished With Errors ---")
        sys.exit(1)
