"""Multi-provider scored eval runner.

Runs all 7 eval problems against configured cloud providers, scores results
against Qiskit-computed baselines, and writes a Markdown report.

Smoke test (single problem, single provider):
    GOOGLE_AI_API_KEY=xxx uv run python scripts/run_scored_eval.py \\
        --providers gemini-flash --problems grover_3q_1iter

Full run:
    GOOGLE_AI_API_KEY=xxx GROQ_API_KEY=xxx \\
        uv run python scripts/run_scored_eval.py \\
            --providers gemini-flash,groq-llama70b \\
            --output reports/eval_report.md

Environment variables:
    GOOGLE_AI_API_KEY   Google AI Studio API key (required for gemini-flash)
    GROQ_API_KEY        Groq API key (required for groq-llama70b)
    ANTHROPIC_API_KEY   Anthropic API key (optional — adds claude-haiku provider)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx

from qarc.baselines import load_baselines
from qarc.eval import EvalCase, EvalResult, run_eval
from qarc.openai_compatible_client import OpenAICompatibleClient
from qarc.registry import registry
from qarc.report import generate_report
from qarc.scoring import ScoringResult, score_run
from qarc.tools import circuit, resources, transpile  # noqa: F401 — register tools

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_compact.txt"

PROVIDER_CONFIGS: dict[str, dict[str, str]] = {
    "gemini-flash": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.0-flash",
        "api_key_env": "GOOGLE_AI_API_KEY",
    },
    "groq-llama70b": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
    },
}


def _build_cases(provider_names: list[str]) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for name in provider_names:
        if name == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                print(f"  [skip] {name}: ANTHROPIC_API_KEY not set")
                continue
            from qarc.anthropic_client import AnthropicClient
            cases.append(EvalCase(
                label="anthropic/claude-haiku-4-5",
                client=AnthropicClient(model="claude-haiku-4-5-20251001", api_key=api_key),
            ))
            continue

        config = PROVIDER_CONFIGS.get(name)
        if not config:
            print(f"  [skip] {name}: unknown provider (valid: {', '.join(PROVIDER_CONFIGS)})")
            continue
        api_key = os.getenv(config["api_key_env"])
        if not api_key:
            print(f"  [skip] {name}: {config['api_key_env']} not set")
            continue
        cases.append(EvalCase(
            label=f"{name}/{config['model']}",
            client=OpenAICompatibleClient(
                base_url=config["base_url"],
                model=config["model"],
                api_key=api_key,
                timeout=120.0,
                # No think= for cloud providers (ADR-035)
            ),
        ))
    return cases


def _run_with_retry(
    query: str,
    case: EvalCase,
    system_prompt: str,
    delay_s: float,
    max_retries: int = 3,
) -> EvalResult:
    delays = [1.0, 2.0, 4.0]
    for attempt in range(max_retries + 1):
        try:
            results = run_eval(query, [case], registry, system_prompt, max_steps=12)
            return results[0]
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429 and attempt < max_retries:
                wait = delays[min(attempt, len(delays) - 1)]
                print(f"    429 rate limit — retry {attempt + 1}/{max_retries} in {wait}s")
                time.sleep(wait)
            else:
                return EvalResult(
                    label=case.label,
                    status="error",
                    steps_count=0,
                    final_answer="",
                    latency_ms=0.0,
                    error=f"rate_limited: {exc}",
                )
        except Exception as exc:
            return EvalResult(
                label=case.label,
                status="error",
                steps_count=0,
                final_answer="",
                latency_ms=0.0,
                error=str(exc),
            )
    return EvalResult(
        label=case.label,
        status="error",
        steps_count=0,
        final_answer="",
        latency_ms=0.0,
        error="rate_limited after max retries",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-provider scored eval runner")
    parser.add_argument(
        "--providers",
        default="gemini-flash,groq-llama70b",
        help="Comma-separated list of providers (default: gemini-flash,groq-llama70b)",
    )
    parser.add_argument(
        "--problems",
        default=None,
        help="Comma-separated problem IDs to run (default: all 7)",
    )
    parser.add_argument(
        "--output",
        default="reports/eval_report.md",
        help="Output path for Markdown report (default: reports/eval_report.md)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds between problems per provider (default: 2.0)",
    )
    args = parser.parse_args()

    provider_names = [p.strip() for p in args.providers.split(",")]
    output_path = Path(args.output)

    # Load system prompt
    if SYSTEM_PROMPT_PATH.exists():
        system_prompt = SYSTEM_PROMPT_PATH.read_text()
    else:
        system_prompt = (
            "You are a quantum computing assistant "
            "with access to quantum circuit tools."
        )

    # Load baselines
    baselines = load_baselines()

    # Filter problems if specified
    if args.problems:
        problem_ids = [p.strip() for p in args.problems.split(",")]
        baselines = [b for b in baselines if b.problem_id in problem_ids]
        if not baselines:
            print(f"No matching problems found for: {problem_ids}")
            sys.exit(1)

    # Build provider cases
    print(f"\nBuilding provider cases for: {provider_names}")
    cases = _build_cases(provider_names)
    if not cases:
        print("No providers available. Set the appropriate API key environment variables.")
        sys.exit(1)
    print(f"Active providers: {[c.label for c in cases]}")

    # Run eval
    total_runs = len(baselines) * len(cases)
    print(f"\nRunning {len(baselines)} problems × {len(cases)} providers = {total_runs} runs")
    print(f"Delay between problems: {args.delay}s\n")

    scoring_results: list[ScoringResult] = []
    for case in cases:
        print(f"\n── Provider: {case.label} ──")
        for i, baseline in enumerate(baselines):
            print(f"  [{i+1}/{len(baselines)}] {baseline.problem_id}...", end="", flush=True)
            if i > 0:
                time.sleep(args.delay)
            eval_result = _run_with_retry(baseline.query, case, system_prompt, args.delay)
            score = score_run(eval_result, baseline)
            scoring_results.append(score)
            status_icon = "✅" if score.failure_mode == "correct" else "❌"
            print(f" {status_icon} {score.failure_mode} ({eval_result.latency_ms:.0f}ms)")

    # Generate report
    generate_report(scoring_results, output_path, baselines)
    print(f"\nReport written to: {output_path}")

    # Summary
    passed = sum(1 for r in scoring_results if r.failure_mode == "correct")
    total = len(scoring_results)
    pct = 100 * passed // total if total else 0
    print(f"Pass rate: {passed}/{total} ({pct}%)")


if __name__ == "__main__":
    main()
