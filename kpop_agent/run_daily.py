import asyncio
from pathlib import Path

from agent import REPORTS_DIR, run_daily_report


def update_index() -> Path:
    index = REPORTS_DIR / "INDEX.md"
    reports = sorted(
        (p for p in REPORTS_DIR.glob("*.md") if p.name != "INDEX.md"),
        reverse=True,
    )
    lines = ["# K-POP 일일 리포트 인덱스", ""]
    for r in reports:
        lines.append(f"- [{r.stem}]({r.name})")
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index


if __name__ == "__main__":
    path = asyncio.run(run_daily_report())
    index = update_index()
    print(f"report: {path}")
    print(f"index:  {index}")
