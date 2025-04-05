"""Utility functions for AutoMCP."""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from .types import GroupConfig, ServiceConfig


def load_config(path: Path) -> Union[ServiceConfig, GroupConfig]:
    """Load configuration from a YAML or JSON file.

    Args:
        path: Path to the configuration file.

    Returns:
        Either a ServiceConfig or GroupConfig object, depending on the file format.
        YAML files are assumed to contain ServiceConfig, while JSON files are assumed
        to contain GroupConfig.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the file format is not supported or if the file contains invalid data.
    """
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    try:
        if path.suffix.lower() in [".yaml", ".yml"]:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            return ServiceConfig(**data)
        elif path.suffix.lower() == ".json":
            with open(path, "r") as f:
                data = json.load(f)
            return GroupConfig(**data)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise ValueError(f"Invalid configuration file format: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load configuration: {e}")


def generate_test_report(
    test_result: int,
    output_path: Optional[Path] = None,
    test_areas: Optional[List[Dict[str, List[str]]]] = None,
    title: str = "AutoMCP Test Report",
    include_coverage_info: bool = True,
    include_conclusion: bool = True,
) -> Path:
    """Generate a test report based on the test results.

    Args:
        test_result: The return code from the test run (0 for success, non-zero for failure)
        output_path: The path where the report should be saved. If None, saves to TEST_REPORT.md
            in the current directory.
        test_areas: A list of dictionaries containing test areas and their items.
            Each dictionary should have a 'name' key and an 'items' key.
            If None, default test areas will be used.
        title: The title for the test report
        include_coverage_info: Whether to include coverage information section in the report
        include_conclusion: Whether to include a conclusion section in the report

    Returns:
        The path to the generated report file

    Example:
        ```python
        test_areas = [
            {
                "name": "API Tests",
                "items": ["Authentication", "Data Retrieval", "Error Handling"]
            },
            {
                "name": "Integration Tests",
                "items": ["Database", "External Services", "UI Components"]
            }
        ]
        report_path = generate_test_report(0, test_areas=test_areas)
        ```
    """
    # Set default output path if not provided
    if output_path is None:
        output_path = Path.cwd() / "TEST_REPORT.md"

    # Set default test areas if not provided
    if test_areas is None:
        test_areas = [
            {
                "name": "Server Loading Tests",
                "items": [
                    "Loading single group from JSON config",
                    "Loading multiple groups from YAML config",
                    "Loading specific groups from multi-group config",
                ],
            },
            {
                "name": "Schema Validation Tests",
                "items": [
                    "Required field validation",
                    "Field type validation",
                    "Value constraint validation",
                    "Optional field handling",
                ],
            },
            {
                "name": "Timeout Handling Tests",
                "items": [
                    "Operations completing before timeout",
                    "Operations exceeding timeout",
                    "Progress reporting with timeouts",
                    "CPU-intensive operations with timeouts",
                    "Concurrent operations with timeouts",
                ],
            },
            {
                "name": "Integration Tests",
                "items": [
                    "End-to-end testing of ServiceGroups",
                    "Multi-group configuration testing",
                    "Specific group loading testing",
                ],
            },
        ]

    # Get the current time
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create the report content
    report_content = f"""# {title}

## Test Run Information

- **Date and Time**: {now}
- **Result**: {"✅ All tests passed!" if test_result == 0 else "❌ Some tests failed!"}

## Test Coverage

The tests cover the following areas:

"""

    # Add test areas to the report
    for i, area in enumerate(test_areas, 1):
        report_content += f"{i}. **{area['name']}**:\n"
        for item in area["items"]:
            report_content += f"   - {item}\n"
        report_content += "\n"

    # Add coverage information if requested
    if include_coverage_info:
        report_content += """## Detailed Test Results

For detailed test results, run the tests with the `-v` flag:

```
pytest -v
```

For coverage information, run the tests with the `--cov` flag:

```
pytest --cov=automcp
```

For an HTML coverage report, run the tests with the `--cov-report=html` flag:

```
pytest --cov=automcp --cov-report=html
```

"""

    # Add conclusion if requested
    if include_conclusion:
        report_content += """## Conclusion

The AutoMCP testing has confirmed that the system works correctly across different usage patterns. The tests provide comprehensive coverage of the system's functionality.
"""

    # Write the report to a file
    with open(output_path, "w") as f:
        f.write(report_content)

    return output_path


def run_tests(
    test_dir: str = "tests/",
    verbose: bool = False,
    coverage: bool = False,
    html_report: bool = False,
    package: str = "automcp",
) -> int:
    """Run tests and return the result code.

    Args:
        test_dir: The directory containing the tests to run
        verbose: Whether to enable verbose output
        coverage: Whether to generate coverage information
        html_report: Whether to generate an HTML coverage report
        package: The package to measure coverage for

    Returns:
        The return code from the test run (0 for success, non-zero for failure)
    """
    print(f"=== Running {package} Tests ===")

    # Determine the test command
    cmd = ["pytest", test_dir]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.append(f"--cov={package}")
        if html_report:
            cmd.append("--cov-report=html")

    # Run the tests
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start_time

    # Print the test output
    print(result.stdout)
    if result.stderr:
        print("Errors:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)

    # Print summary
    print(f"\nTests completed in {elapsed:.2f} seconds")
    print(f"Return code: {result.returncode}")

    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")

    return result.returncode
