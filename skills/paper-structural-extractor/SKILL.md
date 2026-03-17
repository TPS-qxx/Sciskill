---
name: paper-structural-extractor
description: Extract structured, field-level information from a single academic paper given an arXiv ID, DOI, or local PDF path. Use when you need machine-readable metadata about a paper's research question, methodology, datasets, baselines, metrics, findings, limitations, or future work — especially as input to research-gap-identifier or experiment-result-comparator. Do NOT use for simple title/author lookups (use ArXiv/Semantic Scholar API directly), for extracting information from multiple papers at once (call this skill per paper), or when the user just wants a plain-language summary.
---

# Paper Structural Extractor

Produces a structured JSON object with evidence-backed field extraction from a single paper. Every inferential field carries a `confidence` score and `evidence` quotes from the source text.

## Input Schema

```json
{
  "arxiv_id":   "string  — e.g. '2303.08774' or 'arxiv:1706.03762'",
  "doi":        "string  — e.g. '10.1145/3292500.3330919'",
  "pdf_path":   "string  — absolute or relative path to a local PDF",
  "mode":       "string  — 'metadata' | 'method' | 'experiment' | 'full' (default: 'full')",
  "pdf_backend":"string  — 'pymupdf' (default) | 'grobid'",
  "grobid_url": "string  — default 'http://localhost:8070' (only if backend=grobid)"
}
```

**Exactly one of `arxiv_id`, `doi`, or `pdf_path` is required.**

### Extraction modes

| Mode | Fields extracted | Speed | Best for |
|------|-----------------|-------|----------|
| `metadata` | title, authors, year, venue, abstract | Fast | Quick cataloging |
| `method` | + research_question, methodology, datasets, baselines | Medium | Method comparison |
| `experiment` | + metrics, main_findings, implementation_details | Medium | Result comparison |
| `full` | All fields including limitations, future_work | Slow | Gap analysis input |

## Output Schema

```json
{
  "title":   "string",
  "authors": ["string"],
  "year":    "string",
  "venue":   "string",
  "arxiv_id": "string | null",
  "doi":      "string | null",

  "research_question": {
    "value":      "string",
    "evidence":   ["quoted sentence from paper"],
    "confidence": 0.0
  },
  "problem_statement": {
    "value":      "string",
    "evidence":   ["string"],
    "confidence": 0.0
  },
  "methodology": {
    "approach":         "string",
    "model_architecture": "string | null",
    "key_techniques":   ["string"],
    "novelty":          "string",
    "confidence":       0.0
  },
  "datasets": [
    {
      "name":       "string",
      "version":    "string | null",
      "scale":      "string | null",
      "domain":     "string | null",
      "public":     true,
      "url":        "string | null"
    }
  ],
  "baselines": [
    {
      "name":       "string",
      "paper_ref":  "string | null",
      "type":       "prior_work | ablation | upper_bound"
    }
  ],
  "metrics": [
    {
      "name":       "string",
      "value":      "string | null",
      "dataset":    "string | null",
      "is_best":    false,
      "evidence":   "string | null"
    }
  ],
  "main_findings": [
    {
      "claim":      "string",
      "evidence":   ["string"],
      "confidence": 0.0
    }
  ],
  "limitations": ["string"],
  "future_work":  ["string"],
  "implementation_details": {
    "code_available":  true,
    "code_url":        "string | null",
    "hardware":        "string | null",
    "training_time":   "string | null"
  },
  "_extraction_meta": {
    "mode":           "string",
    "source":         "string",
    "full_text_used": false,
    "warnings":       ["string"]
  }
}
```

### Confidence scale

| Range | Meaning |
|-------|---------|
| 0.9–1.0 | Directly stated verbatim in text |
| 0.7–0.9 | Clearly implied; high-confidence paraphrase |
| 0.5–0.7 | Inferred from context; verify manually |
| < 0.5 | Uncertain; treat as suggestion only |

## When to Use

- You need structured paper data as input to `research-gap-identifier`
- Building a literature comparison table
- Extracting baselines or datasets to run `experiment-result-comparator`
- The user asks: "What method does this paper use?", "What datasets did they evaluate on?", "What are the limitations?"

## When NOT to Use

- User only wants title, authors, or abstract → use the ArXiv or Semantic Scholar API directly (faster, no LLM)
- User wants a plain-language summary or explanation → use the model directly without this skill
- Processing more than one paper at once → call this skill once per paper, collect results, then optionally feed to `research-gap-identifier`
- Paper is a survey/review (output quality degrades significantly for surveys)

## Step-by-Step Instructions

1. **Identify the input source** from the user's request (arXiv ID, DOI, or file path).

2. **Choose the mode**: if the user needs gap analysis or full comparison, use `full`; if only a quick method lookup, use `method`.

3. **Run the script**:
   ```bash
   # arXiv:
   python skills/paper-structural-extractor/run.py --arxiv 2303.08774 --mode full

   # DOI:
   python skills/paper-structural-extractor/run.py --doi 10.1145/3292500.3330919 --mode method

   # PDF (better quality than arXiv abstract-only):
   python skills/paper-structural-extractor/run.py --pdf /path/to/paper.pdf --mode full
   ```

4. **Check `_extraction_meta.warnings`** in the output. Common warnings:
   - `"abstract_only"`: only abstract was available (arXiv/DOI without PDF), inferential fields have lower confidence
   - `"llm_retry"`: JSON parsing failed once and was retried
   - `"truncated"`: PDF was too long and was truncated at 12,000 characters

5. **Trust fields selectively**: fields with `confidence < 0.6` should be presented as "possibly" or "the paper may" rather than stated as fact.

6. **Save the output JSON** if passing to `research-gap-identifier`.

## Known Limitations

- Abstract-only extraction (arXiv/DOI without PDF) produces `confidence < 0.7` for most inferential fields
- Survey and review papers return lower-quality `methodology` fields
- Papers behind paywalls cannot be accessed; only metadata from APIs will be available
- Non-English papers may have degraded extraction quality
