import os
import sys
from datetime import date, timedelta
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from prompts import KPOP_RESEARCH_SYSTEM_PROMPT

load_dotenv()

REPORTS_DIR = Path(__file__).parent / "reports"
MODEL = os.getenv("KPOP_AGENT_MODEL", "claude-opus-4-7")
EFFORT = os.getenv("KPOP_AGENT_EFFORT", "high")
MAX_TOKENS = int(os.getenv("KPOP_AGENT_MAX_TOKENS", "32000"))
MAX_CONTINUATIONS = 5


def _print_activity(event) -> None:
    if event.type == "content_block_start":
        block = event.content_block
        if block.type == "server_tool_use":
            tool_name = getattr(block, "name", "?")
            print(f"\n[{tool_name}] running…", flush=True)
        elif block.type == "thinking":
            print("\n[thinking…]", flush=True)
        elif block.type == "text":
            print("\n[writing report…]\n", flush=True)
    elif event.type == "content_block_delta":
        delta = event.delta
        if delta.type == "text_delta":
            print(delta.text, end="", flush=True)


def run_daily_report(target_date: date | None = None) -> Path:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "ERROR: ANTHROPIC_API_KEY is not set. "
            "Copy .env.example to .env and add your key, then re-run."
        )

    today = date.today()
    news_date = target_date or (today - timedelta(days=1))
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / f"{news_date.isoformat()}.md"

    client = anthropic.Anthropic()

    user_prompt = (
        f"Today is {today.isoformat()}. Produce the K-pop daily issue brief "
        f"covering events from {news_date.isoformat()} (D-1). "
        f"Run multiple web searches across different categories, verify the top "
        f"issues with WebFetch where useful, then output the full markdown report. "
        f"The report title and filename use {news_date.isoformat()}."
    )

    messages = [{"role": "user", "content": user_prompt}]
    response = None

    for i in range(MAX_CONTINUATIONS):
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=KPOP_RESEARCH_SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            output_config={"effort": EFFORT},
            tools=[
                {"type": "web_search_20260209", "name": "web_search"},
                {"type": "web_fetch_20260209", "name": "web_fetch"},
            ],
            messages=messages,
        ) as stream:
            for event in stream:
                _print_activity(event)
            response = stream.get_final_message()

        if response.stop_reason != "pause_turn":
            break

        print("\n[server-side tool loop hit max iterations — continuing]", flush=True)
        messages = [
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": response.content},
        ]
    else:
        print(
            f"\n[warning] hit MAX_CONTINUATIONS={MAX_CONTINUATIONS} — "
            "report may be incomplete",
            flush=True,
        )

    report_text = "".join(b.text for b in response.content if b.type == "text")
    report_path.write_text(report_text, encoding="utf-8")

    usage = response.usage
    print(
        f"\n\n[done] input={usage.input_tokens}, output={usage.output_tokens}, "
        f"cache_read={getattr(usage, 'cache_read_input_tokens', 0)}",
        flush=True,
    )

    return report_path


if __name__ == "__main__":
    path = run_daily_report()
    print(f"\nreport saved: {path}")
