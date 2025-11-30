"""
Test fixtures for AI Agent Response Format Optimization.

Provides sample responses in both v1 (old) and v2 (new) formats for testing.
"""

from typing import Any

# Sample Code Response (v1 - Old Format)
CODE_RESPONSE_V1: dict[str, Any] = {
    "results": [
        {
            "id": "abc1234567890def",
            "score": 0.87,
            "rank": 1,
            "source": "python/infra/mongodb.py",  # String, not structured
            "metadata": {
                "name": "get_mongodb_client",
                "type": "function",
                "language": "python",
                "start_line": 24,
                "end_line": 44,
            },
            "content": '''def get_mongodb_client() -> AsyncIOMotorClient:
    """MongoDB client singleton.

    Returns:
        AsyncIOMotorClient: Configured MongoDB client
    """
    global _mongodb_client
    if _mongodb_client is None:
        conn_string = settings.mongodb.mongodb_url
        _mongodb_client = AsyncIOMotorClient(
            conn_string,
            maxPoolSize=settings.mongodb.max_pool_size,
            minPoolSize=settings.mongodb.min_pool_size,
            serverSelectionTimeoutMS=5000
        )
        logger.debug(f"MongoDB client initialized: {conn_string}")
    return _mongodb_client''',  # Full content (~350 tokens)
            "related_nodes": [],  # Always empty
            "navigation": {  # Redundant navigation section
                "read_implementation": "READ python/infra/mongodb.py:24-44",
                "check_usage": "READ python/infra/mongodb.py:51",
                "check_config": "READ python/config/settings.py:MongoDBSettings",
                "find_tests": "SEARCH tests/**/test_mongodb.py",
            },
        }
    ]
}


# Sample Code Response (v2 - New Format)
CODE_RESPONSE_V2: dict[str, Any] = {
    "version": "2.0",  # NEW: version field
    "results": [
        {
            "id": "abc1234567890def",
            "score": 0.87,
            "rank": 1,
            "location": {  # NEW: structured location
                "file": "python/infra/mongodb.py",
                "start_line": 24,
                "end_line": 44,
                "url": "python/infra/mongodb.py:24-44",
            },
            "metadata": {
                "name": "get_mongodb_client",
                "type": "function",
                "signature": "() -> AsyncIOMotorClient",  # NEW: signature
                "language": "python",
                "parent": None,
            },
            "structure": {  # NEW: AST metadata
                "calls": [
                    {"name": "AsyncIOMotorClient", "line": 38, "external": True},
                    {"name": "logger.debug", "line": 43, "external": False},
                ],
                "references": [{"name": "settings.mongodb_url", "line": 25, "type": "config"}],
                "complexity": {"cyclomatic": 2, "lines": 21, "nesting_depth": 2},
            },
            "relationships": {  # NEW: populated from Relationships
                "callers": [
                    {
                        "name": "get_mongodb_database",
                        "location": "python/infra/mongodb.py:51-54",
                        "type": "direct_call",
                    }
                ],
                "callees": [{"name": "AsyncIOMotorClient", "package": "motor", "external": True}],
                "contains": [],
                "similar": [
                    {
                        "name": "get_redis_client",
                        "location": "python/infra/redis.py:20-35",
                        "similarity": 0.92,
                    }
                ],
            },
            "impact_stats": {  # NEW: computed metrics
                "direct_callers": 3,
                "total_callers": 8,
                "direct_callees": 2,
                "children": 0,
            },
            "snippet": {  # NEW: minimal snippet
                "essential": [
                    "def get_mongodb_client() -> AsyncIOMotorClient:",
                    "    client = AsyncIOMotorClient(settings.mongodb_url)",
                    "    return client",
                ],
                "full": None,  # Always null
            },
        }
    ],
    "total": 1,
    "query": "MongoDB connection",
}


# Sample Document Response (v1 - Old Format)
DOCUMENT_RESPONSE_V1: dict[str, Any] = {
    "results": [
        {
            "id": "doc123",
            "score": 0.89,
            "rank": 1,
            "source": "docs/order-dispatch-lifecycle.md",
            "metadata": {
                "type": "document",
                "name": "Order Dispatch Lifecycle",
                "language": "markdown",
            },
            "content": """# Order Dispatch Lifecycle

## Order Creation Flow

When OMS receives a new order request, the following steps occur:
1. Validation of order data
2. Price calculation and freight rate estimation
3. Driver assignment based on location
4. Order persistence to database

The `OmsOrderCommandController.createOrderForOms` method handles this flow.

## Driver Assignment

Automated driver assignment based on proximity...""",  # Full content (~200 tokens)
            "related_nodes": [],
        }
    ]
}


# Sample Document Response (v2 - New Format)
DOCUMENT_RESPONSE_V2: dict[str, Any] = {
    "version": "2.0",
    "results": [
        {
            "id": "doc1234567890abc",
            "score": 0.89,
            "rank": 1,
            "location": {
                "file": "docs/order-dispatch-lifecycle.md",
                "section": "Order Creation Flow",
                "start_line": 15,
                "end_line": 45,
                "url": "docs/order-dispatch-lifecycle.md:15-45#order-creation-flow",
            },
            "metadata": {
                "title": "## Order Creation Flow",
                "keywords": ["order", "creation", "validation", "persistence"],
                "type": "markdown_section",
                "language": "markdown",
            },
            "related_code": [
                {
                    "name": "OmsOrderCommandController.createOrderForOms",
                    "location": "kotlin/order/OmsOrderCommandController.kt:45-78",
                    "match_reason": "mentioned in section",
                },
                {
                    "name": "SaveOrderContext",
                    "location": "kotlin/order/SaveOrderContext.kt:10-50",
                    "match_reason": "referenced in diagram",
                },
            ],
            "related_sections": [
                {
                    "title": "Driver Assignment",
                    "location": "docs/order-dispatch-lifecycle.md:78-120",
                    "similarity": 0.75,
                },
                {
                    "title": "Freight Calculation",
                    "location": "docs/freight-calculation-flow.md:20-50",
                    "similarity": 0.68,
                },
            ],
            "snippet": {
                "preview": [
                    "## Order Creation Flow",
                    "",
                    "When OMS receives a new order request, the following steps occur:",
                    "1. Validation of order data",
                    "2. Price calculation and freight rate estimation",
                ],
                "full": None,
            },
        }
    ],
    "total": 1,
    "query": "order creation flow",
}


# Sample Relationships (for testing)
SAMPLE_RELATIONSHIPS = [
    {
        "source_id": "abc1234567890def",
        "source_name": "main",
        "source_type": "function",
        "source_file": "src/app.py",
        "source_line": 10,
        "target_id": "get_mongodb_database",
        "target_name": "get_mongodb_database",
        "target_type": "function",
        "target_file": "src/db.py",
        "target_line": 25,
        "relation_type": "CALLS",
    },
    {
        "source_id": "get_mongodb_database",
        "source_name": "get_mongodb_database",
        "source_type": "function",
        "source_file": "src/db.py",
        "source_line": 25,
        "target_id": "abc1234567890def",
        "target_name": "main",
        "target_type": "function",
        "target_file": "src/app.py",
        "target_line": 10,
        "relation_type": "CALLS",
    },
    {
        "source_id": "abc1234567890def",
        "source_name": "main",
        "source_type": "function",
        "source_file": "src/app.py",
        "source_line": 10,
        "target_id": "AsyncIOMotorClient",
        "target_name": "AsyncIOMotorClient",
        "target_type": "class",
        "target_file": "motor/core.py",
        "target_line": 1,
        "relation_type": "CALLS",
    },
]


# Token count estimates
TOKEN_ESTIMATES = {
    "v1_code": 500,  # Old format with full content
    "v2_code": 150,  # New format with minimal metadata
    "v1_document": 200,  # Old format document
    "v2_document": 120,  # New format document
    "reduction_percentage": 61,  # Target reduction
}
