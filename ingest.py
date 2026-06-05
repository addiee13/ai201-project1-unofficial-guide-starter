"""
Milestone 3 — Document ingestion and chunking pipeline.

Reads each professor review file from docs/, normalizes the two field
formats found across files, and produces chunk dicts ready for embedding.

Each chunk dict has two keys:
  text     — the string to embed (professor header + review content)
  metadata — structured fields stored in ChromaDB but NOT embedded
             (professor, course, quality, difficulty, date, grade, etc.)

Run directly to inspect sample output:
  python ingest.py
"""

import re
import random
from pathlib import Path

DOCS_DIR = Path("docs")


# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------

def _get_field(text, *names):
    """Return the first matching single-line field value, or None."""
    for name in names:
        m = re.search(rf"^{re.escape(name)}:\s*(.+)$", text, re.MULTILINE)
        if m:
            val = m.group(1).strip()
            if val and val.upper() not in ("UNKNOWN", "N/A", "NONE"):
                return val
    return None


def _get_float(text, *names):
    """Extract a float from a field, handling 'X/Y' and plain 'X' formats."""
    raw = _get_field(text, *names)
    if not raw:
        return None
    m = re.match(r"([\d.]+)", raw)
    return float(m.group(1)) if m else None


def _get_tags(block):
    """
    Extract tags from either format:
      Format 1: tags: TAG1, TAG2, TAG3   (comma-separated, single line)
      Format 2: tags:\n- TAG1\n- TAG2    (multiline list)
    """
    multi = re.search(r"^tags:\s*\n((?:[ \t]*-[ \t]*.+\n?)+)", block, re.MULTILINE)
    if multi:
        items = [t.strip().lstrip("-").strip() for t in multi.group(1).splitlines()]
        return [t for t in items if t and t.upper() != "NONE"]

    single = re.search(r"^tags:\s*(.+)$", block, re.MULTILINE)
    if single:
        raw = single.group(1).strip()
        if raw.upper() not in ("NONE", ""):
            return [t.strip() for t in raw.split(",") if t.strip()]
    return []


def _get_key_points(block):
    """Extract key_points list (Format 1 / professor_bal.md only)."""
    m = re.search(r"^key_points:\s*\n((?:[ \t]*-[ \t]*.+\n?)+)", block, re.MULTILINE)
    if not m:
        return []
    return [p.strip().lstrip("-").strip() for p in m.group(1).splitlines() if p.strip()]


def _get_section(text, *names):
    """
    Extract the content of a named all-caps section block.
    Stops at the next all-caps section header or end of file.
    """
    for name in names:
        pattern = (
            rf"^{re.escape(name)}:\s*\n"
            rf"(.*?)"
            rf"(?=\n[A-Z][A-Z_]{{2,}}:|\Z)"
        )
        m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        if m:
            content = m.group(1).strip()
            if content:
                return content
    return None


# ---------------------------------------------------------------------------
# Chunk text builder
# ---------------------------------------------------------------------------

def _build_text(professor, course, quality, date, verbatim, key_points):
    """Build the string that will be embedded for one review chunk."""
    header = f"Professor: {professor}"
    if course:
        header += f" | Course: {course}"
    if quality is not None:
        header += f" | Rating: {quality}/5.0"
    if date:
        header += f" | Date: {date}"

    text = f"{header}\nReview: {verbatim}"
    if key_points:
        text += "\nKey points: " + "; ".join(key_points)
    return text


# ---------------------------------------------------------------------------
# File parser
# ---------------------------------------------------------------------------

def parse_file(filepath):
    """
    Parse one professor .md file and return a list of chunk dicts.
    Produces one summary chunk per file and one review chunk per [REVIEW_N] block.
    """
    raw = filepath.read_text(encoding="utf-8")
    chunks = []

    professor = _get_field(raw, "PROFESSOR_NAME") or filepath.stem.replace("professor_", "").title()
    source_file = filepath.name

    # --- Summary chunk ---
    summary_parts = []

    aggregate = _get_section(raw, "OVERALL_SIGNALS", "AGGREGATE_METRICS")
    if aggregate:
        summary_parts.append(f"Overall signals for {professor}:\n{aggregate}")

    common = _get_section(raw, "COMMON_THEMES")
    if common:
        summary_parts.append(f"Common themes for {professor}:\n{common}")

    negative = _get_section(raw, "NEGATIVE_THEMES")
    if negative:
        summary_parts.append(f"Negative themes for {professor}:\n{negative}")

    if summary_parts:
        chunks.append({
            "text": "\n\n".join(summary_parts),
            "metadata": {
                "professor": professor,
                "source": source_file,
                "chunk_type": "summary",
            },
        })

    # --- Per-review chunks ---
    review_blocks = re.split(r"\[REVIEW_\d+\]", raw)[1:]

    for block in review_blocks:
        verbatim = _get_field(block, "verbatim_text")
        if not verbatim:
            continue

        course = _get_field(block, "course_if_known", "course")
        date = _get_field(block, "term_or_date", "date")
        quality = _get_float(block, "rating_if_available", "quality")
        difficulty = _get_float(block, "difficulty_if_available", "difficulty")
        grade = _get_field(block, "grade")
        attendance = _get_field(block, "attendance")
        sentiment = _get_field(block, "sentiment_label")
        tags = _get_tags(block)
        key_points = _get_key_points(block)

        embed_text = _build_text(professor, course, quality, date, verbatim, key_points)

        metadata = {
            "professor": professor,
            "source": source_file,
            "chunk_type": "review",
        }
        if course:
            metadata["course"] = course
        if date:
            metadata["date"] = date
        if quality is not None:
            metadata["quality"] = quality
        if difficulty is not None:
            metadata["difficulty"] = difficulty
        if grade:
            metadata["grade"] = grade
        if attendance:
            metadata["attendance"] = attendance
        if sentiment:
            metadata["sentiment"] = sentiment
        if tags:
            metadata["tags"] = ", ".join(tags)

        chunks.append({"text": embed_text, "metadata": metadata})

    return chunks


# ---------------------------------------------------------------------------
# Load all chunks
# ---------------------------------------------------------------------------

def load_chunks():
    """Parse all professor files in DOCS_DIR and return all chunk dicts."""
    all_chunks = []
    for path in sorted(DOCS_DIR.glob("professor_*.md")):
        if path.name == "professor_reviews.md":
            continue
        file_chunks = parse_file(path)
        all_chunks.extend(file_chunks)
        print(f"  {path.name}: {len(file_chunks)} chunks")
    return all_chunks


# ---------------------------------------------------------------------------
# Entrypoint — run to inspect sample output
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Loading and chunking documents...\n")
    chunks = load_chunks()
    print(f"\nTotal chunks: {len(chunks)}")

    review_chunks = [c for c in chunks if c["metadata"]["chunk_type"] == "review"]
    summary_chunks = [c for c in chunks if c["metadata"]["chunk_type"] == "summary"]
    print(f"  Review chunks:  {len(review_chunks)}")
    print(f"  Summary chunks: {len(summary_chunks)}")

    print("\n--- 5 random review chunks ---")
    for chunk in random.sample(review_chunks, min(5, len(review_chunks))):
        print(f"\n[{chunk['metadata']['source']}]")
        print(chunk["text"][:500])
        print(f"Metadata: { {k: v for k, v in chunk['metadata'].items() if k != 'source'} }")
        print("-" * 60)
