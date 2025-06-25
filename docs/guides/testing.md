# Testing khivemcp Servers

You can test your khivemcp-based code with normal Python testing frameworks like
**pytest**. Recommended approaches:

1. **Unit-test** each `ServiceGroup` method directly (bypassing MCP).
2. **Integration-test** an in-memory or local run of the server.

---

## 1. Unit Testing Operations

Since operations are just async Python methods:

```python
import pytest
from myapp.echo_group import EchoGroup, EchoRequest

@pytest.mark.asyncio
async def test_echo_message():
    group = EchoGroup(config={"message_prefix": "[Test] "})
    req = EchoRequest(message="Hello", uppercase=True)
    result = await group.echo_message(request=req)
    assert result["echoed"] == "[Test] HELLO"
```

- Create an instance of the group with your chosen config.
- Call the operation method directly with a valid request object (or dict).

---

## 2. Integration Testing the MCP Server

You can spin up a test server via `khivemcp run` in a subprocess, or via custom
fastmcp usage. Then use an MCP client to send requests. This ensures the entire
pipeline (loading config, operation registration, etc.) works.

A rough outline:

```python
import subprocess
import json
import pytest

@pytest.mark.integration
def test_server_echo():
    proc = subprocess.Popen(["khivemcp", "run", "echo_config.yaml"],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True)

    # (Write an MCP request to proc.stdin, read the response from proc.stdout)
    # For real usage, you'd implement or use an MCP client that speaks stdio.

    proc.terminate()
    proc.wait()
```

This is more complex but confirms end-to-end behavior.

---

## Mocking External Dependencies

If your group calls external APIs (HTTP, etc.), use standard Python mocking
(`unittest.mock.patch`) around those calls to ensure tests are reproducible
offline.

---

## Conclusion

- Basic **unit tests**: direct calls to the operation methods with a
  `request=...` object.
- **Integration tests**: optional, to confirm the CLI/config loading matches
  your expectations.
- Use standard Python testing patterns, as khivemcp does not require a special
  testing harness.
