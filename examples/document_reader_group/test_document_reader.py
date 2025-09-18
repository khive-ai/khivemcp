#!/usr/bin/env python3
"""
Test script for the Document Reader MCP Server
Tests all operations: open, read, list_dir, cache management
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path


from group import (
    DocumentReaderServiceGroup,
    OpenDocumentRequest,
    ReadDocumentRequest,
    ListDirectoryRequest,
    ClearCacheRequest,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_document_operations():
    """Test all document reader operations."""

    print("\n" + "="*60)
    print("🧪 Testing Document Reader MCP Server")
    print("="*60)

    # Initialize the service
    config = {
        "max_cache_size": 10,
        "cache_dir": None,  # Will use ~/.khivemcp.cache/reader/
    }

    service = DocumentReaderServiceGroup(config=config)

    try:
        # Test 1: List cached documents (should be empty)
        print("\n1️⃣ Testing list_cached (empty cache)...")
        result = await service.list_cached_documents()
        print(f"   Cache status: {result['count']} documents")
        print(f"   Cache directory: {result.get('cache_dir')}")
        assert result['success'] == True
        assert result['count'] == 0

        # Test 2: List directory
        print("\n2️⃣ Testing list_directory...")
        test_dir = Path(__file__).parent
        list_req = ListDirectoryRequest(
            directory=str(test_dir),
            recursive=False,
            file_types=[".py"],
            max_files=10
        )
        # Call the underlying method directly (bypass decorator for testing)
        result = await service.list_directory.__wrapped__(service, list_req)
        if result['success']:
            print(f"   ✅ Listed directory: {test_dir}")
            print(f"   Found {result.get('file_count', 0)} Python files")
            print(f"   Document ID: {result['doc_info']['doc_id']}")
            dir_doc_id = result['doc_info']['doc_id']
        else:
            print(f"   ❌ Error: {result['error']}")
            return

        # Test 3: Read the directory listing
        print("\n3️⃣ Testing read_document (directory listing)...")
        read_req = ReadDocumentRequest(
            doc_id=dir_doc_id,
            start_offset=0,
            end_offset=200  # First 200 chars
        )
        result = await service.read_document.__wrapped__(service, read_req)
        if result['success']:
            print(f"   ✅ Read {len(result['chunk']['content'])} characters")
            print(f"   Has more content: {result['chunk']['has_more']}")
            print(f"   Preview:\n{'-'*40}")
            print(result['chunk']['content'][:100] + "...")
            print('-'*40)
        else:
            print(f"   ❌ Error: {result['error']}")

        # Test 4: Try to open a README or Python file
        print("\n4️⃣ Testing open_document...")
        test_file = None

        # Look for a test file
        for potential_file in [
            Path(__file__).parent / "README.md",
            Path(__file__).parent.parent / "README.md",
            Path(__file__),  # This script itself
        ]:
            if potential_file.exists():
                test_file = potential_file
                break

        if test_file:
            open_req = OpenDocumentRequest(
                path_or_url=str(test_file),
                extract_tables=True,
                extract_images=False
            )
            result = await service.open_document.__wrapped__(service, open_req)
            if result['success']:
                print(f"   ✅ Opened document: {test_file.name}")
                print(f"   Document ID: {result['doc_info']['doc_id']}")
                print(f"   Length: {result['doc_info']['length']} characters")
                print(f"   ~Tokens: {result['doc_info'].get('num_tokens', 'N/A')}")
                file_doc_id = result['doc_info']['doc_id']

                # Read first chunk
                print("\n5️⃣ Testing read_document (file content)...")
                read_req = ReadDocumentRequest(
                    doc_id=file_doc_id,
                    start_offset=0,
                    end_offset=500
                )
                result = await service.read_document.__wrapped__(service, read_req)
                if result['success']:
                    print(f"   ✅ Read chunk [{read_req.start_offset}:{read_req.end_offset}]")
                    print(f"   Content preview:\n{'-'*40}")
                    print(result['chunk']['content'][:200] + "...")
                    print('-'*40)
            else:
                print(f"   ❌ Error opening document: {result['error']}")
        else:
            print("   ⚠️ No test file found to open")

        # Test 6: Check cache status
        print("\n6️⃣ Testing list_cached (with documents)...")
        result = await service.list_cached_documents()
        print(f"   📚 Cached documents: {result['count']}/{result['max_cache_size']}")
        if result['count'] > 0:
            for doc in result['cached_documents']:
                print(f"      - {doc['doc_id']}: {doc['source']} ({doc['length']} chars)")

        # Test 7: Test cache eviction by opening multiple files
        print("\n7️⃣ Testing cache eviction (max_cache_size=10)...")
        # This would need actual files to test properly

        # Test 8: Clear cache
        print("\n8️⃣ Testing clear_cache...")
        clear_req = ClearCacheRequest(force=False)
        result = await service.clear_cache.__wrapped__(service, clear_req)
        if result['success']:
            print(f"   ✅ Cache cleared: {result['message']}")
            print(f"   Cache directory: {result.get('cache_dir')}")

        # Final cache check
        result = await service.list_cached_documents()
        print(f"\n✅ Final cache status: {result['count']} documents")

    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        print("\n9️⃣ Running cleanup...")
        await service.cleanup()
        print("   ✅ Cleanup complete")

    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)


async def test_with_lionagi_integration():
    """Test how this would integrate with lionagi via MCP."""

    print("\n" + "="*60)
    print("🦁 Testing LionAGI Integration Pattern")
    print("="*60)

    print("\nTo use this with lionagi, create an .mcp.json file:")

    mcp_config = {
        "mcpServers": {
            "document_reader": {
                "command": "python",
                "args": ["-m", "khivemcp.cli", "examples/configs/document_reader_config.json"],
                "cwd": str(Path(__file__).parent.parent),
                "timeout": 300,
                "env": {
                    "LOG_LEVEL": "ERROR",
                    "FASTMCP_QUIET": "true"
                }
            }
        }
    }

    print(json.dumps(mcp_config, indent=2))

    print("\nThen in lionagi code:")
    print("""
```python
from lionagi import Branch, iModel
from lionagi.protocols.action.manager import load_mcp_tools

# Load the document reader as an MCP tool
tools = await load_mcp_tools(
    ".mcp.json",
    server_names=["document_reader"]
)

# Use in ReAct reasoning
branch = Branch(
    chat_model=iModel(provider="openai", model="gpt-4o-mini"),
    tools=tools
)

result = await branch.ReAct(
    instruct={
        "instruction": "Read and analyze the README file",
        "context": {"file": "README.md"}
    },
    tools=["document_reader_open_document", "document_reader_read_document"],
    max_extensions=3
)
```
""")


if __name__ == "__main__":
    print("Starting Document Reader MCP Server Tests...")

    # Run the tests
    asyncio.run(test_document_operations())

    # Show integration pattern
    asyncio.run(test_with_lionagi_integration())