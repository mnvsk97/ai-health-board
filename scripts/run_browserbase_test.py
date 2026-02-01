#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time

from ai_health_board import redis_store
from ai_health_board.tester_browserbase import BrowserbaseChatConfig, run_browserbase_test


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Browserbase Stagehand chat test")
    parser.add_argument("--scenario-id", required=True, help="Scenario ID to test")
    parser.add_argument("--url", required=True, help="Chat UI URL to test")
    parser.add_argument("--input-selector", required=True, help="CSS selector for chat input")
    parser.add_argument("--response-selector", required=True, help="CSS selector for response blocks")
    parser.add_argument("--send-selector", default=None, help="CSS selector for send button (optional)")
    parser.add_argument("--transcript-selector", default=None, help="CSS selector for transcript container (optional)")
    parser.add_argument("--max-turns", type=int, default=4)
    parser.add_argument("--timeout-ms", type=int, default=45000)
    parser.add_argument("--settle-ms", type=int, default=1500)
    args = parser.parse_args()

    scenario = redis_store.get_scenario(args.scenario_id)
    if not scenario:
        raise SystemExit(f"Scenario not found: {args.scenario_id}")

    run_id = f"bb_run_{int(time.time())}"
    config = BrowserbaseChatConfig(
        url=args.url,
        input_selector=args.input_selector,
        response_selector=args.response_selector,
        send_selector=args.send_selector,
        transcript_selector=args.transcript_selector,
        max_turns=args.max_turns,
        timeout_ms=args.timeout_ms,
        settle_ms=args.settle_ms,
    )

    run_browserbase_test(config, scenario, run_id)
    print(f"Run complete: {run_id}")


if __name__ == "__main__":
    main()
