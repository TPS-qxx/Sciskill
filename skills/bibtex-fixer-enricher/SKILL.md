---
name: bibtex-fixer-enricher
description: Fix, normalize, and enrich BibTeX entries from a .bib file or raw BibTeX string. Use this skill when the user has BibTeX references that need cleaning — missing fields, duplicate entries, inconsistent author name formats, or citation enrichment via Crossref. Ideal for researchers writing papers in LaTeX who want clean, complete bibliography files.
---

# BibTeX Fixer & Enricher

Parses BibTeX, detects and fixes common quality issues, normalizes formatting, and auto-fills missing metadata by querying the Crossref API. Pure rule-based — no LLM required.

## When to Use

- User has a `.bib` file or a BibTeX string that needs cleaning before submission
- Missing required fields (journal, year, volume, pages, DOI)
- Author names inconsistently formatted (mix of "Last, First" and "First Last")
- Suspected duplicate entries
- Want to enrich entries that have a DOI with complete metadata from Crossref

## Step-by-Step Instructions

1. **Identify the input**: the user will provide either a `.bib` file path or raw BibTeX text.

2. **Run the fixer script**:

   ```bash
   # Fix a .bib file (outputs to stdout):
   python skills/bibtex-fixer-enricher/run.py --bib refs.bib

   # Fix raw BibTeX string passed inline:
   python skills/bibtex-fixer-enricher/run.py --bib refs.bib --no-enrich

   # Disable auto-enrichment (offline mode):
   python skills/bibtex-fixer-enricher/run.py --bib refs.bib --no-enrich

   # Disable duplicate removal:
   python skills/bibtex-fixer-enricher/run.py --bib refs.bib --keep-duplicates
   ```

3. **Review the output JSON**, which contains:
   - `fixed_bibtex`: the cleaned `.bib` content — give this to the user
   - `issues_found`: list of detected problems with entry key, issue description, and action taken
   - `stats`: summary counts (total entries, issues found, enriched, duplicates removed)

4. **Report findings** to the user:
   - How many entries had issues
   - Which entries still need manual review (action: `needs_review`)
   - Which entries were auto-enriched
   - If duplicates were removed, list the keys

5. **Offer the fixed BibTeX** for the user to copy or save.

## Issue Severity Levels

| Severity | Meaning | Action |
|----------|---------|--------|
| `error` | Missing required field or invalid format | `needs_review` or `auto_filled` |
| `warning` | Inconsistent formatting, possible duplicate | `needs_review` or `flagged` |
| `info` | Minor style suggestion | `needs_review` |

## Common Issues Detected

- Missing required fields per entry type (article needs journal, inproceedings needs booktitle, etc.)
- Mixed author name formats within a single entry
- All-caps author names (OCR artifact)
- Invalid year format (non-4-digit)
- URL stored in `note` field instead of `url` field
- Unbraced uppercase words in title (e.g. `{BERT}` should be `{{BERT}}`)
- Duplicate entries (same DOI, or same normalized title)

## Notes

- Auto-enrichment queries the Crossref REST API. Requires internet access and only works for entries that already have a `doi` field.
- Rate limit: 1 request per 0.5 seconds. For large `.bib` files (>100 entries), this may take a few minutes.
- The fixed BibTeX preserves the original entry order and all non-enriched fields.

See `docs/issue-types.md` for the complete list of checks and their explanations.
