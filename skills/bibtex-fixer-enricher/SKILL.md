---
name: bibtex-fixer-enricher
description: Parse, validate, and repair BibTeX entries from a .bib file or raw BibTeX string. Detects missing required fields, inconsistent author formatting, invalid years, duplicate entries, and misplaced URLs. Auto-fills missing fields (title, journal, year, pages, DOI) from the Crossref API when a DOI is present. Use when a researcher has a .bib file that needs cleaning before LaTeX compilation or paper submission. Do NOT use for non-BibTeX citation formats (RIS, EndNote, CSL), for citation style enforcement (that is a LaTeX/CSL concern), or when no .bib file or BibTeX string is available.
---

# BibTeX Fixer & Enricher

Rule-based BibTeX quality checker and enricher. No LLM required — deterministic output. Detects and fixes the most common issues that cause LaTeX compilation errors or submission checklist failures.

## Input Schema

```json
{
  "bib_path":          "string  — path to a .bib file (mutually exclusive with bibtex_str)",
  "bibtex_str":        "string  — raw BibTeX string (mutually exclusive with bib_path)",
  "auto_enrich":       "boolean — default true: query Crossref for entries with a DOI",
  "enrich_strategy":   "string  — 'fill_missing' (default) | 'prefer_crossref' | 'prefer_original'",
  "remove_duplicates": "boolean — default true",
  "normalize_authors": "boolean — default true: standardize to 'Last, First and ...' format",
  "dry_run":           "boolean — default false: report issues only, do not modify"
}
```

**Exactly one of `bib_path` or `bibtex_str` is required.**

### `enrich_strategy` values

| Value | Behavior |
|-------|---------|
| `fill_missing` | Only fills blank fields; never overwrites existing values |
| `prefer_crossref` | Crossref value wins if it differs from original |
| `prefer_original` | Enrichment only adds truly absent fields |

## Output Schema

```json
{
  "fixed_bibtex": "string — the full corrected .bib content",
  "issues_found": [
    {
      "entry_key": "string",
      "field":     "string | null",
      "issue":     "string — human-readable description",
      "severity":  "error | warning | info",
      "action":    "auto_fixed | auto_filled | needs_review | removed | flagged",
      "old_value": "string | null",
      "new_value": "string | null"
    }
  ],
  "stats": {
    "total":              0,
    "remaining":          0,
    "issues_found":       0,
    "auto_fixed":         0,
    "enriched":           0,
    "duplicates_removed": 0,
    "needs_review":       0
  }
}
```

### Issue severity levels

| Severity | Description | Example |
|----------|-------------|---------|
| `error` | Will cause LaTeX compilation failure or invalid citation | Missing `journal` in `@article` |
| `warning` | May cause malformed output or bibliography inconsistency | Mixed author name formats |
| `info` | Style recommendation | URL in `note` instead of `url` field |

### Action values

| Action | Meaning |
|--------|---------|
| `auto_fixed` | Rule-based fix applied automatically (e.g. year format) |
| `auto_filled` | Field added from Crossref API |
| `needs_review` | Issue detected but cannot be auto-resolved — user must fix |
| `removed` | Duplicate entry removed |
| `flagged` | Possible duplicate — user should verify |

## When to Use

- Preparing a `.bib` file for journal/conference submission
- Cleaning up a bibliography exported from Zotero, Mendeley, or Google Scholar (these often have inconsistent formatting)
- Auto-filling DOI, page numbers, or journal names for entries that have a DOI
- Detecting duplicate entries before submitting

## When NOT to Use

- Input is in RIS, EndNote XML, or CSL-JSON format → convert to BibTeX first
- User wants to change citation style (APA, MLA, IEEE) → that is handled by LaTeX `\bibliographystyle`, not by this skill
- User wants to reorder or sort references → out of scope
- No `.bib` file or BibTeX text is available

## Step-by-Step Instructions

1. **Get the BibTeX input** from the user — either a file path or pasted text.

2. **Run the script**:

   ```bash
   # Check and fix a .bib file (default: fill missing fields, remove duplicates):
   python skills/bibtex-fixer-enricher/run.py --bib refs.bib

   # Dry-run: report problems without modifying anything:
   python skills/bibtex-fixer-enricher/run.py --bib refs.bib --dry-run

   # Offline mode (no Crossref API calls):
   python skills/bibtex-fixer-enricher/run.py --bib refs.bib --no-enrich

   # Output only the fixed BibTeX (suitable for piping):
   python skills/bibtex-fixer-enricher/run.py --bib refs.bib --format bibtex
   ```

3. **Interpret the output**:
   - Present `stats` first: "Found X issues in Y entries (Z auto-fixed, W need review)"
   - List all `needs_review` items with their `issue` description — these require the user to act
   - Offer the `fixed_bibtex` as a code block for copy-paste or direct file write

4. **For `needs_review` entries**, ask the user to provide the missing information, then offer to re-run.

5. **Do not silently overwrite** the user's original `.bib` unless they confirm. Always show what changed via `issues_found[].old_value` / `new_value`.

## Known Limitations

- Crossref enrichment requires a DOI field already present; it cannot discover DOIs automatically
- `normalize_authors` uses heuristics and may misparse non-Western names (Chinese, Korean, Arabic). Flag as `needs_review` rather than auto-fixing these
- Crossref rate limit: ~1 request per 0.5 seconds. For files with >100 DOI-bearing entries, enrichment may take several minutes
- Does not handle LaTeX encoding issues (e.g. `{\"o}` vs `ö`) — use `bibtexparser`'s unicode handling separately

For a complete list of detected issue types, see `docs/issue-types.md`.
