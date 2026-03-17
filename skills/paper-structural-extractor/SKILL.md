---
name: paper-structural-extractor
description: Extract structured JSON from an academic paper given an arXiv ID, DOI, or local PDF path. Use this skill when the user wants to analyze, summarize, or extract specific fields from a research paper — including research question, methodology, datasets, baselines, metrics, findings, limitations, and future work. Do NOT use for simple paper lookups; use when structured, field-level extraction is needed.
---

# Paper Structural Extractor

Extracts structured, field-level information from academic papers. The output is a rich JSON object suitable for downstream tasks like literature comparison, Related Work generation, and research gap analysis.

## When to Use

- User provides an arXiv ID, DOI, or PDF file path and wants structured information
- Downstream task requires paper metadata (methods, datasets, metrics, etc.)
- Building a literature comparison table or Related Work section
- Input to `research-gap-identifier` skill

## Step-by-Step Instructions

1. **Determine the input source** from the user's message:
   - arXiv ID (e.g. `2303.08774`, `arxiv:1706.03762`)
   - DOI (e.g. `10.1145/3292500.3330919`)
   - Local PDF path (e.g. `/path/to/paper.pdf`)

2. **Run the extraction script**, passing the appropriate argument:

   ```bash
   # From arXiv ID:
   python skills/paper-structural-extractor/run.py --arxiv 2303.08774

   # From DOI:
   python skills/paper-structural-extractor/run.py --doi 10.1145/3292500.3330919

   # From local PDF:
   python skills/paper-structural-extractor/run.py --pdf /path/to/paper.pdf
   ```

3. **Read the JSON output** from stdout. The script prints a single JSON object.

4. **Present key findings** to the user in a readable format. Highlight:
   - Research question / problem being solved
   - Core methodology and novel contributions
   - Datasets used and their scale
   - Baseline methods compared against
   - Key metrics and results (flag any claimed SOTA)
   - Limitations and future work directions

5. **Save the JSON** if the user plans to use it as input to `research-gap-identifier`.

## Output Schema

```json
{
  "title": "string",
  "authors": ["string"],
  "year": "string",
  "venue": "string",
  "research_question": "string",
  "problem_statement": "string",
  "methodology": {
    "approach": "string",
    "model_architecture": "string | null",
    "key_techniques": ["string"],
    "novelty": "string"
  },
  "datasets": [{"name": "string", "scale": "string|null", "domain": "string|null", "public": true}],
  "baselines": [{"name": "string", "source": "string|null"}],
  "metrics": [{"name": "string", "value": "string|null", "dataset": "string|null", "is_best": false}],
  "main_findings": ["string"],
  "limitations": ["string"],
  "future_work": ["string"],
  "implementation_details": {
    "code_available": true,
    "code_url": "string|null",
    "hardware": "string|null"
  }
}
```

## Error Handling

- If the arXiv ID is invalid or not found, the script will print an error to stderr and exit with code 1. Ask the user to verify the ID.
- If PDF parsing fails, try with `--backend grobid` (requires a running GROBID Docker container).
- If the LLM returns malformed JSON, the script retries once automatically; on second failure it returns `{"raw_extraction": "..."}`.

## Notes

- For PDF files, PyMuPDF is used by default (no external server needed). GROBID produces higher-quality section segmentation but requires Docker.
- Abstract-only extraction (arXiv/DOI without PDF) is fast but less detailed than full-text PDF extraction.
- The `implementation_details.code_available` field is `null` if the paper does not mention code.
