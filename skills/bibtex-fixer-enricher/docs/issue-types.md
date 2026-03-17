# BibTeX Issue Types Reference

## Error-level Issues (must fix before submission)

### `missing_required_field`
A required field for the entry type is absent or empty.

| Entry type | Required fields |
|------------|----------------|
| `@article` | author, title, journal, year |
| `@inproceedings` | author, title, booktitle, year |
| `@book` | author, title, publisher, year |
| `@phdthesis` | author, title, school, year |

**Fix**: Add the missing field manually, or if you have the DOI, add it and re-run with `--enrich` to auto-fill.

### `invalid_year_format`
The `year` field is not a 4-digit number.

**Fix**: Correct to a 4-digit year, e.g. `year = {2023}`.

---

## Warning-level Issues (should fix)

### `inconsistent_author_format`
Some author names in the same entry use `Last, First` format and others use `First Last` format.

**Fix**: Use `--normalize` flag, or manually standardize to `Last, First and Last, First`.

### `allcaps_author`
An author name is all uppercase (common OCR artifact from scanned PDFs).

**Fix**: Correct to proper capitalization, e.g. `SMITH, JOHN` → `Smith, John`.

### `duplicate_by_doi`
Two entries share the same DOI.

**Fix**: Remove one. The fixer removes the second occurrence automatically with `--remove-duplicates`.

### `possible_duplicate_by_title`
Two entries have the same normalized title (after lowercasing and whitespace normalization).

**Fix**: Review manually — could be the same paper appearing in arXiv and conference proceedings. Keep the more complete entry.

### `unbraced_acronyms_in_title`
The title contains all-caps words (acronyms, model names) not wrapped in `{}`.

**Example problem**: `title = {BERT for Sequence Tagging}`

**Fix**: `title = {{BERT} for Sequence Tagging}` — the braces prevent BibTeX from downcasing acronyms in certain citation styles.

---

## Info-level Issues (optional)

### `url_in_note_field`
A URL was found in the `note` field. Some citation styles don't render `note` URLs properly.

**Fix**: Move the URL to the `url` field.

---

## Auto-filled Fields (via Crossref)

When `--enrich` is enabled and an entry has a `doi` field, the following missing fields are automatically filled from Crossref:

- `title`
- `author`
- `year`
- `journal` / `booktitle`
- `volume`
- `number`
- `pages`
- `publisher`
- `url`
