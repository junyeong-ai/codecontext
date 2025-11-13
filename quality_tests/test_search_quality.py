"""
Search Quality Tests  - Utility-Based Evaluation

Complete rewrite based on Ground Truth  design principles:
- Symbol-level evaluation (methods/classes, not files)
- Actionability scoring (how useful for AI agents)
- Essential coverage (implementation + domain + context)
- Precision (exact symbols found)

This replaces all legacy test infrastructure.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = [pytest.mark.quality, pytest.mark.search]


class SearchQualityEvaluator:
    """
    Utility-based search quality evaluator.

    Evaluates search results based on:
    1. Essential Coverage - Top-5 includes implementation + domain + context
    2. Actionability - Weighted utility score
    3. Precision - Exact symbols found
    """

    def __init__(self, ground_truth_path: Path):
        """Load ground truth  YAML."""
        with open(ground_truth_path) as f:
            self.gt_data = yaml.safe_load(f)

        self.queries = self.gt_data["ground_truth"]
        self.eval_criteria = self.gt_data["evaluation_criteria"]

    def search(self, query: str, limit: int = 10) -> dict[str, Any]:
        """Execute codecontext search via CLI."""
        result = subprocess.run(
            [
                "uv", "run", "codecontext", "search",
                query,
                "--limit", str(limit),
                "--format", "json"
            ],
            cwd="/Users/a16801/Workspace/codecontext/tests/fixtures/ecommerce_samples",
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            print(f"Search failed: {result.stderr}")
            return {"results": []}

        return json.loads(result.stdout)

    def evaluate_query(self, query_gt: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a single query."""
        query_id = query_gt["query_id"]
        query_text = query_gt["query"]

        print(f"\n{'='*100}")
        print(f"Evaluating {query_id}: {query_text}")
        print(f"{'='*100}")

        # Execute search
        search_results = self.search(query_text, limit=10)
        top5_results = search_results.get("results", [])[:5]

        # Extract essentials
        essentials = query_gt["essentials"]

        # Evaluate three dimensions
        coverage_score = self._evaluate_coverage(top5_results, essentials)
        actionability_score = self._evaluate_actionability(top5_results, essentials)
        precision_score = self._evaluate_precision(top5_results, essentials)

        # Print results
        self._print_evaluation(query_id, top5_results, essentials, coverage_score, actionability_score, precision_score)

        # Overall pass/fail
        passed = (
            coverage_score["score"] >= 3 and  # All 3 categories
            actionability_score["average"] >= 6.0 and  # Good threshold
            precision_score["rate"] >= 0.4  # Acceptable threshold (40%)
        )

        return {
            "query_id": query_id,
            "query": query_text,
            "coverage": coverage_score,
            "actionability": actionability_score,
            "precision": precision_score,
            "passed": passed
        }

    def _evaluate_coverage(self, top5_results: list[dict], essentials: dict) -> dict[str, Any]:
        """
        Check if top-5 includes:
        1. Implementation (method/class/component)
        2. Domain model OR documentation
        3. Context (any related code/doc)
        """
        has_implementation = False
        has_domain_or_doc = False
        has_context = False

        found_items = []

        for result in top5_results:
            path = result.get("path", result.get("file_path", ""))
            name = result.get("name", "")

            # Check implementation
            if "implementation" in essentials:
                for impl in essentials["implementation"]:
                    if impl["path"] in path:
                        # Check if it's the right symbol
                        if impl.get("symbol"):
                            symbol_name = impl["symbol"].split("::")[-1]  # Get method name
                            if symbol_name in name or impl["symbol"] in str(result):
                                has_implementation = True
                                found_items.append(f"impl: {impl['symbol']}")
                        else:
                            has_implementation = True
                            found_items.append(f"impl: {impl['path']}")

            # Check domain_model
            if "domain_model" in essentials:
                for domain in essentials["domain_model"]:
                    if domain["path"] in path:
                        symbol_name = domain.get("symbol", "")
                        if symbol_name in name or symbol_name in str(result):
                            has_domain_or_doc = True
                            found_items.append(f"domain: {domain['symbol']}")

            # Check documentation
            if "documentation" in essentials:
                for doc in essentials["documentation"]:
                    if doc["path"] in path:
                        has_domain_or_doc = True
                        found_items.append(f"doc: {doc['path']}")

            # Check context
            if "context" in essentials:
                for ctx in essentials["context"]:
                    if ctx.get("path", "") in path:
                        has_context = True
                        found_items.append(f"context: {ctx.get('symbol', ctx.get('path'))}")

        # If found implementation or domain, that counts as context too
        if has_implementation or has_domain_or_doc:
            has_context = True

        score = sum([has_implementation, has_domain_or_doc, has_context])

        return {
            "score": score,
            "max": 3,
            "has_implementation": has_implementation,
            "has_domain_or_doc": has_domain_or_doc,
            "has_context": has_context,
            "found_items": found_items
        }

    def _evaluate_actionability(self, top5_results: list[dict], essentials: dict) -> dict[str, Any]:
        """
        Calculate average actionability score.

        Weights:
        - method: 10
        - class: 9
        - component: 8
        - document_section: 6
        - interface: 5
        """
        weights = self.eval_criteria["actionability"]["weights"]
        scores = []

        for result in top5_results:
            result_type = result.get("type", "").lower()

            # Map result type to weight
            if "method" in result_type or "function" in result_type:
                scores.append(weights["method"])
            elif "class" in result_type:
                scores.append(weights["class"])
            elif "component" in result_type:
                scores.append(weights["component"])
            elif "document" in result_type or "markdown" in result_type:
                scores.append(weights["document_section"])
            elif "interface" in result_type or "protocol" in result_type:
                scores.append(weights["interface"])
            else:
                # Unknown type, assume medium utility
                scores.append(6)

        average = sum(scores) / len(scores) if scores else 0

        return {
            "average": average,
            "scores": scores,
            "excellent_threshold": self.eval_criteria["actionability"]["excellent_threshold"],
            "good_threshold": self.eval_criteria["actionability"]["good_threshold"]
        }

    def _evaluate_precision(self, top5_results: list[dict], essentials: dict) -> dict[str, Any]:
        """
        Calculate precision: percentage of essential symbols found in top-5.
        """
        total_essential_symbols = 0
        found_symbols = set()

        # Count all essential symbols (H1 priority)
        for category in ["implementation", "domain_model", "context", "documentation"]:
            if category in essentials:
                for item in essentials[category]:
                    if item.get("priority") == "H1":
                        symbol = item.get("symbol", item.get("path"))
                        total_essential_symbols += 1

                        # Check if found in top-5
                        for result in top5_results:
                            path = result.get("path", result.get("file_path", ""))
                            name = result.get("name", "")

                            if item.get("path", "") in path:
                                # Check symbol match
                                if symbol:
                                    symbol_name = symbol.split("::")[-1]
                                    if symbol_name in name or symbol in str(result):
                                        found_symbols.add(symbol)

        precision_rate = len(found_symbols) / total_essential_symbols if total_essential_symbols > 0 else 0

        return {
            "rate": precision_rate,
            "found": len(found_symbols),
            "total": total_essential_symbols,
            "found_symbols": list(found_symbols)
        }

    def _print_evaluation(
        self,
        query_id: str,
        top5_results: list[dict],
        essentials: dict,
        coverage: dict,
        actionability: dict,
        precision: dict
    ) -> None:
        """Print evaluation details."""
        print(f"\n📊 Top-5 Results:")
        for i, result in enumerate(top5_results, 1):
            path = result.get("path", result.get("file_path", ""))
            name = result.get("name", "")
            score = result.get("score", result.get("similarity", 0))
            result_type = result.get("type", "unknown")

            print(f"  {i}. [{result_type:12s}] {name:40s} (score: {score:.4f})")
            print(f"     {path}")

        print(f"\n📈 Evaluation Metrics:")
        print(f"  1. Essential Coverage: {coverage['score']}/3")
        print(f"     ✓ Implementation: {coverage['has_implementation']}")
        print(f"     ✓ Domain/Doc:     {coverage['has_domain_or_doc']}")
        print(f"     ✓ Context:        {coverage['has_context']}")
        if coverage['found_items']:
            print(f"     Found: {', '.join(coverage['found_items'][:3])}")

        print(f"\n  2. Actionability: {actionability['average']:.1f}/10")
        print(f"     Scores: {actionability['scores']}")
        status = "EXCELLENT" if actionability['average'] >= 8.0 else "GOOD" if actionability['average'] >= 6.0 else "WEAK"
        print(f"     Status: {status}")

        print(f"\n  3. Precision: {precision['rate']:.1%} ({precision['found']}/{precision['total']} symbols)")
        if precision['found_symbols']:
            print(f"     Found symbols: {', '.join(precision['found_symbols'][:3])}")

        status = "EXCELLENT" if precision['rate'] >= 0.8 else "GOOD" if precision['rate'] >= 0.6 else "ACCEPTABLE" if precision['rate'] >= 0.4 else "POOR"
        print(f"     Status: {status}")


class TestSearchQuality:
    """Search quality tests using Ground Truth ."""

    def test_all_queries(self) -> None:
        """Run evaluation on all 10 queries."""
        gt_path = Path("/Users/a16801/Workspace/codecontext/quality_tests/fixtures/ground_truth.yaml")

        if not gt_path.exists():
            pytest.skip("Ground truth  not found")

        evaluator = SearchQualityEvaluator(gt_path)

        results = []
        for query_gt in evaluator.queries:
            result = evaluator.evaluate_query(query_gt)
            results.append(result)

        # Print summary
        print(f"\n\n{'='*100}")
        print("FINAL SUMMARY")
        print(f"{'='*100}")

        passed = sum(1 for r in results if r["passed"])
        total = len(results)

        print(f"\nPassed: {passed}/{total} ({passed/total:.1%})")
        print(f"\nQuery Results:")
        for r in results:
            status = "✅ PASS" if r["passed"] else "❌ FAIL"
            print(f"  {r['query_id']}: {status}")
            print(f"    Coverage: {r['coverage']['score']}/3, Actionability: {r['actionability']['average']:.1f}, Precision: {r['precision']['rate']:.1%}")

        # Calculate averages
        avg_coverage = sum(r["coverage"]["score"] for r in results) / total
        avg_actionability = sum(r["actionability"]["average"] for r in results) / total
        avg_precision = sum(r["precision"]["rate"] for r in results) / total

        print(f"\nAverage Metrics:")
        print(f"  Coverage:      {avg_coverage:.2f}/3")
        print(f"  Actionability: {avg_actionability:.1f}/10")
        print(f"  Precision:     {avg_precision:.1%}")

        print(f"\n{'='*100}")

        # Assert minimum pass rate
        pass_rate = passed / total
        assert pass_rate >= 0.70, f"Pass rate {pass_rate:.1%} below threshold (70%)"
