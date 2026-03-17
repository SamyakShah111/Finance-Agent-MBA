"""
sentiment_analyzer.py
---------------------
Scans the 12 earnings-call transcripts stored in Transcripts/ and produces a
'Sentiment Scorecard' ranked from Most Bullish to Most Cautious.

Bullish keywords  → positive sentiment (+1 each occurrence)
Cautious keywords → negative / cautious sentiment (-1 each occurrence)

Net score = bullish_count - cautious_count

Output: Reports/Sector_Sentiment.md
"""

import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Keyword lists
# ---------------------------------------------------------------------------
BULLISH_KEYWORDS = [
    "bullish",
    "optimistic",
    "optimism",
    "growth",
    "strong",
    "strength",
    "record",
    "outperform",
    "opportunity",
    "opportunities",
    "confident",
    "confidence",
    "positive",
    "upside",
    "momentum",
    "robust",
    "accelerate",
    "accelerating",
    "expand",
    "expansion",
    "recovery",
    "beat",
    "exceed",
    "exceeded",
]

CAUTIOUS_KEYWORDS = [
    "caution",
    "cautious",
    "headwind",
    "headwinds",
    "risk",
    "risks",
    "challenge",
    "challenges",
    "uncertain",
    "uncertainty",
    "slowdown",
    "decline",
    "pressure",
    "pressures",
    "concern",
    "concerns",
    "volatile",
    "volatility",
    "weak",
    "weakness",
    "miss",
    "missed",
    "disappointing",
    "disappoint",
    "downside",
    "deteriorate",
    "deterioration",
]

# ---------------------------------------------------------------------------
# Helper: count keyword occurrences in text (case-insensitive, whole-word)
# ---------------------------------------------------------------------------

def count_keywords(text: str, keywords: list[str]) -> dict[str, int]:
    """Return a dict mapping each keyword to its occurrence count."""
    counts: dict[str, int] = {}
    text_lower = text.lower()
    for kw in keywords:
        pattern = r"\b" + re.escape(kw.lower()) + r"\b"
        counts[kw] = len(re.findall(pattern, text_lower))
    return counts


# ---------------------------------------------------------------------------
# Discover transcript files
# ---------------------------------------------------------------------------

def find_transcripts(base_dir: Path) -> list[tuple[str, str, Path]]:
    """
    Walk Transcripts/ and return a list of (company_name, sector, path).
    Sector is derived from the sub-folder name.
    """
    transcripts: list[tuple[str, str, Path]] = []
    transcripts_dir = base_dir / "Transcripts"
    for sector_dir in sorted(transcripts_dir.iterdir()):
        if sector_dir.is_dir():
            sector = sector_dir.name
            for txt_file in sorted(sector_dir.glob("*.txt")):
                company = txt_file.stem
                transcripts.append((company, sector, txt_file))
    return transcripts


# ---------------------------------------------------------------------------
# Analyse a single transcript
# ---------------------------------------------------------------------------

def analyze_transcript(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise OSError(f"Failed to read transcript '{path}': {exc}") from exc

    bullish_counts = count_keywords(text, BULLISH_KEYWORDS)
    cautious_counts = count_keywords(text, CAUTIOUS_KEYWORDS)

    total_bullish = sum(bullish_counts.values())
    total_cautious = sum(cautious_counts.values())
    net_score = total_bullish - total_cautious

    return {
        "bullish_count": total_bullish,
        "cautious_count": total_cautious,
        "net_score": net_score,
        "bullish_breakdown": bullish_counts,
        "cautious_breakdown": cautious_counts,
    }


# ---------------------------------------------------------------------------
# Assign a qualitative label based on net score
# ---------------------------------------------------------------------------

def sentiment_label(net_score: int) -> str:
    # Thresholds are empirical: a transcript with ≥50 more bullish than cautious
    # mentions reflects strongly positive management tone; negative values indicate
    # increasing caution in language.
    if net_score >= 50:
        return "Very Bullish"
    if net_score >= 20:
        return "Bullish"
    if net_score >= 0:
        return "Mildly Bullish"
    if net_score >= -20:
        return "Mildly Cautious"
    if net_score >= -50:
        return "Cautious"
    return "Very Cautious"


# ---------------------------------------------------------------------------
# Build the Markdown report
# ---------------------------------------------------------------------------

def build_report(results: list[dict]) -> str:
    lines: list[str] = []

    lines.append("# Sector Sentiment Scorecard")
    lines.append("")
    lines.append(
        "Earnings transcripts for 12 companies were scanned for bullish and cautious "
        "keywords. A **Net Score** is computed as:"
    )
    lines.append("")
    lines.append("```")
    lines.append("Net Score = Bullish keyword count − Cautious keyword count")
    lines.append("```")
    lines.append("")
    lines.append(
        "Companies are ranked from **Most Bullish** (highest Net Score) to "
        "**Most Cautious** (lowest Net Score)."
    )
    lines.append("")

    # Main ranking table
    lines.append(
        "| Rank | Company | Sector | Bullish Hits | Cautious Hits | Net Score | Sentiment |"
    )
    lines.append(
        "|-----:|---------|--------|-------------:|--------------:|----------:|-----------|"
    )
    for i, row in enumerate(results, start=1):
        lines.append(
            f"| {i} | {row['company']} | {row['sector']} "
            f"| {row['bullish_count']} | {row['cautious_count']} "
            f"| {row['net_score']:+d} | {row['label']} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Keyword Reference")
    lines.append("")
    lines.append(
        "| Category | Keywords |"
    )
    lines.append(
        "|----------|----------|"
    )
    lines.append(
        f"| **Bullish** | {', '.join(BULLISH_KEYWORDS)} |"
    )
    lines.append(
        f"| **Cautious** | {', '.join(CAUTIOUS_KEYWORDS)} |"
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Per-Company Keyword Breakdown")
    lines.append("")

    for row in results:
        lines.append(f"### {row['company']} ({row['sector']})")
        lines.append("")
        lines.append(f"**Net Score: {row['net_score']:+d} — {row['label']}**")
        lines.append("")

        # Bullish breakdown (only keywords with hits)
        bullish_hits = {k: v for k, v in row["bullish_breakdown"].items() if v > 0}
        if bullish_hits:
            lines.append("**Bullish keywords found:**")
            lines.append("")
            for kw, cnt in sorted(bullish_hits.items(), key=lambda x: -x[1]):
                lines.append(f"- `{kw}`: {cnt}")
            lines.append("")

        # Cautious breakdown (only keywords with hits)
        cautious_hits = {k: v for k, v in row["cautious_breakdown"].items() if v > 0}
        if cautious_hits:
            lines.append("**Cautious keywords found:**")
            lines.append("")
            for kw, cnt in sorted(cautious_hits.items(), key=lambda x: -x[1]):
                lines.append(f"- `{kw}`: {cnt}")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base_dir = Path(__file__).resolve().parent.parent  # repo root

    transcripts = find_transcripts(base_dir)
    if not transcripts:
        print("No transcript files found under Transcripts/")
        return

    results: list[dict] = []
    for company, sector, path in transcripts:
        print(f"Analyzing {company} ({sector}) …")
        stats = analyze_transcript(path)
        results.append(
            {
                "company": company,
                "sector": sector,
                "path": str(path),
                **stats,
                "label": sentiment_label(stats["net_score"]),
            }
        )

    # Sort: highest net score first (Most Bullish → Most Cautious)
    results.sort(key=lambda r: r["net_score"], reverse=True)

    report_text = build_report(results)

    reports_dir = base_dir / "Reports"
    reports_dir.mkdir(exist_ok=True)
    output_path = reports_dir / "Sector_Sentiment.md"
    output_path.write_text(report_text, encoding="utf-8")

    print(f"\nReport written to: {output_path}")
    print("\nRanking summary:")
    print(f"{'Rank':<5} {'Company':<15} {'Net Score':>10} {'Sentiment'}")
    print("-" * 50)
    for i, row in enumerate(results, start=1):
        print(
            f"{i:<5} {row['company']:<15} {row['net_score']:>+10}  {row['label']}"
        )


if __name__ == "__main__":
    main()
