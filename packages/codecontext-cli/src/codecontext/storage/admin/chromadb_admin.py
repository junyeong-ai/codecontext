"""ChromaDB admin utilities for CLI commands.

This module provides lightweight HTTP-based admin operations for ChromaDB,
such as listing collections, deleting collections, and checking server status.

For full storage operations (add, query, update), use the storage provider plugin
(codecontext-storage-chromadb) instead.
"""

from typing import Any

import httpx


class ChromaDBAdminClient:
    """Lightweight HTTP client for ChromaDB admin operations.

    This client provides minimal admin functionality needed by CLI commands.
    It uses direct HTTP calls for maximum simplicity and minimal dependencies.

    For full storage provider functionality, use codecontext-storage-chromadb package.
    """

    def __init__(self, host: str = "localhost", port: int = 8000, timeout: float = 30.0) -> None:
        """Initialize admin client.

        Args:
            host: ChromaDB server host
            port: ChromaDB server port
            timeout: Request timeout in seconds
        """
        self.base_url = f"http://{host}:{port}/api/v2"
        self.client = httpx.Client(timeout=timeout)
        self.host = host
        self.port = port

    def heartbeat(self) -> dict[str, Any]:
        """Check if ChromaDB server is alive.

        Returns:
            Server heartbeat response

        Raises:
            httpx.ConnectError: If server is not reachable
            httpx.HTTPStatusError: If server returns error
        """
        from typing import cast

        response = self.client.get(f"{self.base_url}/heartbeat")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    def list_collections(self) -> list[dict[str, Any]]:
        """List all collections.

        Returns:
            List of collection metadata dictionaries

        Raises:
            httpx.HTTPStatusError: If server returns error
        """
        from typing import cast

        response = self.client.get(f"{self.base_url}/collections")
        response.raise_for_status()
        return cast(list[dict[str, Any]], response.json())

    def delete_collection(self, name: str) -> None:
        """Delete a collection.

        Args:
            name: Collection name to delete

        Raises:
            httpx.HTTPStatusError: If server returns error
        """
        response = self.client.delete(f"{self.base_url}/collections/{name}")
        response.raise_for_status()

    def count_collection(self, name: str) -> int:
        """Count items in a collection.

        Args:
            name: Collection name

        Returns:
            Number of items in collection

        Raises:
            httpx.HTTPStatusError: If server returns error
        """
        from typing import cast

        response = self.client.get(f"{self.base_url}/collections/{name}/count")
        response.raise_for_status()
        return cast(int, response.json())

    def close(self) -> None:
        """Close HTTP client connection."""
        self.client.close()

    def __enter__(self) -> "ChromaDBAdminClient":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: object,
    ) -> None:
        """Context manager exit."""
        self.close()
