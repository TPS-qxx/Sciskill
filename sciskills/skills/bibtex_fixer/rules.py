"""
Rule engine for BibTeX quality checks and normalization.
No LLM required - pure rule-based logic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BibIssue:
    entry_key: str
    issue: str
    severity: str  # "error" | "warning" | "info"
    action: str    # "auto_filled" | "needs_review" | "removed" | "flagged"
    field: str = ""
    detail: str = ""


# Required fields per entry type
REQUIRED_FIELDS: dict[str, list[str]] = {
    "article": ["author", "title", "journal", "year"],
    "inproceedings": ["author", "title", "booktitle", "year"],
    "proceedings": ["title", "year"],
    "book": ["author", "title", "publisher", "year"],
    "incollection": ["author", "title", "booktitle", "publisher", "year"],
    "phdthesis": ["author", "title", "school", "year"],
    "mastersthesis": ["author", "title", "school", "year"],
    "techreport": ["author", "title", "institution", "year"],
    "misc": ["author", "title", "year"],
    "unpublished": ["author", "title"],
}

# Common journal abbreviation map (sample)
JOURNAL_ABBREVIATIONS: dict[str, str] = {
    "proceedings of the acm": "Proc. ACM",
    "transactions on neural networks": "IEEE Trans. Neural Netw.",
    "neural information processing systems": "NeurIPS",
    "international conference on machine learning": "ICML",
    "computer vision and pattern recognition": "CVPR",
    "empirical methods in natural language processing": "EMNLP",
    "association for computational linguistics": "ACL",
    "international conference on learning representations": "ICLR",
    "aaai conference on artificial intelligence": "AAAI",
}


def check_missing_fields(entry: dict) -> list[BibIssue]:
    """Check for missing required fields."""
    issues = []
    entry_type = entry.get("ENTRYTYPE", "misc").lower()
    required = REQUIRED_FIELDS.get(entry_type, ["author", "title", "year"])
    key = entry.get("ID", "unknown")

    for f in required:
        if not entry.get(f, "").strip():
            issues.append(BibIssue(
                entry_key=key,
                issue=f"Missing required field: {f}",
                severity="error",
                action="needs_review",
                field=f,
            ))
    return issues


def check_author_format(entry: dict) -> list[BibIssue]:
    """
    Check author name formatting.
    BibTeX standard: "Last, First and Last, First" or "First Last and First Last"
    Flag mixed formats.
    """
    issues = []
    key = entry.get("ID", "unknown")
    author = entry.get("author", "").strip()
    if not author:
        return issues

    names = [n.strip() for n in re.split(r"\band\b", author, flags=re.IGNORECASE)]
    has_comma = [("," in n) for n in names]

    if any(has_comma) and not all(has_comma):
        issues.append(BibIssue(
            entry_key=key,
            issue="Inconsistent author name format (mix of 'Last, First' and 'First Last')",
            severity="warning",
            action="needs_review",
            field="author",
            detail=author[:100],
        ))

    # Check for all-caps authors (common OCR artifact)
    for name in names:
        if name == name.upper() and len(name) > 4:
            issues.append(BibIssue(
                entry_key=key,
                issue=f"Author name appears to be all-caps (possible OCR artifact): {name}",
                severity="warning",
                action="needs_review",
                field="author",
            ))
            break

    return issues


def check_year_format(entry: dict) -> list[BibIssue]:
    """Validate year is a 4-digit number."""
    issues = []
    key = entry.get("ID", "unknown")
    year = entry.get("year", "").strip().strip("{}")
    if year and not re.fullmatch(r"\d{4}", year):
        issues.append(BibIssue(
            entry_key=key,
            issue=f"Invalid year format: '{year}'",
            severity="error",
            action="needs_review",
            field="year",
        ))
    return issues


def check_url_in_note(entry: dict) -> list[BibIssue]:
    """Flag entries that store URLs in 'note' instead of 'url' field."""
    issues = []
    key = entry.get("ID", "unknown")
    note = entry.get("note", "")
    if re.search(r"https?://", note) and not entry.get("url"):
        issues.append(BibIssue(
            entry_key=key,
            issue="URL found in 'note' field; consider moving to 'url'",
            severity="info",
            action="needs_review",
            field="note",
        ))
    return issues


def check_title_braces(entry: dict) -> list[BibIssue]:
    """
    Warn if title has no braces around proper nouns / acronyms.
    Simple heuristic: flag ALL-CAPS words not wrapped in {}.
    """
    issues = []
    key = entry.get("ID", "unknown")
    title = entry.get("title", "")
    # Find words that are 2+ uppercase letters and not already wrapped in {}
    pattern = re.compile(r"(?<!\{)\b([A-Z]{2,})\b(?!\})")
    matches = pattern.findall(title)
    if matches:
        issues.append(BibIssue(
            entry_key=key,
            issue=f"Title has unbraced uppercase words (may be downcased by BibTeX): {matches[:3]}",
            severity="warning",
            action="needs_review",
            field="title",
        ))
    return issues


def find_duplicate_entries(entries: list[dict]) -> list[BibIssue]:
    """Detect duplicate entries by DOI or by (author, title) similarity."""
    issues = []
    seen_dois: dict[str, str] = {}
    seen_titles: dict[str, str] = {}

    for entry in entries:
        key = entry.get("ID", "unknown")
        doi = entry.get("doi", "").strip().lower()
        title = re.sub(r"\s+", " ", entry.get("title", "").strip().lower())

        if doi:
            if doi in seen_dois:
                issues.append(BibIssue(
                    entry_key=key,
                    issue=f"Duplicate entry (same DOI as '{seen_dois[doi]}')",
                    severity="error",
                    action="removed",
                    detail=doi,
                ))
            else:
                seen_dois[doi] = key

        if title:
            if title in seen_titles:
                issues.append(BibIssue(
                    entry_key=key,
                    issue=f"Possible duplicate (same title as '{seen_titles[title]}')",
                    severity="warning",
                    action="flagged",
                    detail=title[:80],
                ))
            else:
                seen_titles[title] = key

    return issues


def normalize_author(author_str: str) -> str:
    """
    Normalize author string to 'Last, First and Last, First' format.
    Handles simple cases; complex cases returned as-is.
    """
    names = [n.strip() for n in re.split(r"\band\b", author_str, flags=re.IGNORECASE)]
    normalized = []
    for name in names:
        if "," in name:
            normalized.append(name)
        else:
            parts = name.split()
            if len(parts) >= 2:
                last = parts[-1]
                first = " ".join(parts[:-1])
                normalized.append(f"{last}, {first}")
            else:
                normalized.append(name)
    return " and ".join(normalized)


def run_all_checks(entries: list[dict]) -> list[BibIssue]:
    """Run all rule-based checks on a list of BibTeX entry dicts."""
    issues: list[BibIssue] = []
    for entry in entries:
        issues.extend(check_missing_fields(entry))
        issues.extend(check_author_format(entry))
        issues.extend(check_year_format(entry))
        issues.extend(check_url_in_note(entry))
        issues.extend(check_title_braces(entry))
    issues.extend(find_duplicate_entries(entries))
    return issues
