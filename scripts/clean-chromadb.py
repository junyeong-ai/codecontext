#!/usr/bin/env python3
"""
Clean ChromaDB Collections Script

완벽한 재색인을 위해 모든 ChromaDB 컬렉션을 삭제합니다.

Usage:
    python scripts/clean-chromadb.py                    # 모든 컬렉션 삭제
    python scripts/clean-chromadb.py --pattern quality  # 패턴 매칭
    python scripts/clean-chromadb.py --dry-run          # 시뮬레이션
"""

import argparse
import sys
from typing import Any

import chromadb


def list_collections(client: chromadb.HttpClient) -> list[tuple[str, int]]:
    """List all collections with counts."""
    collections = client.list_collections()
    return [(c.name, c.count()) for c in collections]


def delete_collections(
    client: chromadb.HttpClient,
    pattern: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Delete collections matching pattern.

    Args:
        client: ChromaDB client
        pattern: Pattern to match collection names (None = all)
        dry_run: If True, only show what would be deleted

    Returns:
        Dict with deletion results
    """
    collections = list_collections(client)

    # Filter by pattern
    if pattern:
        collections = [(name, count) for name, count in collections if pattern in name]

    if not collections:
        return {
            "deleted": [],
            "total_items": 0,
            "dry_run": dry_run,
            "message": "No collections found matching pattern" if pattern else "No collections found",
        }

    total_items = sum(count for _, count in collections)

    print("\n" + "=" * 80)
    print(f"{'🔍 DRY RUN - ' if dry_run else ''}Collections to Delete")
    print("=" * 80)

    for name, count in collections:
        print(f"  • {name}: {count:,} items")

    print(f"\nTotal: {len(collections)} collections, {total_items:,} items")
    print("=" * 80)

    if dry_run:
        print("\n💡 Remove --dry-run to actually delete collections")
        return {
            "deleted": [],
            "total_items": total_items,
            "dry_run": True,
            "message": "Dry run completed",
        }

    # Confirm deletion
    print("\n⚠️  WARNING: This will permanently delete all data!")
    response = input("Continue? (yes/no): ")

    if response.lower() != "yes":
        print("\n❌ Deletion cancelled")
        return {
            "deleted": [],
            "total_items": 0,
            "dry_run": False,
            "message": "Deletion cancelled by user",
        }

    # Delete collections
    deleted = []
    print("\n🗑️  Deleting collections...")

    for name, count in collections:
        try:
            client.delete_collection(name=name)
            deleted.append(name)
            print(f"  ✅ Deleted: {name} ({count:,} items)")
        except Exception as e:
            print(f"  ❌ Failed: {name} - {e}")

    print(f"\n✅ Successfully deleted {len(deleted)}/{len(collections)} collections")

    return {
        "deleted": deleted,
        "total_items": total_items,
        "dry_run": False,
        "message": f"Deleted {len(deleted)} collections",
    }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean ChromaDB collections for fresh indexing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/clean-chromadb.py                       # Delete all collections (with confirmation)
  python scripts/clean-chromadb.py --dry-run             # Show what would be deleted
  python scripts/clean-chromadb.py --pattern quality     # Delete only quality test collections
  python scripts/clean-chromadb.py --pattern ecommerce   # Delete only ecommerce collections
        """,
    )

    parser.add_argument(
        "--pattern",
        type=str,
        help="Only delete collections matching this pattern (default: all)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="ChromaDB host (default: localhost)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="ChromaDB port (default: 8000)",
    )

    args = parser.parse_args()

    # Connect to ChromaDB
    try:
        client = chromadb.HttpClient(host=args.host, port=args.port)
        # Test connection
        client.heartbeat()
    except Exception as e:
        print(f"\n❌ Failed to connect to ChromaDB at {args.host}:{args.port}")
        print(f"   Error: {e}")
        print("\n💡 Start ChromaDB with: ./scripts/chroma-cli.sh start")
        return 1

    # Delete collections
    try:
        result = delete_collections(client, pattern=args.pattern, dry_run=args.dry_run)

        if result["dry_run"] or not result["deleted"]:
            return 0

        # Verify deletion
        remaining = list_collections(client)
        if remaining:
            print(f"\n📊 Remaining collections: {len(remaining)}")
            for name, count in remaining:
                print(f"  • {name}: {count:,} items")

        return 0

    except Exception as e:
        print(f"\n❌ Error during deletion: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
