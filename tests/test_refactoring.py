"""Tests for refactored AutoMCP core modules."""

import pytest
from pydantic import BaseModel

from automcp.client import parse_model_response, parse_text_response
from automcp.testing import VerificationResult


# Test the VerificationResult class
def test_verification_result():
    """Test VerificationResult class."""
    result = VerificationResult("Test Suite")

    # Add some test results
    result.add_result("Test 1", True, "Test passed")
    result.add_result("Test 2", False, "Test failed")
    result.add_result("Test 3", True, "Another test passed")
    result.add_result("Test 4", False, "Another test failed", skipped=True)

    # Check counts
    assert result.passed == 2
    assert result.failed == 1
    assert result.skipped == 1

    # Check summary
    summary = result.summary()
    assert "Test Suite" in summary
    assert "2 passed" in summary
    assert "1 failed" in summary
    assert "1 skipped" in summary

    # Check detailed report
    report = result.detailed_report()
    assert "Test Suite" in report
    assert "PASSED: Test 1" in report
    assert "FAILED: Test 2" in report
    assert "SKIPPED: Test 4" in report


# Test client module functions with mock responses
def test_client_parsing():
    """Test the client module's response parsing functions with mocks."""
    # Create a mock response with text content
    mock_text_response = type(
        "MockResponse",
        (),
        {"content": [type("TextContent", (), {"text": "Hello, World!"})()]},
    )()

    # Test text response parsing
    text = parse_text_response(mock_text_response)
    assert text == "Hello, World!"

    # Create a mock response with JSON content
    mock_json_response = type(
        "MockResponse",
        (),
        {
            "content": [
                type("TextContent", (), {"text": '{"message": "test", "count": 42}'})()
            ]
        },
    )()

    # Test model parsing with a custom model
    class TestResponse(BaseModel):
        message: str
        count: int

    model_result = parse_model_response(mock_json_response, TestResponse)
    assert isinstance(model_result, TestResponse)
    assert model_result.message == "test"
    assert model_result.count == 42
