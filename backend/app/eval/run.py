"""Run Sage conversation evaluations.

Usage:
    python -m app.eval.run                     # All personas
    python -m app.eval.run --persona sarah     # One persona (partial match)
    python -m app.eval.run --turns 15          # Override turn count
    python -m app.eval.run --repeat 3          # Run each persona N times
    python -m app.eval.run --no-judge          # Skip Claude judge (rules only)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from app.eval.personas import PERSONAS, Persona
from app.eval.runner import EvalRunner
from app.eval.evaluator import EvalResult

logger = logging.getLogger(__name__)

# Results directory relative to backend/
RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "eval" / "results"


def _match_personas(name_filter: str | None) -> list[Persona]:
    """Match personas by partial slug match. Returns all if no filter."""
    if not name_filter:
        return list(PERSONAS.values())

    matched = []
    for slug, persona in PERSONAS.items():
        if name_filter.lower() in slug.lower():
            matched.append(persona)
    return matched


def _print_transcript(transcript: list[dict]) -> None:
    """Print conversation transcript with turn labels."""
    for entry in transcript:
        role = "USER" if entry["role"] == "user" else "SAGE"
        turn = entry.get("turn", "?")
        content = entry["content"]
        # Truncate long messages for display
        if len(content) > 120:
            content = content[:117] + "..."
        print(f"  Turn {turn}: [{role}] {content}")


def _print_rule_results(rule_results: dict) -> None:
    """Print rule check results with pass/fail indicators."""
    checks = [
        ("onboarding_complete", "onboarding_complete"),
        ("plants_created", "plants_created"),
        ("no_banned_words", "no_banned_words"),
        ("no_empty_responses", "no_empty_responses"),
        ("response_length_ok", "response_length_ok"),
    ]
    for label, key in checks:
        passed = rule_results.get(key, False)
        icon = "PASS" if passed else "FAIL"
        extra = ""
        if key == "plants_created" and rule_results.get("plants_matched"):
            extra = f": {rule_results['plants_matched']}"
        if key == "no_banned_words" and rule_results.get("banned_word_violations"):
            extra = f": {rule_results['banned_word_violations']}"
        if key == "no_empty_responses" and rule_results.get("empty_response_turns"):
            extra = f": turns {rule_results['empty_response_turns']}"
        if key == "response_length_ok" and rule_results.get("length_exceeded_turns"):
            extra = f": turns {rule_results['length_exceeded_turns']}"
        print(f"    [{icon}] {label}{extra}")


def _print_judge_scores(judge_scores: dict | None) -> None:
    """Print judge evaluation scores."""
    if not judge_scores:
        print("    (skipped)")
        return
    if "error" in judge_scores:
        print(f"    ERROR: {judge_scores['error']}")
        return

    score_keys = ["coaching_style", "tone", "specificity", "flow", "conciseness"]
    for key in score_keys:
        val = judge_scores.get(key, "?")
        label = key.replace("_", " ").title()
        print(f"    {label}: {val}/5")

    overall = judge_scores.get("overall", "?")
    print(f"    Overall: {overall}/5")

    issues = judge_scores.get("issues", [])
    if issues:
        print("    Issues:")
        for issue in issues:
            print(f"      - {issue}")


def _save_results(
    results: list[EvalResult], timestamp: str, output_dir: Path
) -> None:
    """Save results to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Summary
    summary = {
        "timestamp": timestamp,
        "personas": [],
    }
    for r in results:
        rules_passed = sum(
            1 for k in ("onboarding_complete", "plants_created",
                        "no_banned_words", "no_empty_responses", "response_length_ok")
            if r.rule_results.get(k, False)
        )
        rules_total = 5
        entry = {
            "persona": r.persona_name,
            "turns_completed": r.turns_completed,
            "rules_passed": f"{rules_passed}/{rules_total}",
            "rule_passed": r.rule_passed,
            "judge_average": r.judge_average,
            "errors": r.errors,
        }
        summary["personas"].append(entry)

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    # Per-persona detail
    for r in results:
        detail = {
            "persona": r.persona_name,
            "turns_completed": r.turns_completed,
            "transcript": r.transcript,
            "rule_results": r.rule_results,
            "rule_passed": r.rule_passed,
            "judge_scores": r.judge_scores,
            "judge_average": r.judge_average,
            "errors": r.errors,
        }
        detail_path = output_dir / f"{r.persona_name}.json"
        detail_path.write_text(json.dumps(detail, indent=2, default=str))


async def _run_eval(
    personas: list[Persona],
    turns_override: int | None,
    repeat: int,
    run_judge: bool,
) -> list[EvalResult]:
    """Run evaluations for all selected personas."""
    runner = EvalRunner(run_judge=run_judge)
    all_results: list[EvalResult] = []

    for persona in personas:
        if turns_override is not None:
            persona.turns = turns_override

        for i in range(repeat):
            suffix = f" (run {i + 1}/{repeat})" if repeat > 1 else ""
            print(f"\nRunning {persona.slug} ({persona.turns} turns){suffix}...")

            result = await runner.run_persona(persona)
            all_results.append(result)

            # Print transcript
            print()
            _print_transcript(result.transcript)

            # Print rule results
            print("\n  Rule checks:")
            _print_rule_results(result.rule_results)

            # Print judge scores
            if run_judge:
                print("\n  Judge scores:")
                _print_judge_scores(result.judge_scores)

            if result.errors:
                print(f"\n  Errors: {result.errors}")

    return all_results


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run Sage conversation evaluations")
    parser.add_argument(
        "--persona",
        type=str,
        default=None,
        help="Filter personas by partial slug match (e.g. 'sarah')",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=None,
        help="Override turn count for all personas",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Run each persona N times",
    )
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Skip Claude judge evaluation (rules only)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    # Match personas
    personas = _match_personas(args.persona)
    if not personas:
        print(f"No personas matching '{args.persona}'. Available: {list(PERSONAS.keys())}")
        sys.exit(1)

    print("=" * 50)
    print("  SAGE EVAL")
    print("=" * 50)
    print(f"Personas: {[p.slug for p in personas]}")
    print(f"Judge: {'enabled' if not args.no_judge else 'disabled'}")

    # Run evaluations
    results = asyncio.run(
        _run_eval(personas, args.turns, args.repeat, not args.no_judge)
    )

    # Print summary
    print("\n" + "=" * 50)
    print("  RESULTS")
    print("=" * 50)
    for r in results:
        rules_passed = sum(
            1 for k in ("onboarding_complete", "plants_created",
                        "no_banned_words", "no_empty_responses", "response_length_ok")
            if r.rule_results.get(k, False)
        )
        status = "PASS" if r.rule_passed else "FAIL"
        judge_str = f"Judge: {r.judge_average:.1f}/5" if r.judge_average else "Judge: n/a"
        print(f"  [{status}] {r.persona_name:<25} Rules: {rules_passed}/5  {judge_str}")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = RESULTS_DIR / timestamp
    _save_results(results, timestamp, output_dir)
    print(f"\nResults saved to: {output_dir}")


if __name__ == "__main__":
    main()
