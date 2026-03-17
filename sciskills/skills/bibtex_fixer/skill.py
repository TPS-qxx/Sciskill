"""
Skill 2: BibTeX Fixer & Enricher

Inputs:
  - bibtex_str: raw BibTeX string  OR
  - bib_path: path to a .bib file
  - auto_enrich: bool (default True) — try to auto-fill missing fields via APIs
  - remove_duplicates: bool (default True)
  - normalize_authors: bool (default True)

Output:
  {
    "fixed_bibtex": "...",
    "fixed_entries": [...],
    "issues_found": [...],
    "stats": {"total": N, "issues": M, "enriched": K, "duplicates_removed": J}
  }
"""
from __future__ import annotations

import io
from pathlib import Path

from sciskills.core.base import BaseSkill, SkillResult
from sciskills.core.registry import registry
from sciskills.skills.bibtex_fixer.rules import (
    BibIssue,
    normalize_author,
    run_all_checks,
)
from sciskills.utils.api_clients import CrossrefClient


def _parse_bibtex(bibtex_str: str) -> list[dict]:
    """Parse BibTeX string using bibtexparser v1.x API."""
    try:
        import bibtexparser
        from bibtexparser.bparser import BibTexParser
        from bibtexparser.customization import convert_to_unicode
    except ImportError as e:
        raise ImportError(
            "bibtexparser is required: pip install bibtexparser"
        ) from e

    parser = BibTexParser(common_strings=True)
    parser.customization = convert_to_unicode
    db = bibtexparser.loads(bibtex_str, parser=parser)
    return [dict(e) for e in db.entries]


def _entries_to_string(entries: list[dict]) -> str:
    """Serialize entries back to BibTeX using bibtexparser v1.x API."""
    try:
        import bibtexparser
        from bibtexparser.bibdatabase import BibDatabase
        from bibtexparser.bwriter import BibTexWriter
    except ImportError as e:
        raise ImportError("bibtexparser is required: pip install bibtexparser") from e

    db = BibDatabase()
    db.entries = entries
    writer = BibTexWriter()
    return bibtexparser.dumps(db, writer)


@registry.register
class BibTeXFixerEnricher(BaseSkill):
    name = "bibtex_fixer_enricher"
    description = (
        "Parse, check, fix, and enrich BibTeX entries. "
        "Detects missing fields, duplicate entries, author name inconsistencies, "
        "and auto-fills missing metadata via Crossref / Semantic Scholar APIs."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "bibtex_str": {
                "type": "string",
                "description": "Raw BibTeX string to process.",
            },
            "bib_path": {
                "type": "string",
                "description": "Path to a .bib file.",
            },
            "auto_enrich": {
                "type": "boolean",
                "default": True,
                "description": "Attempt to auto-fill missing fields via Crossref API.",
            },
            "remove_duplicates": {
                "type": "boolean",
                "default": True,
                "description": "Remove duplicate entries detected by DOI or title matching.",
            },
            "normalize_authors": {
                "type": "boolean",
                "default": True,
                "description": "Normalize author name format to 'Last, First and ...'.",
            },
        },
        "oneOf": [
            {"required": ["bibtex_str"]},
            {"required": ["bib_path"]},
        ],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "fixed_bibtex": {"type": "string"},
            "fixed_entries": {"type": "array"},
            "issues_found": {"type": "array"},
            "stats": {"type": "object"},
        },
    }

    def execute(self, params: dict) -> SkillResult:
        try:
            bibtex_str = self._load_bibtex(params)
            entries = _parse_bibtex(bibtex_str)
            original_count = len(entries)
        except Exception as e:
            return SkillResult.fail(errors=[f"BibTeX parse error: {e}"])

        auto_enrich = params.get("auto_enrich", True)
        remove_duplicates = params.get("remove_duplicates", True)
        normalize_authors = params.get("normalize_authors", True)

        # 1. Run checks
        issues = run_all_checks(entries)

        # 2. Remove duplicates
        duplicate_keys: set[str] = set()
        if remove_duplicates:
            for issue in issues:
                if issue.action == "removed":
                    duplicate_keys.add(issue.entry_key)
            entries = [e for e in entries if e.get("ID", "") not in duplicate_keys]

        # 3. Normalize author names
        if normalize_authors:
            for entry in entries:
                if entry.get("author"):
                    entry["author"] = normalize_author(entry["author"])

        # 4. Auto-enrich via Crossref
        enriched_count = 0
        if auto_enrich:
            crossref = CrossrefClient()
            for entry in entries:
                enriched = self._enrich_entry(entry, crossref)
                if enriched:
                    enriched_count += 1

        # 5. Serialize back to BibTeX
        try:
            fixed_bibtex = _entries_to_string([dict(e) for e in entries])
        except Exception:
            # Fallback: manual serialization
            fixed_bibtex = self._manual_serialize(entries)

        issues_dicts = [
            {
                "entry_key": i.entry_key,
                "issue": i.issue,
                "severity": i.severity,
                "action": i.action,
                "field": i.field,
                "detail": i.detail,
            }
            for i in issues
        ]

        stats = {
            "total": original_count,
            "remaining": len(entries),
            "issues_found": len(issues),
            "enriched": enriched_count,
            "duplicates_removed": len(duplicate_keys),
        }

        return SkillResult.ok(
            data={
                "fixed_bibtex": fixed_bibtex,
                "fixed_entries": entries,
                "issues_found": issues_dicts,
                "stats": stats,
            }
        )

    # ------------------------------------------------------------------ #

    def _load_bibtex(self, params: dict) -> str:
        if "bibtex_str" in params:
            return params["bibtex_str"]
        path = Path(params["bib_path"])
        return path.read_text(encoding="utf-8")

    def _enrich_entry(self, entry: dict, crossref: CrossrefClient) -> bool:
        """
        Try to fill missing fields using Crossref.
        Returns True if any field was enriched.
        """
        doi = entry.get("doi", "").strip()
        if not doi:
            return False

        missing = [
            f for f in ["title", "author", "year", "journal", "volume", "pages"]
            if not entry.get(f, "").strip()
        ]
        if not missing:
            return False

        try:
            data = crossref.bib_from_doi(doi)
        except Exception:
            return False

        enriched = False
        for f in missing:
            if data.get(f):
                entry[f] = data[f]
                enriched = True
        return enriched

    def _manual_serialize(self, entries: list[dict]) -> str:
        """Fallback BibTeX serialization without bibtexparser."""
        lines = []
        for entry in entries:
            entry_type = entry.get("ENTRYTYPE", "misc")
            entry_id = entry.get("ID", "unknown")
            lines.append(f"@{entry_type}{{{entry_id},")
            for k, v in entry.items():
                if k in ("ENTRYTYPE", "ID"):
                    continue
                lines.append(f"  {k} = {{{v}}},")
            lines.append("}\n")
        return "\n".join(lines)
