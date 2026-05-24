"""
Регресійний runner для LLMMatcher.

Запуск:
  python tests/regression.py tests/cases/yahotynske_suite.json
  python tests/regression.py tests/cases/yahotynske_suite.json --model groq/llama-3.3-70b-versatile
  python tests/regression.py tests/cases/yahotynske_suite.json --prompts-dir prompts_v2/
  python tests/regression.py tests/cases/yahotynske_suite.json --verbose
  python tests/regression.py tests/cases/yahotynske_suite.json --output tests/results/my_run.json
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))
from llm_match import LLMMatcher, MatchMode


def extract_groups(result: list[dict]) -> list[set[str]]:
    groups = []
    for group in result:
        ids = {offer["product_id"] for offer in group["offers"].values()}
        if ids:
            groups.append(ids)
    return groups


def check_expected(groups: list[set[str]], expected: list[dict]) -> list[str]:
    errors = []
    for e in expected:
        ids = set(e["ids"])
        if len(ids) == 1:
            pid = next(iter(ids))
            for g in groups:
                if pid in g and len(g) > 1:
                    others = g - ids
                    errors.append(
                        f"  ✗ {e['comment']}\n"
                        f"    {pid} wrongly grouped with: {sorted(others)}"
                    )
            continue
        if not any(ids.issubset(g) for g in groups):
            locations = {}
            for pid in e["ids"]:
                for g in groups:
                    if pid in g:
                        locations[pid] = sorted(g)
                        break
                else:
                    locations[pid] = "not found"
            errors.append(
                f"  ✗ {e['comment']}\n"
                f"    Expected together: {e['ids']}\n"
                f"    Actual: {locations}"
            )
    return errors


def check_must_not_group(groups: list[set[str]], must_not: list[dict]) -> list[str]:
    errors = []
    for m in must_not:
        ids = set(m["ids"])
        if any(ids.issubset(g) for g in groups):
            errors.append(
                f"  ✗ {m['comment']}\n"
                f"    Wrongly grouped: {m['ids']}"
            )
    return errors


async def run_suite(
    suite_path: Path, matcher: LLMMatcher, verbose: bool
) -> tuple[int, int, list[dict]]:
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    print(f"\n{'='*60}")
    print(f"Suite: {suite['name']}  ({len(suite['cases'])} cases)")
    print(f"{'='*60}")

    passed = failed = 0
    case_results = []

    for case in suite["cases"]:
        query = case["query"]
        mode = MatchMode(case.get("mode", "strict"))

        id_to_name = {
            p["id"]: p["name"]
            for shop in case["shops"]
            for p in shop["products"]
        }

        result = await matcher.match_raw(shops=case["shops"], mode=mode)
        groups = extract_groups(result)

        if verbose:
            print(f"\n[{query}] Groups ({len(groups)}):")
            for g in groups:
                print(f"  {sorted(g)}")

        errors = (
            check_expected(groups, case.get("expected", []))
            + check_must_not_group(groups, case.get("must_not_group", []))
        )
        total = len(case.get("expected", [])) + len(case.get("must_not_group", []))
        ok = total - len(errors)

        if errors:
            print(f"\n❌ [{query}]  {ok}/{total} checks")
            print("\n".join(errors))
            failed += 1
        else:
            print(f"✅ [{query}]  {total}/{total} checks")
            passed += 1

        case_results.append({
            "query": query,
            "mode": mode.value,
            "prompt": matcher._prompts[mode].splitlines(),
            "passed": not bool(errors),
            "checks_ok": ok,
            "checks_total": total,
            "errors": errors,
            "groups": [
                [{"id": pid, "name": id_to_name.get(pid, pid)} for pid in sorted(g)]
                for g in groups
            ],
        })

    return passed, failed, case_results


def save_results(
    output_path: Path,
    suite_path: Path,
    model: str,
    prompts_dir: Path | None,
    passed: int,
    failed: int,
    case_results: list[dict],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "suite": str(suite_path),
        "model": model,
        "prompts_dir": str(prompts_dir) if prompts_dir else "default (prompts/)",
        "score": {
            "passed": passed,
            "failed": failed,
            "total": passed + failed,
            "pct": round(passed / (passed + failed) * 100, 1) if (passed + failed) else 0,
        },
        "cases": case_results,
    }
    output_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults saved → {output_path}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("suite", help="Path to test suite JSON")
    parser.add_argument("--model", default=os.getenv("LLM_MODEL", "groq/llama-3.3-70b-versatile"))
    parser.add_argument("--prompts-dir", default=None)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--output", default=None, help="Where to save results JSON (default: tests/results/<suite>_<ts>.json)")
    args = parser.parse_args()

    prompts_dir = Path(args.prompts_dir) if args.prompts_dir else None
    matcher = LLMMatcher(
        model=args.model,
        api_key=os.environ["GROQ_API_KEY"],
        prompts_dir=prompts_dir,
    )

    print(f"Model:   {args.model}")
    print(f"Prompts: {prompts_dir or 'default (prompts/)'}")

    suite_path = Path(args.suite)
    passed, failed, case_results = await run_suite(suite_path, matcher, args.verbose)
    total = passed + failed
    score = passed / total * 100 if total else 0

    print(f"\n{'='*60}")
    print(f"Score: {passed}/{total} cases  ({score:.0f}%)")

    if args.output:
        output_path = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = suite_path.stem
        output_path = Path(__file__).parent / "results" / f"{slug}_{ts}.json"

    save_results(output_path, suite_path, args.model, prompts_dir, passed, failed, case_results)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
