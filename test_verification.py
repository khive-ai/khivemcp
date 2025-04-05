import asyncio
from pathlib import Path

from automcp.verification import Verifier


async def run_verification():
    # Create a verifier with verbose output
    verifier = Verifier(verbose=True)

    # Define the operations to test for the data processor group
    operations = [
        {
            "name": "data-processor.process_data",
            "args": {"data": [{"id": 1, "value": 42}, {"id": 2, "value": 78}]},
            "expected": "Processed 2 items",
            "test_name": "Process data operation",
        },
        {
            "name": "data-processor.generate_report",
            "args": {"title": "Test Report", "data": [{"id": 1, "value": 42}]},
            "expected": "Test Report",
            "test_name": "Generate report operation",
        },
        {
            "name": "data-processor.validate_schema",
            "args": {
                "data": {"name": "Test User", "email": "test@example.com", "age": 30}
            },
            "expected": "valid",
            "test_name": "Validate schema operation",
        },
    ]

    # Run the environment check
    env_result = verifier.check_environment()
    print("\n=== Environment Check ===")
    print(env_result.detailed_report())

    # Test the data processor group
    config_path = Path("verification/config/data_processor_group.json")
    print(f"\n=== Testing {config_path.stem} ===")
    group_result = await verifier.test_group(config_path, operations)
    print(group_result.detailed_report())

    # Print overall results
    verifier.results = [env_result, group_result]
    verifier.print_results()


if __name__ == "__main__":
    asyncio.run(run_verification())
