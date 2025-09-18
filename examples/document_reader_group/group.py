"""
Document Reader Service Group for khivemcp
An async document processing service with stateful caching.
Replaces lionagi's ReaderTool with a scalable MCP service.
"""

import asyncio
import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import aiofiles
from khivemcp import ServiceGroup, operation
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ========================== Schemas ==========================

class OpenDocumentRequest(BaseModel):
    """Request to open a document from file path or URL."""

    path_or_url: str = Field(
        ...,
        description="Local file path or remote URL to open and convert to text"
    )

    extract_images: bool = Field(
        False,
        description="Whether to extract and describe images from the document"
    )

    extract_tables: bool = Field(
        True,
        description="Whether to extract tables in markdown format"
    )


class ReadDocumentRequest(BaseModel):
    """Request to read a partial slice from an already-opened document."""

    doc_id: str = Field(
        ...,
        description="Unique ID referencing a previously opened document (starts with 'DOC_' or 'DIR_')"
    )

    start_offset: Optional[int] = Field(
        None,
        description="Character start offset for partial reading. Defaults to 0 if omitted."
    )

    end_offset: Optional[int] = Field(
        None,
        description="Character end offset for partial reading. Reads to end if omitted."
    )

    @field_validator("start_offset", "end_offset", mode="before")
    @classmethod
    def validate_offsets(cls, v):
        """Ensure offsets are valid integers."""
        if v is None or v == {}:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None


class ListDirectoryRequest(BaseModel):
    """Request to list files in a directory."""

    directory: str = Field(
        ...,
        description="Directory path to list files from"
    )

    recursive: bool = Field(
        False,
        description="Whether to recursively list files in subdirectories"
    )

    file_types: Optional[list[str]] = Field(
        None,
        description="List only files with specific extensions (e.g., ['.py', '.txt'])"
    )

    max_files: Optional[int] = Field(
        1000,
        description="Maximum number of files to list (prevents overwhelming output)"
    )


class ClearCacheRequest(BaseModel):
    """Request to clear document cache."""

    force: bool = Field(
        False,
        description="Force clear even if documents are being read"
    )


# ========================== Service Group ==========================

def generate_doc_id(source: str, prefix: str = "DOC") -> str:
    """Generate a unique document ID from source path/URL."""
    hash_obj = hashlib.md5(source.encode())
    return f"{prefix}_{hash_obj.hexdigest()[:12]}"


class DocumentReaderServiceGroup(ServiceGroup):
    """
    Async document reader service with stateful caching.
    Provides document conversion, partial reading, and directory listing.
    """

    def __init__(self, config: dict | None = None):
        """Initialize the document reader service."""
        super().__init__(config=config)

        # Document cache: doc_id -> (temp_file_path, length, source)
        self.documents: Dict[str, Tuple[str, int, str]] = {}

        # Lazy-load converter to avoid import if not needed
        self._converter = None
        self._token_calculator = None

        # Configuration
        self.max_cache_size = config.get("max_cache_size", 100) if config else 100

        # Set up cache directory
        if config and config.get("cache_dir"):
            self.cache_dir = Path(config["cache_dir"])
        else:
            # Default to ~/.khivemcp.cache/reader/
            self.cache_dir = Path.home() / ".khivemcp.cache" / "reader"

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Use cache dir for temp files
        self.temp_dir = str(self.cache_dir / "temp")
        Path(self.temp_dir).mkdir(exist_ok=True)

        logger.info(
            f"[DocumentReaderService] Initialized with max_cache_size={self.max_cache_size}, "
            f"cache_dir={self.cache_dir}"
        )

    @property
    def converter(self):
        """Lazy-load the document converter."""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter
                self._converter = DocumentConverter()
                logger.info("[DocumentReaderService] Docling converter initialized")
            except ImportError as e:
                logger.error(f"[DocumentReaderService] Failed to import docling: {e}")
                raise ImportError(
                    "docling is required for document conversion. "
                    "Install with: pip install docling"
                ) from e
        return self._converter

    async def _save_to_temp(self, text: str, doc_id: str, source: str) -> dict:
        """Save text to a temporary file and cache the reference."""
        # Check cache size and evict oldest if needed
        if len(self.documents) >= self.max_cache_size:
            # Simple FIFO eviction for now
            oldest = next(iter(self.documents))
            old_path, _, _ = self.documents.pop(oldest)
            try:
                os.unlink(old_path)
                logger.debug(f"[DocumentReaderService] Evicted cached document: {oldest}")
            except Exception as e:
                logger.warning(f"[DocumentReaderService] Failed to delete temp file: {e}")

        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            mode="w",
            encoding="utf-8",
            dir=self.temp_dir,
            prefix=f"{doc_id}_",
            suffix=".txt"
        )

        # Write content asynchronously
        async with aiofiles.open(temp_file.name, mode="w", encoding="utf-8") as f:
            await f.write(text)

        doc_len = len(text)

        # Store in cache
        self.documents[doc_id] = (temp_file.name, doc_len, source)

        # Calculate tokens (rough approximation)
        num_tokens = len(text) // 4  # Simple approximation: 1 token ≈ 4 characters

        logger.info(
            f"[DocumentReaderService] Cached document {doc_id}: "
            f"{doc_len} chars, ~{num_tokens} tokens"
        )

        return {
            "doc_id": doc_id,
            "length": doc_len,
            "num_tokens": num_tokens,
            "source": source,
            "doc_type": Path(source).suffix if "." in source else "unknown"
        }

    async def _convert_document(self, source: str) -> str:
        """Convert a document to markdown text asynchronously."""
        # Run CPU-intensive conversion in thread pool
        loop = asyncio.get_event_loop()

        def convert_sync():
            result = self.converter.convert(source)
            return result.document.export_to_markdown()

        text = await loop.run_in_executor(None, convert_sync)
        return text

    @operation(name="open_document", schema=OpenDocumentRequest)
    async def open_document(self, request: OpenDocumentRequest) -> dict:
        """
        Open and convert a document from file path or URL.
        Returns a doc_id for subsequent read operations.
        """
        try:
            doc_id = generate_doc_id(request.path_or_url)

            # Check if already cached
            if doc_id in self.documents:
                _, length, source = self.documents[doc_id]
                logger.info(f"[DocumentReaderService] Document already cached: {doc_id}")

                return {
                    "success": True,
                    "doc_info": {
                        "doc_id": doc_id,
                        "length": length,
                        "source": source,
                        "doc_type": Path(source).suffix if "." in source else "unknown"
                    },
                    "message": "Document already in cache"
                }

            # Convert document
            logger.info(f"[DocumentReaderService] Converting document: {request.path_or_url}")
            text = await self._convert_document(request.path_or_url)

            # Save to temp and cache
            doc_info = await self._save_to_temp(text, doc_id, request.path_or_url)

            return {
                "success": True,
                "doc_info": doc_info,
                "message": "Document successfully opened"
            }

        except Exception as e:
            logger.error(f"[DocumentReaderService] Failed to open document: {e}")
            return {
                "success": False,
                "error": f"Failed to open document: {str(e)}"
            }

    @operation(name="read_document", schema=ReadDocumentRequest)
    async def read_document(self, request: ReadDocumentRequest) -> dict:
        """
        Read a partial slice from a previously opened document.
        Supports pagination through start_offset and end_offset.
        """
        try:
            # Check if document exists in cache
            if request.doc_id not in self.documents:
                return {
                    "success": False,
                    "error": f"Document not found: {request.doc_id}. Please open it first."
                }

            file_path, doc_length, source = self.documents[request.doc_id]

            # Validate and clamp offsets
            start = max(0, request.start_offset if request.start_offset is not None else 0)
            end = min(doc_length, request.end_offset if request.end_offset is not None else doc_length)

            if start >= end:
                return {
                    "success": False,
                    "error": f"Invalid offsets: start={start} >= end={end}"
                }

            # Read the requested slice asynchronously
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                await f.seek(start)
                content = await f.read(end - start)

            has_more = end < doc_length

            logger.debug(
                f"[DocumentReaderService] Read {request.doc_id} "
                f"[{start}:{end}] ({len(content)} chars)"
            )

            return {
                "success": True,
                "chunk": {
                    "content": content,
                    "start_offset": start,
                    "end_offset": end,
                    "has_more": has_more
                },
                "message": f"Read {len(content)} characters"
            }

        except Exception as e:
            logger.error(f"[DocumentReaderService] Failed to read document: {e}")
            return {
                "success": False,
                "error": f"Failed to read document: {str(e)}"
            }

    @operation(name="list_directory", schema=ListDirectoryRequest)
    async def list_directory(self, request: ListDirectoryRequest) -> dict:
        """
        List files in a directory and store as a document for reading.
        Supports recursive listing and file type filtering.
        """
        try:
            directory = Path(request.directory)

            if not directory.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {request.directory}"
                }

            if not directory.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {request.directory}"
                }

            # Collect files asynchronously
            loop = asyncio.get_event_loop()

            def collect_files_sync():
                files = []
                pattern = "**/*" if request.recursive else "*"

                for path in directory.glob(pattern):
                    if path.is_file():
                        # Check file type filter
                        if request.file_types:
                            if not any(path.suffix == ext for ext in request.file_types):
                                continue

                        files.append(str(path.relative_to(directory)))

                        # Respect max_files limit
                        if len(files) >= request.max_files:
                            break

                return files

            files = await loop.run_in_executor(None, collect_files_sync)

            # Format as text document
            files_text = f"Directory listing: {request.directory}\n"
            files_text += f"Found {len(files)} files\n"
            files_text += "-" * 40 + "\n"
            files_text += "\n".join(files)

            # Save as document
            doc_id = generate_doc_id(request.directory, prefix="DIR")
            doc_info = await self._save_to_temp(files_text, doc_id, request.directory)

            logger.info(
                f"[DocumentReaderService] Listed directory {request.directory}: "
                f"{len(files)} files"
            )

            return {
                "success": True,
                "doc_info": doc_info,
                "file_count": len(files)
            }

        except Exception as e:
            logger.error(f"[DocumentReaderService] Failed to list directory: {e}")
            return {
                "success": False,
                "error": f"Failed to list directory: {str(e)}"
            }

    @operation(name="clear_cache", schema=ClearCacheRequest)
    async def clear_cache(self, request: ClearCacheRequest) -> dict:
        """Clear all cached documents and temporary files."""
        try:
            count = len(self.documents)

            for doc_id, (file_path, _, _) in list(self.documents.items()):
                try:
                    os.unlink(file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {file_path}: {e}")

            self.documents.clear()

            # Clean up temp directory if requested
            if request.force:
                import shutil
                try:
                    shutil.rmtree(self.temp_dir)
                    Path(self.temp_dir).mkdir(exist_ok=True)
                    logger.info(f"[DocumentReaderService] Cleaned temp directory: {self.temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean temp directory: {e}")

            logger.info(f"[DocumentReaderService] Cleared {count} cached documents")

            return {
                "success": True,
                "message": f"Cleared {count} cached documents",
                "cache_dir": str(self.cache_dir)
            }

        except Exception as e:
            logger.error(f"[DocumentReaderService] Failed to clear cache: {e}")
            return {
                "success": False,
                "error": f"Failed to clear cache: {str(e)}"
            }

    @operation(name="list_cached")
    async def list_cached_documents(self, request: dict = None) -> dict:
        """List all currently cached documents."""
        try:
            cached = []
            for doc_id, (file_path, length, source) in self.documents.items():
                cached.append({
                    "doc_id": doc_id,
                    "source": source,
                    "length": length,
                    "temp_file": file_path
                })

            return {
                "success": True,
                "cached_documents": cached,
                "count": len(cached),
                "max_cache_size": self.max_cache_size,
                "cache_dir": str(self.cache_dir)
            }

        except Exception as e:
            logger.error(f"[DocumentReaderService] Failed to list cached documents: {e}")
            return {
                "success": False,
                "error": f"Failed to list cache: {str(e)}"
            }

    async def cleanup(self):
        """Cleanup method called on service shutdown."""
        try:
            # Clean up temp files but keep the cache directory structure
            for doc_id, (file_path, _, _) in self.documents.items():
                try:
                    os.unlink(file_path)
                    logger.debug(f"[DocumentReaderService] Cleaned up temp file for {doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {file_path}: {e}")

            self.documents.clear()
            logger.info(f"[DocumentReaderService] Cleanup complete, cache directory preserved at {self.cache_dir}")

        except Exception as e:
            logger.error(f"[DocumentReaderService] Error during cleanup: {e}")