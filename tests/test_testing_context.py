"""Tests for the MockContext class."""

import pytest

from automcp.testing.context import MockContext


@pytest.fixture
def mock_context():
    """Create a MockContext instance for testing."""
    return MockContext()


def test_mock_context_initialization(mock_context):
    """Test that MockContext initializes correctly."""
    assert mock_context.progress_updates == []
    assert mock_context.info_messages == []
    assert mock_context.request_id is None
    assert mock_context.type == "text"
    assert mock_context.text == ""


def test_mock_context_info(mock_context):
    """Test the info method of MockContext."""
    mock_context.info("Test message")
    mock_context.info("Another message")

    assert len(mock_context.info_messages) == 2
    assert mock_context.info_messages[0] == "Test message"
    assert mock_context.info_messages[1] == "Another message"


@pytest.mark.asyncio
async def test_mock_context_report_progress(mock_context):
    """Test the report_progress method of MockContext."""
    await mock_context.report_progress(10, 100)
    await mock_context.report_progress(50, 100)
    await mock_context.report_progress(100, 100)

    assert len(mock_context.progress_updates) == 3
    assert mock_context.progress_updates[0] == (10, 100)
    assert mock_context.progress_updates[1] == (50, 100)
    assert mock_context.progress_updates[2] == (100, 100)


def test_mock_context_request_id(mock_context):
    """Test setting and getting the request_id attribute."""
    assert mock_context.request_id is None

    mock_context.request_id = "test-123"
    assert mock_context.request_id == "test-123"

    mock_context.request_id = "another-id"
    assert mock_context.request_id == "another-id"
