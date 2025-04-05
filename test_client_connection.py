import asyncio

from automcp.client import AutoMCPClient


async def test_server():
    print("Connecting to server...")
    client = await AutoMCPClient.connect(
        "verification/config/data_processor_group.json"
    )
    print("Connected to server")

    tools = await client.list_tools()
    print(f"Available tools: {tools}")

    print("\nTesting process_data operation:")
    response = await client.call(
        "data-processor.process_data",
        {"data": [{"id": 1, "value": 42}, {"id": 2, "value": 78}]},
    )
    print(f"Process data response: {response}")

    print("\nTesting generate_report operation:")
    response = await client.call(
        "data-processor.generate_report",
        {"title": "Test Report", "data": [{"id": 1, "value": 42}]},
    )
    print(f"Generate report response: {response}")

    print("\nTesting validate_schema operation:")
    response = await client.call(
        "data-processor.validate_schema",
        {"data": {"name": "Test User", "email": "test@example.com", "age": 30}},
    )
    print(f"Validate schema response: {response}")

    await client.close()
    print("\nTest completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_server())
