from typing import Any

import pytest

pytestmark = [pytest.mark.quality]


class TestSearchQuality:
    def test_all_queries(
        self,
        search_cli: Any,  # noqa: ANN401
        ground_truth_data: dict[str, Any],
    ) -> None:
        results = []

        for query_id, query_data in ground_truth_data.items():
            query_text = query_data["text"]

            print(f"\n{'=' * 100}")
            print(f"Query {query_id}: {query_text}")
            print(f"{'=' * 100}")

            search_results = search_cli(query_text, limit=10)
            top5_results = search_results["results"][:5]

            print("\nTop-5 Results:")
            for i, result in enumerate(top5_results, 1):
                obj_type = result["object_type"]
                name = result["name"]
                score = result["score"]
                print(f"  {i}. {obj_type:12s} {name:40s} (score: {score:.4f})")
                print(f"     {result['file_path']}")

            essentials = query_data["essential_symbols"]
            coverage = self._evaluate_coverage(top5_results, essentials)
            precision = self._evaluate_precision(top5_results, essentials)

            print("\nMetrics:")
            print(f"  Coverage: {coverage['score']}/3")
            print(
                f"  Precision: {precision['rate']:.1%} ({precision['found']}/{precision['total']})"
            )

            passed = coverage["score"] >= 2 and precision["rate"] >= 0.3
            results.append(
                {
                    "query_id": query_id,
                    "query": query_text,
                    "coverage": coverage,
                    "precision": precision,
                    "passed": passed,
                }
            )

        print(f"\n\n{'=' * 100}")
        print("FINAL SUMMARY")
        print(f"{'=' * 100}")

        passed = sum(1 for r in results if r["passed"])
        total = len(results)

        print(f"\nPassed: {passed}/{total} ({passed / total:.1%})")
        print("\nQuery Results:")
        for r in results:
            status = "✅ PASS" if r["passed"] else "❌ FAIL"
            print(f"  {r['query_id']}: {status}")
            print(
                f"    Coverage: {r['coverage']['score']}/3, Precision: {r['precision']['rate']:.1%}"
            )

        avg_coverage = sum(r["coverage"]["score"] for r in results) / total
        avg_precision = sum(r["precision"]["rate"] for r in results) / total

        print("\nAverage Metrics:")
        print(f"  Coverage:  {avg_coverage:.2f}/3")
        print(f"  Precision: {avg_precision:.1%}")

        print(f"\n{'=' * 100}")

        pass_rate = passed / total
        assert pass_rate >= 0.60, f"Pass rate {pass_rate:.1%} below threshold (60%)"

    def _evaluate_coverage(  # noqa: C901
        self, top5_results: list[dict], essentials: list[dict]
    ) -> dict[str, Any]:
        has_implementation = False
        has_domain_or_doc = False
        has_context = False
        found_items = []

        for result in top5_results:
            path = result["file_path"]
            name = result["name"]

            for item in essentials:
                if item["path"] not in path:
                    continue

                category = item["category"]
                symbol = item.get("symbol", "")

                if category == "implementation":
                    if symbol:
                        symbol_name = symbol.split("::")[-1]
                        if symbol_name in name or symbol in name:
                            has_implementation = True
                            found_items.append(f"impl: {symbol}")
                    else:
                        has_implementation = True
                        found_items.append(f"impl: {item['path']}")
                elif category == "domain_model":
                    if symbol in name:
                        has_domain_or_doc = True
                        found_items.append(f"domain: {symbol}")
                elif category == "documentation":
                    has_domain_or_doc = True
                    found_items.append(f"doc: {item['path']}")
                elif category == "context":
                    has_context = True
                    found_items.append(f"context: {symbol or item['path']}")

        if has_implementation or has_domain_or_doc:
            has_context = True

        score = sum([has_implementation, has_domain_or_doc, has_context])

        return {
            "score": score,
            "max": 3,
            "has_implementation": has_implementation,
            "has_domain_or_doc": has_domain_or_doc,
            "has_context": has_context,
            "found_items": found_items,
        }

    def _evaluate_precision(
        self, top5_results: list[dict], essentials: list[dict]
    ) -> dict[str, Any]:
        total_h1_symbols = sum(1 for item in essentials if item.get("priority") == "H1")
        found_symbols = set()

        for item in essentials:
            if item.get("priority") != "H1":
                continue

            symbol = item.get("symbol", item.get("path"))

            for result in top5_results:
                path = result["file_path"]
                name = result["name"]

                if item["path"] in path and symbol:
                    symbol_name = symbol.split("::")[-1]
                    if symbol_name in name or symbol in name:
                        found_symbols.add(symbol)

        precision_rate = len(found_symbols) / total_h1_symbols if total_h1_symbols > 0 else 0

        return {
            "rate": precision_rate,
            "found": len(found_symbols),
            "total": total_h1_symbols,
            "found_symbols": list(found_symbols),
        }
